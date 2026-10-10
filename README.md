# QubitX-MaxCut: QAOA for Weighted Max-Cut & SWAP Bottleneck Analysis

**Qiskit Fall Fest 2026 — Phase 1 Hackathon**  
**Team:** QubitX  
**Track:** Quantum Optimization  
**Problem:** PS-O1 — Max-Cut on Weighted Graphs  

---

## 📌 Project Overview

This repository provides a modular, reproducible Qiskit workflow for solving **Weighted Max-Cut** problems using the **Quantum Approximate Optimization Algorithm (QAOA)**. It features an exact ground-truth solver, parameterized QAOA circuit builder, hardware transpilation pass analysis, and automated benchmarking across multiple hardware coupling topologies.

> **Note on Processor Data:**  
> Hardware layouts in this repository (Linear Chain, Ring, 2D Grid, Fully Connected) are development examples used for SWAP bottleneck analysis. They are designed to be easily replaced when official Processor A and Processor B specs are provided by hackathon organizers.

---

## 📁 Repository Structure

```text
QubitX-MaxCut/
├── README.md                           # Project overview & quickstart guide
├── TECHNICAL_REPORT.md                 # Comprehensive hackathon technical submission
├── requirements.txt                    # Exact pinned Python dependencies
├── processors/                         # Reserved for official Processor A/B JSON specs
├── results/                            # Output directory for CSV metrics & charts
│   ├── qaoa_benchmark_results.csv      # Solution quality & transpilation metrics
│   ├── transpilation_metrics.csv       # Transpilation-only bottleneck data
│   └── plots/                          # 300 DPI benchmark plots
│       ├── qaoa_performance_by_depth.png
│       ├── transpilation_depth.png
│       └── swap_gate_overhead.png
└── src/                                # Core modular Python package
    ├── __init__.py
    ├── graph_utils.py                  # Weighted graph creation & brute-force exact solver
    ├── qaoa_builder.py                 # QAOA circuit builder, expectation value & COBYLA optimizer
    ├── transpilation.py                # Development coupling map generators & transpilation pass analyzer
    ├── benchmarking.py                 # Automated benchmark suite runner
    └── visualization.py                # Publication-quality Matplotlib visualization routines
```

---

## ⚙️ Installation & Setup

1. **Clone & Open Project Directory**:
   ```powershell
   cd C:\Projects\QubitX-MaxCut
   ```

2. **Activate Virtual Environment**:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   .\venv\Scripts\Activate.ps1
   ```

3. **Verify Installed Dependencies**:
   ```powershell
   pip list
   ```

---

## 🚀 Quickstart Usage

### 1. Run Brute-Force Baseline & QAOA Optimization
```powershell
python -c "from src.graph_utils import create_sample_graph, solve_max_cut_brute_force; from src.qaoa_builder import optimize_qaoa; g = create_sample_graph(); val, part, _ = solve_max_cut_brute_force(g); print('Exact Cut:', val); opt_p, opt_exp, counts = optimize_qaoa(g, p=1); print('QAOA Expected Cut:', opt_exp)"
```

### 2. Run Transpilation Bottleneck Benchmarks
```powershell
python -c "from src.graph_utils import create_sample_graph; from src.transpilation import run_transpilation_benchmarks; g = create_sample_graph(); df = run_transpilation_benchmarks(g, p=1); print(df[['layout_name', 'orig_depth', 'transpiled_depth', 'swap_overhead']])"
```

### 3. Run Full QAOA Benchmark Suite
```powershell
python -c "from src.graph_utils import create_sample_graph; from src.benchmarking import run_qaoa_benchmark; g = create_sample_graph(); df = run_qaoa_benchmark(g, p_list=[1, 2]); print(df[['qaoa_depth_p', 'exact_max_cut_value', 'opt_expected_cut', 'optimal_solution_prob', 'layout_name', 'transpiled_depth', 'swap_overhead']])"
```

### 4. Generate All Visualization Charts
```powershell
python -c "from src.visualization import generate_all_plots; generate_all_plots()"
```
Charts will be saved to `results/plots/`.

---

## 📊 Key Benchmark Findings (Development Graph)

- **Exact Max-Cut Ground Truth**: `7.0` (Partitions `{0:0, 1:1, 2:0, 3:0}` and `{0:1, 1:0, 2:1, 3:1}`).
- **QAOA Depth \(p=1\)**: Expected cut \(\langle C \rangle = 6.006\) (Approximation ratio **85.8%**), sampling optimal partition with **23.1%** probability.
- **Hardware Bottlenecks**:
  - **Linear Chain**: Transpiled Depth = 11, SWAP Overhead = 2.
  - **Ring Layout**: Transpiled Depth = 8, SWAP Overhead = 2 (reduced depth due to boundary connection).
  - **Fully Connected**: Transpiled Depth = 7, SWAP Overhead = 0.

---

## 📜 Technical Submission Report

For complete mathematical formulations, transpilation analyses, and experimental trade-off discussions, see [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md).
