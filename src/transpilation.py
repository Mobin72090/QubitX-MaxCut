"""Transpilation analysis and SWAP bottleneck benchmarking for QAOA circuits."""

import os
import time
from typing import Sequence
import networkx as nx
import pandas as pd
from qiskit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit.transpiler import CouplingMap

from src.graph_utils import validate_graph
from src.qaoa_builder import build_qaoa_circuit

DOCUMENTED_BASIS_GATES = ["rz", "sx", "x", "cx"]


def get_development_coupling_map(
    layout_type: str, num_qubits: int = 4, **kwargs
) -> tuple[CouplingMap, str]:
    """Generate development coupling maps for hardware transpilation analysis.

    Note:
        These layouts are development examples for SWAP analysis and do NOT
        represent official hackathon Processor A or Processor B hardware specs.

    Args:
        layout_type: One of 'line', 'grid', 'ring', or 'full'.
        num_qubits: Total number of physical qubits.
        **kwargs: Optional layout specs (e.g. rows, cols for grid).

    Returns:
        tuple[CouplingMap, str]: The CouplingMap instance and its descriptive label.
    """
    layout_key = layout_type.lower().strip()

    if layout_key in ("line", "linear"):
        cm = CouplingMap.from_line(num_qubits)
        desc = f"Development Linear Chain ({num_qubits} qubits, 1D line)"
    elif layout_key in ("grid", "2d_grid"):
        rows = kwargs.get("rows", 2)
        cols = kwargs.get("cols", (num_qubits + rows - 1) // rows)
        if rows * cols < num_qubits:
            raise ValueError(f"Grid dimensions {rows}x{cols} cannot accommodate {num_qubits} qubits.")
        cm = CouplingMap.from_grid(rows, cols)
        desc = f"Development 2D Grid ({rows}x{cols}, {cm.size()} qubits)"
    elif layout_key in ("ring", "circular"):
        cm = CouplingMap.from_ring(num_qubits)
        desc = f"Development Ring Layout ({num_qubits} qubits, 1D ring)"
    elif layout_key in ("full", "fully_connected", "all_to_all"):
        cm = CouplingMap.from_full(num_qubits)
        desc = f"Development Fully Connected ({num_qubits} qubits, all-to-all)"
    else:
        raise ValueError(
            f"Unsupported layout_type '{layout_type}'. "
            "Choose from 'line', 'grid', 'ring', or 'full'."
        )

    return cm, desc


def validate_coupling_map(coupling_map: CouplingMap, required_qubits: int) -> None:
    """Validate that a coupling map is suitable for transpilation.

    Args:
        coupling_map: Qiskit CouplingMap object.
        required_qubits: Minimum number of physical qubits required by the circuit.
    """
    if coupling_map is None:
        raise ValueError("Coupling map cannot be None.")

    if coupling_map.size() < required_qubits:
        raise ValueError(
            f"Coupling map size ({coupling_map.size()}) is smaller than required qubits ({required_qubits})."
        )

    if not coupling_map.is_connected():
        raise ValueError("Coupling map is disconnected. Qubit routing requires a connected coupling graph.")


def count_two_qubit_gates(circuit: QuantumCircuit) -> int:
    """Count the total number of 2-qubit gate instructions in a circuit.

    Includes gates operating on exactly 2 qubits (e.g., cx, cz, ecr, rzz, swap).
    Excludes non-gate instructions like barriers and measurements.
    """
    count = 0
    for inst in circuit.data:
        op = inst.operation
        if op.num_qubits == 2 and op.name not in ("barrier", "measure"):
            count += 1
    return count


def count_swap_gates(circuit: QuantumCircuit) -> int:
    """Count the number of SWAP gates present in a circuit."""
    return sum(1 for inst in circuit.data if inst.operation.name == "swap")


def analyze_transpilation(
    circuit: QuantumCircuit,
    coupling_map: CouplingMap,
    layout_name: str = "custom",
    optimization_level: int = 1,
    seed_transpiler: int = 42,
    basis_gates: Sequence[str] | None = None,
) -> dict:
    """Transpile a circuit onto a coupling map and return detailed structural metrics.

    Args:
        circuit: Logical Qiskit QuantumCircuit.
        coupling_map: Target Qiskit CouplingMap.
        layout_name: Human-readable identifier for the coupling layout.
        optimization_level: Transpiler optimization level (0, 1, 2, or 3).
        seed_transpiler: Random seed for deterministic transpilation.
        basis_gates: Optional target hardware basis gates (e.g. ['cz', 'rz', 'sx', 'x', 'id']).

    Returns:
        dict: Summary containing depth, gate counts, SWAP overhead, and transpilation time.
    """
    validate_coupling_map(coupling_map, circuit.num_qubits)

    # Record original circuit properties
    orig_depth = circuit.depth()
    orig_total_ops = sum(circuit.count_ops().values())
    orig_2q_gates = count_two_qubit_gates(circuit)
    orig_swap_count = count_swap_gates(circuit)

    start_time = time.perf_counter()
    transpiled_qc = transpile(
        circuit,
        coupling_map=coupling_map,
        basis_gates=basis_gates,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )
    elapsed_time = time.perf_counter() - start_time

    # Record transpiled circuit properties
    transpiled_depth = transpiled_qc.depth()
    transpiled_total_ops = sum(transpiled_qc.count_ops().values())
    transpiled_2q_gates = count_two_qubit_gates(transpiled_qc)
    transpiled_swap_count = count_swap_gates(transpiled_qc)

    # Calculate CX count under documented challenge basis ['cx', 'rz', 'sx', 'x']
    if basis_gates is not None and "cx" in basis_gates:
        transpiled_cx_count = int(transpiled_qc.count_ops().get("cx", 0))
    else:
        basis_qc = transpile(
            circuit,
            coupling_map=coupling_map,
            basis_gates=["cx", "rz", "sx", "x"],
            optimization_level=optimization_level,
            seed_transpiler=seed_transpiler,
        )
        transpiled_cx_count = int(basis_qc.count_ops().get("cx", 0))

    # SWAP overhead inserted specifically for routing
    swap_overhead = max(0, transpiled_swap_count - orig_swap_count)

    return {
        "layout_name": layout_name,
        "num_qubits": circuit.num_qubits,
        "optimization_level": optimization_level,
        "seed_transpiler": seed_transpiler,
        "orig_depth": orig_depth,
        "orig_total_ops": orig_total_ops,
        "orig_2q_gates": orig_2q_gates,
        "orig_swap_count": orig_swap_count,
        "transpiled_depth": transpiled_depth,
        "transpiled_total_ops": transpiled_total_ops,
        "transpiled_2q_gates": transpiled_2q_gates,
        "transpiled_swap_count": transpiled_swap_count,
        "swap_overhead": swap_overhead,
        "transpiled_cx_count": transpiled_cx_count,
        "transpilation_time_sec": round(elapsed_time, 5),
    }


def run_transpilation_benchmarks(
    graph: nx.Graph,
    p: int = 1,
    optimization_levels: Sequence[int] = (1, 2, 3),
    output_csv: str = "results/transpilation_metrics.csv",
    seed: int = 42,
) -> pd.DataFrame:
    """Run transpilation benchmarking across development layouts and optimization levels.

    Args:
        graph: NetworkX problem graph.
        p: QAOA depth.
        optimization_levels: Sequence of transpiler optimization levels to test.
        output_csv: Path to save the resulting benchmark CSV table.
        seed: Fixed seed for transpiler reproducibility.

    Returns:
        pd.DataFrame: Table of transpilation performance metrics.
    """
    validate_graph(graph)
    num_nodes = graph.number_of_nodes()

    # Build unmeasured parameterized QAOA circuit for structural analysis
    logical_qc = build_qaoa_circuit(graph, p=p, measure=False)

    # Define standard development layouts for testing connectivity constraints
    layouts_to_test = [
        ("line", "Development Linear Chain"),
        ("ring", "Development Ring Layout"),
        ("grid", "Development 2D Grid"),
        ("full", "Development Fully Connected"),
    ]

    benchmark_rows = []

    for layout_key, label in layouts_to_test:
        cm, desc = get_development_coupling_map(layout_key, num_qubits=num_nodes)
        for opt_level in optimization_levels:
            metrics = analyze_transpilation(
                logical_qc,
                coupling_map=cm,
                layout_name=f"{desc} (opt_level={opt_level})",
                optimization_level=opt_level,
                seed_transpiler=seed,
            )
            benchmark_rows.append(metrics)

    df = pd.DataFrame(benchmark_rows)

    # Save metrics to CSV under results/
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)

    return df
