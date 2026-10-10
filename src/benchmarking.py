"""Benchmarking module for QAOA Max-Cut optimization, solution quality, and transpilation bottlenecks."""

import os
from typing import Sequence
import networkx as nx
import pandas as pd

from src.graph_utils import (
    calculate_cut_value,
    solve_max_cut_brute_force,
    validate_graph,
)
from src.processors import load_development_processors
from src.qaoa_builder import (
    bitstring_to_partition,
    build_qaoa_circuit,
    get_most_frequent_partition,
    optimize_qaoa,
)
from src.transpilation import (
    analyze_transpilation,
    get_development_coupling_map,
)


def calculate_optimal_probability(
    counts: dict[str, int],
    graph: nx.Graph,
    optimal_partitions: Sequence[dict[int, int]],
) -> float:
    """Calculate the fraction of measurement shots that yielded an exact optimal Max-Cut partition.

    Args:
        counts: Dictionary mapping measured bitstring -> frequency count.
        graph: NetworkX problem graph.
        optimal_partitions: List of partition dictionaries corresponding to exact ground truth Max-Cut.

    Returns:
        float: Probability (between 0.0 and 1.0) of measuring an optimal solution.
    """
    total_shots = sum(counts.values())
    if total_shots == 0:
        return 0.0

    nodes = sorted(list(graph.nodes()))
    optimal_shots = 0

    for bitstring, count in counts.items():
        partition = bitstring_to_partition(bitstring, nodes)
        if partition in optimal_partitions:
            optimal_shots += count

    return float(optimal_shots / total_shots)


def run_qaoa_benchmark(
    graph: nx.Graph,
    p_list: Sequence[int] = (1, 2),
    layouts: Sequence[str] = ("line", "ring", "grid", "full"),
    optimization_level: int = 1,
    shots: int = 2048,
    maxiter: int = 40,
    seed_simulator: int = 42,
    seed_transpiler: int = 42,
    output_csv: str = "results/qaoa_benchmark_results.csv",
) -> pd.DataFrame:
    """Run comprehensive QAOA benchmarks combining solution quality and transpilation metrics.

    Note:
        Coupling layouts are development examples for hardware connectivity analysis and do NOT
        represent official hackathon Processor A or Processor B hardware specs.

    Args:
        graph: NetworkX graph.
        p_list: List of QAOA depths p to benchmark.
        layouts: List of coupling layout keys ('line', 'ring', 'grid', 'full').
        optimization_level: Transpiler optimization level (0, 1, 2, 3).
        shots: Number of measurement shots per circuit execution.
        maxiter: Maximum iterations for classical parameter optimization.
        seed_simulator: Random seed for simulation and QAOA initialization reproducibility.
        seed_transpiler: Fixed seed for deterministic hardware transpilation routing.
        output_csv: Path to save the resulting CSV file under results/.

    Returns:
        pd.DataFrame: Table of benchmark results.
    """
    validate_graph(graph)
    nodes = sorted(list(graph.nodes()))
    num_nodes = len(nodes)
    num_edges = graph.number_of_edges()

    # 1. Exact Brute-Force Ground Truth Baseline
    exact_max_cut, exact_partition, all_optimal_partitions = (
        solve_max_cut_brute_force(graph)
    )

    if exact_max_cut <= 0:
        raise ValueError("Ground-truth Max-Cut value must be greater than zero.")

    results_data = []

    for p in p_list:
        if p < 1:
            raise ValueError(f"QAOA depth p must be >= 1, got {p}.")

        # 2. Run QAOA Classical Optimization via Qiskit Aer
        opt_params, opt_exp_cut, final_counts = optimize_qaoa(
            graph=graph,
            p=p,
            maxiter=maxiter,
            shots=shots,
            seed=seed_simulator,
        )

        # 3. Analyze Solution Quality
        best_partition, best_sampled_cut, top_prob = get_most_frequent_partition(
            final_counts, graph
        )
        top_bitstring = max(final_counts, key=final_counts.get)
        optimal_solution_prob = calculate_optimal_probability(
            final_counts, graph, all_optimal_partitions
        )

        approx_ratio_expected = float(opt_exp_cut / exact_max_cut)
        approx_ratio_best = float(best_sampled_cut / exact_max_cut)

        # 4. Transpilation & Hardware Topology Metrics
        logical_qc = build_qaoa_circuit(graph, p=p, measure=False)

        for layout_key in layouts:
            cm, layout_desc = get_development_coupling_map(
                layout_key, num_qubits=num_nodes
            )
            t_metrics = analyze_transpilation(
                logical_qc,
                coupling_map=cm,
                layout_name=layout_desc,
                optimization_level=optimization_level,
                seed_transpiler=seed_transpiler,
            )

            record = {
                "nodes": num_nodes,
                "edges": num_edges,
                "qaoa_depth_p": p,
                "shots": shots,
                "seed_simulator": seed_simulator,
                "seed_transpiler": seed_transpiler,
                "exact_max_cut_value": round(exact_max_cut, 4),
                "opt_expected_cut": round(opt_exp_cut, 4),
                "best_sampled_cut": round(best_sampled_cut, 4),
                "approx_ratio_expected": round(approx_ratio_expected, 4),
                "approx_ratio_best": round(approx_ratio_best, 4),
                "optimal_solution_prob": round(optimal_solution_prob, 4),
                "top_bitstring": top_bitstring,
                "top_bitstring_prob": round(top_prob, 4),
                "layout_name": layout_desc,
                "transpiler_opt_level": optimization_level,
                "orig_depth": t_metrics["orig_depth"],
                "orig_2q_gates": t_metrics["orig_2q_gates"],
                "transpiled_depth": t_metrics["transpiled_depth"],
                "transpiled_2q_gates": t_metrics["transpiled_2q_gates"],
                "transpiled_swap_count": t_metrics["transpiled_swap_count"],
                "swap_overhead": t_metrics["swap_overhead"],
                "transpilation_time_sec": t_metrics["transpilation_time_sec"],
            }
            results_data.append(record)

    df = pd.DataFrame(results_data)

    # Save to CSV under results/
    if output_csv:
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        df.to_csv(output_csv, index=False)

    return df


def run_processor_ab_benchmark(
    graph: nx.Graph,
    p_list: Sequence[int] = (1, 2),
    optimization_level: int = 1,
    shots: int = 2048,
    maxiter: int = 40,
    seed_simulator: int = 42,
    seed_transpiler: int = 42,
    output_csv: str = "results/processor_ab_development_results.csv",
) -> pd.DataFrame:
    """Benchmark QAOA solution quality and transpilation metrics on Processor A and B configurations.

    Args:
        graph: NetworkX problem graph.
        p_list: List of QAOA depths p to benchmark.
        optimization_level: Transpiler optimization level.
        shots: Measurement shot count.
        maxiter: Maximum iterations for classical parameter optimization.
        seed_simulator: Random seed for simulation reproducibility.
        seed_transpiler: Random seed for deterministic transpilation routing.
        output_csv: Path to save the resulting comparison CSV file.

    Returns:
        pd.DataFrame: Table comparing Processor A and Processor B benchmarks.
    """
    validate_graph(graph)
    nodes = sorted(list(graph.nodes()))
    num_nodes = len(nodes)
    num_edges = graph.number_of_edges()

    exact_max_cut, exact_partition, all_optimal_partitions = (
        solve_max_cut_brute_force(graph)
    )

    dev_processors = load_development_processors()
    results_data = []

    for p in p_list:
        if p < 1:
            raise ValueError(f"QAOA depth p must be >= 1, got {p}.")

        # 1. QAOA Optimization
        opt_params, opt_exp_cut, final_counts = optimize_qaoa(
            graph=graph,
            p=p,
            maxiter=maxiter,
            shots=shots,
            seed=seed_simulator,
        )

        best_partition, best_sampled_cut, top_prob = get_most_frequent_partition(
            final_counts, graph
        )
        top_bitstring = max(final_counts, key=final_counts.get)
        optimal_solution_prob = calculate_optimal_probability(
            final_counts, graph, all_optimal_partitions
        )

        approx_ratio_expected = float(opt_exp_cut / exact_max_cut)
        approx_ratio_best = float(best_sampled_cut / exact_max_cut)

        logical_qc = build_qaoa_circuit(graph, p=p, measure=False)

        # 2. Transpile onto Processor A and Processor B
        for pid, (data_dict, cm, desc_label) in dev_processors.items():
            t_metrics = analyze_transpilation(
                logical_qc,
                coupling_map=cm,
                layout_name=desc_label,
                optimization_level=optimization_level,
                seed_transpiler=seed_transpiler,
            )

            record = {
                "processor_id": data_dict["processor_id"],
                "processor_name": data_dict["processor_name"],
                "configuration_status": data_dict["configuration_status"],
                "is_official_specification": data_dict["is_official_specification"],
                "physical_qubits": data_dict["num_qubits"],
                "logical_qubits": num_nodes,
                "edges": num_edges,
                "qaoa_depth_p": p,
                "shots": shots,
                "seed_simulator": seed_simulator,
                "seed_transpiler": seed_transpiler,
                "exact_max_cut_value": round(exact_max_cut, 4),
                "opt_expected_cut": round(opt_exp_cut, 4),
                "best_sampled_cut": round(best_sampled_cut, 4),
                "approx_ratio_expected": round(approx_ratio_expected, 4),
                "approx_ratio_best": round(approx_ratio_best, 4),
                "optimal_solution_prob": round(optimal_solution_prob, 4),
                "top_bitstring": top_bitstring,
                "top_bitstring_prob": round(top_prob, 4),
                "orig_depth": t_metrics["orig_depth"],
                "orig_2q_gates": t_metrics["orig_2q_gates"],
                "transpiled_depth": t_metrics["transpiled_depth"],
                "transpiled_2q_gates": t_metrics["transpiled_2q_gates"],
                "transpiled_swap_count": t_metrics["transpiled_swap_count"],
                "swap_overhead": t_metrics["swap_overhead"],
                "transpilation_time_sec": t_metrics["transpilation_time_sec"],
            }
            results_data.append(record)

    df = pd.DataFrame(results_data)

    if output_csv:
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        df.to_csv(output_csv, index=False)

    return df


def run_graph_size_routing_sweep(
    node_counts: Sequence[int] = (5, 6, 7),
    p: int = 1,
    optimization_level: int = 1,
    seed_transpiler: int = 42,
    output_csv: str = "results/graph_size_routing_sweep.csv",
) -> pd.DataFrame:
    """Benchmark transpilation SWAP bottlenecks across expanding logical graph sizes (5, 6, 7 nodes).

    Capacity Check Rule:
        If logical qubits (n) > physical qubits (N), the combination is marked as unsupported
        (`is_supported = False`, `transpilation_success = False`) without attempting invalid transpilation.

    Args:
        node_counts: Sequence of logical node counts to test (default (5, 6, 7)).
        p: QAOA depth.
        optimization_level: Transpiler optimization level.
        seed_transpiler: Random seed for deterministic transpilation routing.
        output_csv: Path to save the output CSV table under results/.

    Returns:
        pd.DataFrame: Table of routing sweep results.
    """
    from src.graph_utils import create_synthetic_graph
    from src.transpilation import count_two_qubit_gates

    dev_processors = load_development_processors()
    sweep_records = []

    for n in node_counts:
        # Build reproducible synthetic weighted graph for node count n
        g = create_synthetic_graph(num_nodes=n, seed=42)
        num_edges = g.number_of_edges()
        logical_qc = build_qaoa_circuit(g, p=p, measure=False)

        for pid, (data_dict, cm, desc_label) in dev_processors.items():
            physical_qubits = data_dict["num_qubits"]
            is_supported = n <= physical_qubits

            if is_supported:
                t_metrics = analyze_transpilation(
                    logical_qc,
                    coupling_map=cm,
                    layout_name=desc_label,
                    optimization_level=optimization_level,
                    seed_transpiler=seed_transpiler,
                )
                record = {
                    "logical_nodes": n,
                    "logical_edges": num_edges,
                    "processor_id": data_dict["processor_id"],
                    "processor_name": data_dict["processor_name"],
                    "physical_qubits": physical_qubits,
                    "qaoa_depth_p": p,
                    "is_supported": True,
                    "transpilation_success": True,
                    "orig_depth": t_metrics["orig_depth"],
                    "orig_2q_gates": t_metrics["orig_2q_gates"],
                    "transpiled_depth": t_metrics["transpiled_depth"],
                    "transpiled_2q_gates": t_metrics["transpiled_2q_gates"],
                    "transpiled_swap_count": t_metrics["transpiled_swap_count"],
                    "swap_overhead": t_metrics["swap_overhead"],
                    "transpilation_time_sec": t_metrics["transpilation_time_sec"],
                    "notes": "Supported development transpilation",
                }
            else:
                record = {
                    "logical_nodes": n,
                    "logical_edges": num_edges,
                    "processor_id": data_dict["processor_id"],
                    "processor_name": data_dict["processor_name"],
                    "physical_qubits": physical_qubits,
                    "qaoa_depth_p": p,
                    "is_supported": False,
                    "transpilation_success": False,
                    "orig_depth": logical_qc.depth(),
                    "orig_2q_gates": count_two_qubit_gates(logical_qc),
                    "transpiled_depth": None,
                    "transpiled_2q_gates": None,
                    "transpiled_swap_count": None,
                    "swap_overhead": None,
                    "transpilation_time_sec": 0.0,
                    "notes": f"Unsupported: logical qubits ({n}) exceed physical capacity ({physical_qubits})",
                }

            sweep_records.append(record)

    df = pd.DataFrame(sweep_records)

    if output_csv:
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        df.to_csv(output_csv, index=False)

    return df

