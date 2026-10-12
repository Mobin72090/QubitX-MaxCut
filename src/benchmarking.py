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
from src.noise import (
    DOCUMENTED_BASIS_GATES,
    build_synthetic_noise_model,
    run_noisy_transpiled_qaoa,
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
    count_two_qubit_gates,
    get_development_coupling_map,
)



def _save_csv_dual(df: pd.DataFrame, primary_path: str) -> None:
    """Helper function to save benchmark DataFrame to both results/tables/ and results/."""
    filename = os.path.basename(primary_path)
    paths = [
        primary_path,
        os.path.join("results", "tables", filename),
        os.path.join("results", filename),
    ]
    for p in paths:
        if p:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            df.to_csv(p, index=False)



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

    # Save to CSV under results/ and results/tables/
    if output_csv:
        _save_csv_dual(df, output_csv)

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
            physical_qubits = data_dict["num_qubits"]
            is_supported = num_nodes <= physical_qubits

            if is_supported:
                t_metrics = analyze_transpilation(
                    logical_qc,
                    coupling_map=cm,
                    layout_name=desc_label,
                    optimization_level=optimization_level,
                    seed_transpiler=seed_transpiler,
                )
                t_depth = t_metrics["transpiled_depth"]
                t_2q = t_metrics["transpiled_2q_gates"]
                t_swap = t_metrics["transpiled_swap_count"]
                s_overhead = t_metrics["swap_overhead"]
                t_cx = t_metrics["transpiled_cx_count"]
                t_time = t_metrics["transpilation_time_sec"]
                notes = "Supported development transpilation"
            else:
                t_depth = None
                t_2q = None
                t_swap = None
                s_overhead = None
                t_cx = None
                t_time = 0.0
                notes = f"Unsupported: logical qubits ({num_nodes}) exceed physical capacity ({physical_qubits})"

            record = {
                "processor_id": data_dict["processor_id"],
                "processor_name": data_dict["processor_name"],
                "configuration_status": data_dict["configuration_status"],
                "is_official_specification": data_dict["is_official_specification"],
                "physical_qubits": physical_qubits,
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
                "is_supported": is_supported,
                "orig_depth": logical_qc.depth(),
                "orig_2q_gates": count_two_qubit_gates(logical_qc),
                "transpiled_depth": t_depth,
                "transpiled_2q_gates": t_2q,
                "transpiled_swap_count": t_swap,
                "swap_overhead": s_overhead,
                "transpiled_cx_count": t_cx,
                "transpilation_time_sec": t_time,
                "notes": notes,
            }
            results_data.append(record)


    df = pd.DataFrame(results_data)

    if output_csv:
        _save_csv_dual(df, output_csv)

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
                    "transpiled_cx_count": t_metrics["transpiled_cx_count"],
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
                    "transpiled_cx_count": None,
                    "transpilation_time_sec": 0.0,
                    "notes": f"Unsupported: logical qubits ({n}) exceed physical capacity ({physical_qubits})",
                }

            sweep_records.append(record)

    df = pd.DataFrame(sweep_records)

    if output_csv:
        _save_csv_dual(df, output_csv)

    return df


def run_processor_ab_noisy_comparison(
    graph: nx.Graph,
    p_list: Sequence[int] = (1, 2),
    optimization_level: int = 1,
    shots_ideal: int = 1000,
    shots_noisy: int = 4096,
    maxiter: int = 25,
    seed_simulator: int = 42,
    seed_transpiler: int = 42,
    p1q: float = 0.001,
    p2q: float = 0.005,
    p_ro: float = 0.01,
    noisy_1q_gates: Sequence[str] = ("sx", "x"),
    output_csv: str = "results/tables/processor_ab_noisy_comparison.csv",
) -> pd.DataFrame:
    """Benchmark QAOA under synthetic noise on Processor A and Processor B.

    Evaluates the exact same pre-optimized logical QAOA parameters (gamma*, beta*)
    on both processors' transpiled circuits with synthetic noise models attached.
    Applies identical noise rates to isolate hardware connectivity effects.

    Args:
        graph: NetworkX problem graph.
        p_list: QAOA depths to evaluate.
        optimization_level: Transpiler optimization level (default 1).
        shots_ideal: Shots for ideal optimization (default 1000).
        shots_noisy: Shots for noisy circuit evaluation (default 4096).
        maxiter: Iterations for ideal classical optimization.
        seed_simulator: Simulator random seed.
        seed_transpiler: Transpiler routing random seed.
        p1q: Single-qubit depolarizing error probability (default 0.001).
        p2q: Two-qubit CX depolarizing error probability (default 0.005).
        p_ro: Symmetric readout bit-flip probability (default 0.01).
        noisy_1q_gates: Names of single-qubit gates receiving p1q noise.
        output_csv: Path to output CSV.

    Returns:
        pd.DataFrame: Table comparing ideal vs noisy performance metrics.
    """
    validate_graph(graph)
    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()

    exact_max_cut, _, all_optimal_partitions = solve_max_cut_brute_force(graph)
    dev_processors = load_development_processors()
    noise_model = build_synthetic_noise_model(
        p1q=p1q, p2q=p2q, p_ro=p_ro, noisy_1q_gates=noisy_1q_gates
    )

    records = []

    for p in p_list:
        # 1. Ideal QAOA optimization (noiseless baseline)
        opt_params, opt_exp_cut, final_counts = optimize_qaoa(
            graph=graph,
            p=p,
            maxiter=maxiter,
            shots=shots_ideal,
            seed=seed_simulator,
        )
        opt_gamma = opt_params[:p]
        opt_beta = opt_params[p:]

        _, best_cut_ideal, _ = get_most_frequent_partition(final_counts, graph)
        opt_prob_ideal = calculate_optimal_probability(
            final_counts, graph, all_optimal_partitions
        )
        approx_ratio_ideal = float(opt_exp_cut / exact_max_cut)

        # 2. Evaluate on Processor A and Processor B
        for pid, (data_dict, cm, desc_label) in dev_processors.items():
            physical_qubits = data_dict["num_qubits"]
            is_supported = num_nodes <= physical_qubits

            if is_supported:
                noisy_res = run_noisy_transpiled_qaoa(
                    graph=graph,
                    opt_gamma=opt_gamma,
                    opt_beta=opt_beta,
                    p=p,
                    coupling_map=cm,
                    noise_model=noise_model,
                    shots=shots_noisy,
                    optimization_level=optimization_level,
                    seed_transpiler=seed_transpiler,
                    seed_simulator=seed_simulator,
                )

                t_depth = noisy_res["transpiled_depth"]
                t_cx = noisy_res["transpiled_cx_count"]
                n_exp_cut = noisy_res["noisy_expected_cut"]
                n_best_cut = noisy_res["noisy_best_sampled_cut"]
                n_approx = noisy_res["noisy_approx_ratio"]
                n_opt_prob = noisy_res["noisy_optimal_solution_prob"]
                drop = round(float(opt_exp_cut - n_exp_cut), 4)
                retention = round(float(n_exp_cut / opt_exp_cut), 4)
                notes = "Supported noisy development simulation"
            else:
                t_depth = None
                t_cx = None
                n_exp_cut = None
                n_best_cut = None
                n_approx = None
                n_opt_prob = None
                drop = None
                retention = None
                notes = f"Unsupported: logical qubits ({num_nodes}) exceed physical capacity ({physical_qubits})"

            rec = {
                "processor_id": data_dict["processor_id"],
                "processor_name": data_dict["processor_name"],
                "physical_qubits": physical_qubits,
                "logical_qubits": num_nodes,
                "edges": num_edges,
                "qaoa_depth_p": p,
                "is_supported": is_supported,
                "ideal_shots": shots_ideal,
                "noisy_shots": shots_noisy,
                "p1q_error": p1q,
                "p2q_cx_error": p2q,
                "readout_error": p_ro,
                "noisy_1q_gates": str(list(noisy_1q_gates)),
                "exact_max_cut_value": round(exact_max_cut, 4),
                "opt_expected_cut": round(opt_exp_cut, 4),
                "ideal_expected_cut": round(opt_exp_cut, 4),
                "ideal_approx_ratio": round(approx_ratio_ideal, 4),
                "ideal_best_sampled_cut": round(best_cut_ideal, 4),
                "ideal_optimal_prob": round(opt_prob_ideal, 4),
                "transpiled_depth": t_depth,
                "transpiled_cx_count": t_cx,
                "noisy_expected_cut": n_exp_cut,
                "noisy_approx_ratio": n_approx,
                "noisy_best_sampled_cut": n_best_cut,
                "noisy_optimal_prob": n_opt_prob,
                "expectation_drop": drop,
                "solution_quality_retention": retention,
                "quality_retention": retention,
                "notes": notes,
            }
            records.append(rec)

    df = pd.DataFrame(records)

    if output_csv:
        _save_csv_dual(df, output_csv)

    return df
