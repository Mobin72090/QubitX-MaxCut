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
