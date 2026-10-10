"""Visualization module for QAOA Max-Cut benchmark results, hardware transpilation metrics, and SWAP overhead analysis."""

import os
from typing import Sequence
import matplotlib.pyplot as plt
import pandas as pd


def _shorten_layout_name(name: str) -> str:
    """Helper function to clean long layout names for concise chart labels."""
    if "Linear" in name:
        return "Linear Chain"
    elif "Ring" in name:
        return "Ring Layout"
    elif "Grid" in name:
        return "2D Grid"
    elif "Fully Connected" in name or "all-to-all" in name:
        return "Fully Connected"
    return name.split("(")[0].strip()


def validate_dataframe_columns(df: pd.DataFrame, required_columns: Sequence[str], file_label: str) -> None:
    """Validate that a DataFrame contains all required columns."""
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns {missing} in {file_label}. "
            f"Available columns: {list(df.columns)}"
        )


def plot_transpilation_depth(
    df: pd.DataFrame,
    output_path: str = "results/plots/transpilation_depth.png",
) -> str:
    """Plot original vs. transpiled circuit depth across development coupling layouts.

    Args:
        df: Benchmark DataFrame (from transpilation_metrics.csv or qaoa_benchmark_results.csv).
        output_path: Target PNG file path under results/plots/.

    Returns:
        str: Absolute or relative file path of the saved plot.
    """
    required_cols = ["layout_name", "orig_depth", "transpiled_depth"]
    validate_dataframe_columns(df, required_cols, "transpilation depth data")

    # Aggregate by layout_name and QAOA depth p if available
    df_plot = df.copy()
    df_plot["clean_layout"] = df_plot["layout_name"].apply(_shorten_layout_name)

    plt.figure(figsize=(9, 5))

    # Group by layout and compute mean depths across optimization levels/depths
    grouped = df_plot.groupby("clean_layout", sort=False)[["orig_depth", "transpiled_depth"]].mean()

    layouts = grouped.index.tolist()
    orig_depths = grouped["orig_depth"].tolist()
    transpiled_depths = grouped["transpiled_depth"].tolist()

    x = range(len(layouts))
    width = 0.35

    plt.bar([i - width / 2 for i in x], orig_depths, width, label="Logical Depth (Original)", color="#4C72B0")
    plt.bar([i + width / 2 for i in x], transpiled_depths, width, label="Hardware Transpiled Depth", color="#DD8452")

    plt.title(
        "Circuit Depth Across Development Topologies\n(Note: Development Examples, Not Official Hardware)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    plt.xlabel("Development Coupling Layout", fontsize=10, fontweight="bold")
    plt.ylabel("Circuit Depth", fontsize=10, fontweight="bold")
    plt.xticks(x, layouts, fontsize=9)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.legend(fontsize=9)
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def plot_swap_and_gate_overhead(
    df: pd.DataFrame,
    output_path: str = "results/plots/swap_gate_overhead.png",
) -> str:
    """Plot original 2-qubit gates, transpiled 2-qubit gates, and SWAP overhead by topology.

    Args:
        df: Benchmark DataFrame.
        output_path: Target PNG file path under results/plots/.

    Returns:
        str: Saved plot file path.
    """
    required_cols = ["layout_name", "orig_2q_gates", "transpiled_2q_gates", "swap_overhead"]
    validate_dataframe_columns(df, required_cols, "gate overhead data")

    df_plot = df.copy()
    df_plot["clean_layout"] = df_plot["layout_name"].apply(_shorten_layout_name)

    grouped = df_plot.groupby("clean_layout", sort=False)[
        ["orig_2q_gates", "transpiled_2q_gates", "swap_overhead"]
    ].mean()

    layouts = grouped.index.tolist()
    orig_2q = grouped["orig_2q_gates"].tolist()
    transpiled_2q = grouped["transpiled_2q_gates"].tolist()
    swaps = grouped["swap_overhead"].tolist()

    x = range(len(layouts))
    width = 0.25

    plt.figure(figsize=(10, 5))

    plt.bar([i - width for i in x], orig_2q, width, label="Original 2-Qubit Gates", color="#55A868")
    plt.bar(x, transpiled_2q, width, label="Transpiled 2-Qubit Gates", color="#C44E52")
    plt.bar([i + width for i in x], swaps, width, label="Routing SWAP Overhead", color="#8172B0")

    plt.title(
        "Two-Qubit Gates & SWAP Overhead by Development Layout\n(Development Examples)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    plt.xlabel("Development Coupling Layout", fontsize=10, fontweight="bold")
    plt.ylabel("Gate Count", fontsize=10, fontweight="bold")
    plt.xticks(x, layouts, fontsize=9)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.legend(fontsize=9)
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def plot_qaoa_performance_by_depth(
    df: pd.DataFrame,
    output_path: str = "results/plots/qaoa_performance_by_depth.png",
) -> str:
    """Plot expected cut value, approximation ratio, and optimal solution probability vs QAOA depth p.

    Args:
        df: DataFrame from qaoa_benchmark_results.csv.
        output_path: Target PNG file path under results/plots/.

    Returns:
        str: Saved plot file path.
    """
    required_cols = [
        "qaoa_depth_p",
        "exact_max_cut_value",
        "opt_expected_cut",
        "approx_ratio_expected",
        "optimal_solution_prob",
    ]
    validate_dataframe_columns(df, required_cols, "QAOA performance benchmark data")

    # Group by QAOA depth p
    grouped = df.groupby("qaoa_depth_p")[
        ["exact_max_cut_value", "opt_expected_cut", "approx_ratio_expected", "optimal_solution_prob"]
    ].mean()

    p_values = grouped.index.tolist()
    exact_cuts = grouped["exact_max_cut_value"].tolist()
    opt_expected_cuts = grouped["opt_expected_cut"].tolist()
    approx_ratios = grouped["approx_ratio_expected"].tolist()
    optimal_probs = grouped["optimal_solution_prob"].tolist()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Subplot 1: Expected Cut Value vs Ground Truth
    ax1.plot(p_values, exact_cuts, "r--", marker="o", label="Exact Ground Truth Cut", linewidth=2)
    ax1.plot(p_values, opt_expected_cuts, "b-", marker="s", label="QAOA Expected Cut <C>", linewidth=2)
    ax1.set_title("Expected Cut Value vs QAOA Depth p", fontweight="bold", fontsize=11)
    ax1.set_xlabel("QAOA Depth p", fontweight="bold")
    ax1.set_ylabel("Cut Value", fontweight="bold")
    ax1.set_xticks(p_values)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend()

    # Subplot 2: Approximation Ratio & Optimal Solution Sampling Probability
    ax2.plot(p_values, approx_ratios, "g-", marker="^", label="Approximation Ratio <C>/C_max", linewidth=2)
    ax2.plot(p_values, optimal_probs, "m-", marker="d", label="Optimal Solution Prob", linewidth=2)
    ax2.set_title("Approximation Ratio & Optimal Prob vs Depth p", fontweight="bold", fontsize=11)
    ax2.set_xlabel("QAOA Depth p", fontweight="bold")
    ax2.set_ylabel("Ratio / Probability", fontweight="bold")
    ax2.set_ylim(0, 1.05)
    ax2.set_xticks(p_values)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend()

    plt.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()

    return output_path


def generate_all_plots(
    qaoa_benchmark_csv: str = "results/qaoa_benchmark_results.csv",
    transpilation_csv: str = "results/transpilation_metrics.csv",
    output_dir: str = "results/plots",
) -> list[str]:
    """Load benchmark CSVs and generate all publication-quality comparison charts.

    Args:
        qaoa_benchmark_csv: Path to qaoa_benchmark_results.csv.
        transpilation_csv: Path to transpilation_metrics.csv.
        output_dir: Target directory for plot PNG files.

    Returns:
        list[str]: List of created image file paths.
    """
    created_files = []
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate plots from qaoa_benchmark_results.csv if present
    if os.path.exists(qaoa_benchmark_csv):
        df_bench = pd.read_csv(qaoa_benchmark_csv)
        p1 = plot_qaoa_performance_by_depth(
            df_bench, os.path.join(output_dir, "qaoa_performance_by_depth.png")
        )
        created_files.append(p1)

        p2 = plot_transpilation_depth(
            df_bench, os.path.join(output_dir, "transpilation_depth.png")
        )
        created_files.append(p2)

        p3 = plot_swap_and_gate_overhead(
            df_bench, os.path.join(output_dir, "swap_gate_overhead.png")
        )
        created_files.append(p3)

    # 2. Alternatively / additionally plot from transpilation_metrics.csv
    elif os.path.exists(transpilation_csv):
        df_trans = pd.read_csv(transpilation_csv)
        p2 = plot_transpilation_depth(
            df_trans, os.path.join(output_dir, "transpilation_depth.png")
        )
        created_files.append(p2)

        p3 = plot_swap_and_gate_overhead(
            df_trans, os.path.join(output_dir, "swap_gate_overhead.png")
        )
        created_files.append(p3)
    else:
        raise FileNotFoundError(
            f"Neither benchmark CSV ({qaoa_benchmark_csv}) nor transpilation CSV ({transpilation_csv}) was found."
        )

    return created_files
