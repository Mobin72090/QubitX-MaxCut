# QubitX-MaxCut: QAOA for Weighted Max-Cut & SWAP Bottleneck Analysis

**Qiskit Fall Fest 2026 — Phase 1 Hackathon**  
**Team:** QubitX  
**Track:** Quantum Optimization  
**Problem:** PS-O1 — Max-Cut on Weighted Graphs  

---

## 📌 Project Overview

This repository provides a modular, reproducible Qiskit workflow for solving **Weighted Max-Cut** problems using the **Quantum Approximate Optimization Algorithm (QAOA)**. It features an exact ground-truth solver, parameterized QAOA circuit builder, hardware transpilation pass analysis, and automated benchmarking across multiple hardware coupling topologies and scaling graph sizes.

> **Note on Processor Data:**  
> Hardware configurations in `processors/` (`processor_a_dev.json` and `processor_b_dev.json`) are provisional development examples used for SWAP bottleneck analysis. They are designed to be easily replaced when official Processor A and Processor B specs are provided by hackathon organizers.

---

## 📁 Repository Structure

```text
QubitX-MaxCut/
├── README.md                           # Project overview & quickstart guide
├── TECHNICAL_REPORT.md                 # Comprehensive hackathon technical submission
├── requirements.txt                    # Exact pinned Python dependencies
├── .gitignore                          # Version control ignore rules
├── processors/                         # Processor configuration specs
│   ├── README.md                       # Schema & instructions for official JSON specs
│   ├── processor_a_dev.json            # Provisional 5-qubit tree topology
│   └── processor_b_dev.json            # Provisional 7-qubit Heavy-Hex sub-unit topology
├── results/                            # Output directory for CSV metrics & charts
│   ├── qaoa_benchmark_results.csv      # 4-node QAOA solution quality & topology metrics
│   ├── transpilation_metrics.csv       # Transpilation-only bottleneck data
│   ├── processor_ab_development_results.csv # Processor A/B benchmark comparison
│   ├── graph_size_routing_sweep.csv   # Graph capacity & scaling routing sweep (5, 6, 7 nodes)
│   └── plots/                          # 300 DPI benchmark plots
│       ├── qaoa_performance_by_depth.png
│       ├── transpilation_depth.png
│       └── swap_gate_overhead.png
└── src/                                # Core modular Python package
    ├── __init__.py
    ├── graph_utils.py                  # Weighted graph creation & brute-force exact solver
    ├── qaoa_builder.py                 # QAOA circuit builder, expectation value & COBYLA optimizer
    ├── transpilation.py                # Coupling map generators & transpilation pass analyzer
    ├── processors.py                   # Processor JSON configuration loader, validator & layout inspector
    ├── benchmarking.py                 # Automated benchmark suite runner & routing sweep engine
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

### 2. Run Processor A & Processor B Comparison
```powershell
python -c "from src.graph_utils import create_sample_graph; from src.benchmarking import run_processor_ab_benchmark; g = create_sample_graph(); df = run_processor_ab_benchmark(g, p_list=[1, 2]); print(df[['processor_id', 'physical_qubits', 'qaoa_depth_p', 'transpiled_depth', 'swap_overhead']])"
```

### 3. Run Graph-Size Routing Sweep (5, 6, 7 Nodes)
```powershell
python -c "from src.benchmarking import run_graph_size_routing_sweep; df = run_graph_size_routing_sweep(node_counts=[5, 6, 7], p=1); print(df[['logical_nodes', 'processor_id', 'physical_qubits', 'is_supported', 'transpiled_depth', 'swap_overhead']])"
```

### 4. Generate All Visualization Charts
```powershell
python -c "from src.visualization import generate_all_plots; generate_all_plots()"
```
Charts will be saved to `results/plots/`.

---

## 📊 Key Benchmark Findings

- **Exact Max-Cut Ground Truth (4-Node Dev Graph)**: `7.0` (Partitions `{0:0, 1:1, 2:0, 3:0}` and `{0:1, 1:0, 2:1, 3:1}`).
- **QAOA Depth \(p=1\)**: Expected cut \(\langle C \rangle = 6.006\) (Approximation ratio **85.8%**), sampling optimal partition with **23.1%** probability.
- **Processor Capacity & Routing Sweep Scaling**:
  - **5 Logical Nodes**: Both `processor_a_dev` (5 qubits) and `processor_b_dev` (7 qubits) supported (Transpiled Depth = 11, SWAP Overhead = 3).
  - **6 Logical Nodes**: `processor_a_dev` **unsupported by capacity** (6 > 5); `processor_b_dev` supported (Transpiled Depth = 16, SWAP Overhead = 4).
  - **7 Logical Nodes**: `processor_a_dev` **unsupported by capacity** (7 > 5); `processor_b_dev` supported (Transpiled Depth = 17, SWAP Overhead = 5).

---

## 📜 Technical Submission Report

For complete mathematical formulations, transpilation analyses, and experimental trade-off discussions, see [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md).
