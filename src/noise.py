"""Synthetic noise model module for QubitX-MaxCut benchmarks.

Configured according to the Qiskit Fall Fest 2026 Master Guide:
- 1-qubit depolarizing error: 0.001
- 2-qubit CX depolarizing error: 0.005
- Symmetric readout bit-flip error: 0.01
"""

from typing import Any, Sequence
import networkx as nx
import numpy as np
from qiskit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit.transpiler import CouplingMap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError

from src.graph_utils import calculate_cut_value, solve_max_cut_brute_force, validate_graph
from src.qaoa_builder import (
    bitstring_to_partition,
    build_qaoa_circuit,
    compute_expectation_value,
    get_most_frequent_partition,
)

# Standard basis gates for superconducting architectures
DOCUMENTED_BASIS_GATES = ["rz", "sx", "x", "cx"]


def build_synthetic_noise_model(
    p1q: float = 0.001,
    p2q: float = 0.005,
    p_ro: float = 0.01,
    noisy_1q_gates: Sequence[str] = ("sx", "x"),
    include_rz: bool = False,
) -> NoiseModel:
    """Build a calibrated synthetic Qiskit Aer NoiseModel for Processor A/B benchmarking.

    Noise Allocation Rationale:
        - 2-qubit CX gates: Receive the 0.005 depolarizing error ('p2q').
        - Physical single-qubit gates ('sx', 'x'): Driven by microwave pulses that suffer
          from control and decoherence errors, thus receiving the 0.001 error ('p1q').
        - Virtual-Z gates ('rz'): In superconducting transmon architectures, RZ rotations
          are implemented via frame rotations in software (virtual Z gates) and have zero
          duration and zero physical gate error. Unless 'include_rz=True', RZ is modeled
          as error-free to reflect hardware physics.
        - Measurement readout ('measure'): Modeled as symmetric classical bit-flip channels
          with probability 'p_ro' = 0.01 (P(0|1) = P(1|0) = 0.01).

    Args:
        p1q: Depolarizing error probability for 1-qubit gates (default 0.001).
        p2q: Depolarizing error probability for 2-qubit CX gates (default 0.005).
        p_ro: Symmetric readout bit-flip probability (default 0.01).
        noisy_1q_gates: Names of single-qubit gates to apply p1q noise to.
        include_rz: If True, also applies p1q depolarizing error to 'rz' gates.

    Returns:
        NoiseModel: Configured Qiskit Aer NoiseModel.
    """
    for name, val in [("p1q", p1q), ("p2q", p2q), ("p_ro", p_ro)]:
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"Error probability '{name}' must be in [0.0, 1.0], got {val}")

    basis = list(DOCUMENTED_BASIS_GATES)
    noise_model = NoiseModel(basis_gates=basis)

    # 1. Single-qubit depolarizing error
    target_1q = list(noisy_1q_gates)
    if include_rz and "rz" not in target_1q:
        target_1q.append("rz")

    if p1q > 0.0 and target_1q:
        error_1q = depolarizing_error(p1q, 1)
        noise_model.add_all_qubit_quantum_error(error_1q, target_1q)

    # 2. Two-qubit CX depolarizing error
    if p2q > 0.0:
        error_2q = depolarizing_error(p2q, 2)
        noise_model.add_all_qubit_quantum_error(error_2q, ["cx"])

    # 3. Readout error (symmetric bit-flip)
    if p_ro > 0.0:
        ro_matrix = [[1.0 - p_ro, p_ro], [p_ro, 1.0 - p_ro]]
        readout_error = ReadoutError(ro_matrix)
        noise_model.add_all_qubit_readout_error(readout_error)

    return noise_model


def evaluate_transpiled_circuit_with_noise(
    circuit: QuantumCircuit,
    noise_model: NoiseModel,
    shots: int = 4096,
    seed_simulator: int = 42,
) -> dict[str, int]:
    """Execute a transpiled QuantumCircuit on AerSimulator with a synthetic NoiseModel.

    Args:
        circuit: Transpiled QuantumCircuit containing measurements.
        noise_model: Configured Qiskit Aer NoiseModel.
        shots: Number of measurement shots.
        seed_simulator: Random seed for simulation reproducibility.

    Returns:
        dict[str, int]: Measurement bitstring count dictionary.
    """
    sim = AerSimulator(noise_model=noise_model)
    result = sim.run(circuit, shots=shots, seed_simulator=seed_simulator).result()
    return result.get_counts()


def run_noisy_transpiled_qaoa(
    graph: nx.Graph,
    opt_gamma: Sequence[float],
    opt_beta: Sequence[float],
    p: int,
    coupling_map: CouplingMap,
    noise_model: NoiseModel | None = None,
    shots: int = 4096,
    optimization_level: int = 1,
    seed_transpiler: int = 42,
    seed_simulator: int = 42,
) -> dict[str, Any]:
    """Transpile a QAOA circuit to hardware coupling and evaluate with synthetic noise.

    Preserves measurement-to-logical-node mapping:
        Logical measurements are added to classical register bits 0..n-1.
        Qiskit's compiler maintains this logical mapping even when physical qubits
        are permuted by SWAP gates during routing.

    Args:
        graph: NetworkX graph.
        opt_gamma: Pre-optimized gamma parameters (from ideal optimization).
        opt_beta: Pre-optimized beta parameters (from ideal optimization).
        p: QAOA depth.
        coupling_map: Target Qiskit CouplingMap.
        noise_model: NoiseModel to apply. If None, default Master Guide model is used.
        shots: Measurement shots (default 4096).
        optimization_level: Transpiler optimization level (default 1).
        seed_transpiler: Seed for transpiler routing determinism.
        seed_simulator: Seed for simulator shot sampling.

    Returns:
        dict: Detailed noisy evaluation metrics.
    """
    validate_graph(graph)
    if noise_model is None:
        noise_model = build_synthetic_noise_model()

    # 1. Build logical measured QAOA circuit at optimal parameters
    qc_logical = build_qaoa_circuit(
        graph, p=p, gamma=opt_gamma, beta=opt_beta, measure=True
    )

    # 2. Transpile to target coupling map and documented hardware basis
    transpiled_qc = transpile(
        qc_logical,
        coupling_map=coupling_map,
        basis_gates=DOCUMENTED_BASIS_GATES,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )

    # 3. Simulate with noise
    counts = evaluate_transpiled_circuit_with_noise(
        transpiled_qc,
        noise_model=noise_model,
        shots=shots,
        seed_simulator=seed_simulator,
    )

    # 4. Compute solution quality metrics from noisy counts
    expected_cut = compute_expectation_value(counts, graph)
    best_part, best_cut, top_prob = get_most_frequent_partition(counts, graph)

    exact_max_cut, _, all_opts = solve_max_cut_brute_force(graph)

    # Probability of sampling any optimal bitstring
    nodes = sorted(list(graph.nodes()))
    total_shots = sum(counts.values())
    opt_shots = sum(
        cnt
        for bstr, cnt in counts.items()
        if bitstring_to_partition(bstr, nodes) in all_opts
    )
    opt_prob = opt_shots / total_shots if total_shots > 0 else 0.0

    ops = dict(transpiled_qc.count_ops())

    return {
        "transpiled_qc": transpiled_qc,
        "counts": counts,
        "transpiled_depth": transpiled_qc.depth(),
        "transpiled_cx_count": ops.get("cx", 0),
        "transpiled_total_ops": sum(ops.values()),
        "noisy_expected_cut": round(expected_cut, 4),
        "noisy_best_sampled_cut": round(best_cut, 4),
        "noisy_approx_ratio": round(expected_cut / exact_max_cut, 4),
        "noisy_optimal_solution_prob": round(opt_prob, 4),
    }
