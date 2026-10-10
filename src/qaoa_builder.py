"""QAOA circuit construction, parameter binding, and expectation value calculation for weighted Max-Cut."""

from typing import Sequence
import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector

from src.graph_utils import calculate_cut_value, validate_graph


def build_qaoa_circuit(
    graph: nx.Graph,
    p: int = 1,
    gamma: Sequence[float | object] | None = None,
    beta: Sequence[float | object] | None = None,
    measure: bool = True,
) -> QuantumCircuit:
    """Construct a QAOA QuantumCircuit for weighted Max-Cut on a given graph.

    Args:
        graph: NetworkX graph with numeric edge weights.
        p: QAOA depth (number of cost + mixer layers). Must be >= 1.
        gamma: Angles for the cost Hamiltonian layers. If None, symbolic ParameterVector is used.
        beta: Angles for the mixer Hamiltonian layers. If None, symbolic ParameterVector is used.
        measure: If True, appends measurement of all qubits to classical bits at the end.

    Returns:
        QuantumCircuit: The constructed QAOA circuit.
    """
    validate_graph(graph)

    if p < 1:
        raise ValueError("QAOA depth p must be at least 1.")

    nodes = sorted(list(graph.nodes()))
    num_qubits = len(nodes)
    node_to_qubit = {node: idx for idx, node in enumerate(nodes)}

    # Define symbolic parameters if not provided
    if gamma is None:
        gamma = ParameterVector("gamma", p)
    if beta is None:
        beta = ParameterVector("beta", p)

    if len(gamma) != p or len(beta) != p:
        raise ValueError(f"Length of gamma and beta must match QAOA depth p={p}.")

    qc = QuantumCircuit(num_qubits)

    # 1. Initial State: Equal superposition |+>^n
    for q in range(num_qubits):
        qc.h(q)

    # 2. QAOA Layers
    for layer in range(p):
        g_val = gamma[layer]
        b_val = beta[layer]

        # Cost Unitary: U(C, gamma) = exp(-i * gamma * H_C)
        # H_C = sum_{(u,v)} w_{uv} * (1 - Z_u Z_v) / 2
        # RZZ gate implements exp(-i * theta/2 * Z_u Z_v)
        # So theta = 2 * gamma * w_{uv}
        for u, v, data in graph.edges(data=True):
            w = float(data["weight"])
            qubit_u = node_to_qubit[u]
            qubit_v = node_to_qubit[v]
            qc.rzz(2 * g_val * w, qubit_u, qubit_v)

        # Mixer Unitary: U(B, beta) = exp(-i * beta * H_B)
        # H_B = sum_u X_u
        # RX gate implements exp(-i * theta/2 * X_u) -> theta = 2 * beta
        for q in range(num_qubits):
            qc.rx(2 * b_val, q)

    # 3. Measurement layer
    if measure:
        qc.measure_all()

    return qc


def bitstring_to_partition(bitstring: str, nodes: Sequence[int]) -> dict[int, int]:
    """Convert a Qiskit measurement bitstring to a graph partition assignment.

    Note on Qiskit bitstring endianness:
        Qiskit bitstrings are ordered right-to-left: bitstring[-1] is qubit 0,
        bitstring[-2] is qubit 1, ..., bitstring[0] is qubit n-1.

    Args:
        bitstring: Binary string from Qiskit measurement counts (e.g., '0110').
        nodes: List of graph node labels corresponding to qubit indices 0..n-1.

    Returns:
        dict[int, int]: Mapping from graph node -> partition assignment (0 or 1).
    """
    # Reverse string so index i maps directly to qubit i
    reversed_bits = bitstring[::-1]
    return {nodes[i]: int(reversed_bits[i]) for i in range(len(nodes))}


def compute_expectation_value(counts: dict[str, int], graph: nx.Graph) -> float:
    """Calculate the expected cut value <C> from measurement outcome counts.

    Args:
        counts: Outcome dictionary mapping measured bitstring -> count.
        graph: NetworkX graph with numeric edge weights.

    Returns:
        float: Expected Max-Cut value <C>.
    """
    validate_graph(graph)
    nodes = sorted(list(graph.nodes()))
    total_shots = sum(counts.values())

    if total_shots == 0:
        return 0.0

    expected_cut = 0.0
    for bitstring, count in counts.items():
        partition = bitstring_to_partition(bitstring, nodes)
        cut_val = calculate_cut_value(graph, partition)
        expected_cut += cut_val * (count / total_shots)

    return float(expected_cut)


def get_most_frequent_partition(
    counts: dict[str, int], graph: nx.Graph
) -> tuple[dict[int, int], float, float]:
    """Find the most frequently sampled partition from measurement counts.

    Args:
        counts: Outcome dictionary mapping measured bitstring -> count.
        graph: NetworkX graph.

    Returns:
        tuple containing:
            - best_partition (dict): Partition corresponding to top bitstring.
            - cut_value (float): Cut value of the top partition.
            - probability (float): Sampling frequency of the top bitstring.
    """
    nodes = sorted(list(graph.nodes()))
    total_shots = sum(counts.values())
    top_bitstring = max(counts, key=counts.get)
    best_partition = bitstring_to_partition(top_bitstring, nodes)
    cut_val = calculate_cut_value(graph, best_partition)
    prob = counts[top_bitstring] / total_shots if total_shots > 0 else 0.0

    return best_partition, cut_val, prob


def optimize_qaoa(
    graph: nx.Graph,
    p: int = 1,
    optimizer_name: str = "COBYLA",
    maxiter: int = 100,
    shots: int = 2048,
    seed: int | None = 42,
    initial_point: Sequence[float] | None = None,
) -> tuple[np.ndarray, float, dict[str, int]]:
    """Optimize QAOA gamma and beta parameters to maximize expected cut value.

    Args:
        graph: NetworkX graph.
        p: QAOA depth.
        optimizer_name: SciPy optimization method (default 'COBYLA').
        maxiter: Maximum optimization iterations.
        shots: Number of measurement shots per circuit evaluation.
        seed: Random seed for reproducibility.
        initial_point: Optional initial parameter array of shape (2*p,).

    Returns:
        tuple containing:
            - optimal_params (np.ndarray): Array of [gamma_0..gamma_{p-1}, beta_0..beta_{p-1}].
            - max_expected_cut (float): Maximized expected cut value <C>.
            - final_counts (dict[str, int]): Measurement counts at optimal parameters.
    """
    from qiskit_aer import AerSimulator
    from scipy.optimize import minimize

    validate_graph(graph)

    if initial_point is None:
        rng = np.random.default_rng(seed)
        # Standard initial range: gamma in [0, pi], beta in [0, pi/2]
        init_gamma = rng.uniform(0, np.pi, size=p)
        init_beta = rng.uniform(0, np.pi / 2, size=p)
        initial_point = np.concatenate([init_gamma, init_beta])

    initial_point = np.array(initial_point, dtype=float)

    sim = AerSimulator()

    def loss_function(params: np.ndarray) -> float:
        gamma_angles = params[:p]
        beta_angles = params[p:]

        qc = build_qaoa_circuit(
            graph, p=p, gamma=gamma_angles, beta=beta_angles, measure=True
        )

        result = sim.run(qc, shots=shots, seed_simulator=seed).result()
        counts = result.get_counts()
        exp_cut = compute_expectation_value(counts, graph)

        # Minimize negative expected cut value
        return -float(exp_cut)

    res = minimize(
        loss_function,
        initial_point,
        method=optimizer_name,
        options={"maxiter": maxiter},
    )

    opt_params = res.x
    opt_gamma = opt_params[:p]
    opt_beta = opt_params[p:]

    final_qc = build_qaoa_circuit(
        graph, p=p, gamma=opt_gamma, beta=opt_beta, measure=True
    )
    final_result = sim.run(final_qc, shots=shots, seed_simulator=seed).result()
    final_counts = final_result.get_counts()
    max_expected_cut = compute_expectation_value(final_counts, graph)

    return opt_params, max_expected_cut, final_counts

