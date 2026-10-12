# QubitX-MaxCut: QAOA for Weighted Max-Cut & SWAP Bottleneck Analysis

**Qiskit Fall Fest 2026 — Phase 1 Hackathon**  
**Team:** QubitX  
**Track:** Quantum Optimization  
**Problem:** PS-O1 — Max-Cut on Weighted Graphs  

---

## 📌 Project Overview

This repository provides a modular, reproducible Qiskit workflow for solving **Weighted Max-Cut** problems using the **Quantum Approximate Optimization Algorithm (QAOA)**. It features an exact ground-truth solver, parameterized QAOA circuit builder, hardware transpilation pass analysis, and automated benchmarking across multiple hardware coupling topologies and scaling graph sizes.

> **Note on Processor Topologies & Synthetic Noise Model:**
> Hardware configurations in `processors/` (`processor_A.json` / `processor_a_dev.json` and `processor_B.json` / `processor_b_dev.json`) reflect the authoritative topologies from the Challenge Kit (`Processor_AB_Benchmark_Configuration_FINAL.pdf`): 5-qubit tree topology for Processor A, and 9-qubit Heavy-Hex topology for Processor B.
> Alongside ideal/noiseless simulations, synthetic noise evaluation implements the official **Qiskit Fall Fest 2026 Master Guide** calibration: 1-qubit depolarizing error $p_{1q} = 0.001$ on physical microwave pulses (`sx`, `x`), 2-qubit CX depolarizing error $p_{2q} = 0.005$, and symmetric readout error $p_{ro} = 0.01$. Basis gates are `['rz', 'sx', 'x', 'cx']` (with virtual $R_Z$ rotations modeled error-free). All benchmarks are development simulations executed on `AerSimulator` and do not represent physical hardware execution or official organizer approval.

---

## 📁 Repository Structure

```text
QubitX-MaxCut/
├── README.md                           # Project overview & quickstart guide
├── report.md                           # Full hackathon submission technical report
├── TECHNICAL_REPORT.md                 # Technical report copy for evaluation
├── main.ipynb                          # Executable Jupyter notebook end-to-end walkthrough
├── requirements.txt                    # Exact pinned Python dependencies
├── .gitignore                          # Version control ignore rules
├── processors/                         # Processor configuration specs
│   ├── README.md                       # Schema & notes on documented topologies
│   ├── processor_A.json                # Documented 5-qubit tree topology
│   ├── processor_B.json                # Documented 9-qubit Heavy-Hex topology
│   ├── processor_a_dev.json            # Backward-compatible alias for Processor A
│   └── processor_b_dev.json            # Backward-compatible alias for Processor B
├── results/                            # Output directory for CSV metrics & charts
│   ├── tables/                         # Formatted CSV benchmark tables
│   │   ├── qaoa_benchmark_results.csv
│   │   ├── transpilation_metrics.csv
│   │   ├── processor_ab_development_results.csv
│   │   ├── processor_ab_noisy_comparison.csv
│   │   ├── pso1_six_node_processor_ab.csv
│   │   └── graph_size_routing_sweep.csv
│   ├── figures/                        # 300 DPI benchmark plots
│   │   ├── qaoa_performance_by_depth.png
│   │   ├── transpilation_depth.png
│   │   └── swap_gate_overhead.png
│   └── plots/                          # Backward-compatible plot directory
├── tests/                              # Automated unit tests and verification checks
│   └── test_noise.py                   # Tests for noise rates, 4Q simulation, and 6Q capacity
└── src/                                # Core modular Python package
    ├── __init__.py
    ├── graph_utils.py                  # Weighted graph creation (4-node & PS-O1 6-node) & exact solver
    ├── qaoa_builder.py                 # QAOA circuit builder, expectation value & COBYLA optimizer
    ├── noise.py                        # Synthetic noise-model factory & noisy transpiled circuit runner
    ├── transpilation.py                # Coupling map generators & transpilation pass analyzer
    ├── processors.py                   # Processor JSON configuration loader, validator & layout inspector
    ├── benchmarking.py                 # Automated benchmark suite runner, noisy comparison & routing sweep
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

4. **Run Verification Test Suite**:
   ```powershell
   python -m unittest discover -s tests
   ```

---

## 🚀 Quickstart Usage

### 1. Run Brute-Force Baseline & QAOA Optimization (4-Node Problem)
```powershell
python -c "from src.graph_utils import create_sample_graph, solve_max_cut_brute_force; from src.qaoa_builder import optimize_qaoa; g = create_sample_graph(); val, part, _ = solve_max_cut_brute_force(g); print('Exact Cut:', val); opt_p, opt_exp, counts = optimize_qaoa(g, p=1); print('QAOA Expected Cut:', opt_exp)"
```

### 2. Run PS-O1 6-Node Instance Benchmark
```powershell
python -c "from src.graph_utils import create_pso1_6node_graph, solve_max_cut_brute_force; g = create_pso1_6node_graph(instance_id=1); val, part, _ = solve_max_cut_brute_force(g); print('Exact Cut (6 nodes):', val)"
```

### 3. Run Processor A (5Q) & Processor B (9Q) Comparison
```powershell
python -c "from src.graph_utils import create_sample_graph; from src.benchmarking import run_processor_ab_benchmark; g = create_sample_graph(); df = run_processor_ab_benchmark(g, p_list=[1, 2]); print(df[['processor_id', 'physical_qubits', 'qaoa_depth_p', 'transpiled_depth', 'swap_overhead']])"
```

### 4. Run Synthetic Noise-Model Evaluation (Master Guide Calibration)
```powershell
python -c "from src.graph_utils import create_sample_graph; from src.benchmarking import run_processor_ab_noisy_comparison; g = create_sample_graph(); df = run_processor_ab_noisy_comparison(g, p_list=[1, 2], shots_noisy=4096); print(df[['processor_id', 'qaoa_depth_p', 'opt_expected_cut', 'noisy_expected_cut', 'solution_quality_retention', 'transpiled_cx_count']])"
```

### 5. Run Graph-Size Routing Sweep (5, 6, 7 Nodes)
```powershell
python -c "from src.benchmarking import run_graph_size_routing_sweep; df = run_graph_size_routing_sweep(node_counts=[5, 6, 7], p=1); print(df[['logical_nodes', 'processor_id', 'physical_qubits', 'is_supported', 'transpiled_depth', 'swap_overhead']])"
```

### 6. Generate All Visualization Charts
```powershell
python -c "from src.visualization import generate_all_plots; generate_all_plots()"
```
Charts are saved to both `results/figures/` and `results/plots/`.

---

## 📊 Key Benchmark Findings

- **Exact Max-Cut Ground Truth**:
  - **4-Node Development Graph**: `7.0` (Partitions `{0:0, 1:1, 2:0, 3:0}` and `{0:1, 1:0, 2:1, 3:1}`).
  - **6-Node PS-O1 Instances (Weights 1–5)**:
    - Instance 1 (8 edges): **19.0** (4 optimal bitstrings).
    - Instance 2 (9 edges): **25.0** (2 optimal bitstrings).
    - Instance 3 (7 edges): **22.0** (2 optimal bitstrings).
- **4-Node QAOA Optimization & Hardware Routing (Ideal Simulation Benchmark)**:
  - Sourced directly from `results/tables/processor_ab_development_results.csv` (`shots = 2048`, `maxiter = 40`, `seed = 42`):
    - **p=1**: Expected cut \(\langle C \rangle = 5.9678\) (Approximation ratio **85.3%**).
      - `processor_A` (5Q Tree): High-level routed depth **11** (unmeasured native basis depth **39**), SWAP overhead **2**, CX count **16**.
      - `processor_B` (9Q Heavy-Hex): High-level routed depth **8** (unmeasured native basis depth **23**), SWAP overhead **1**, CX count **10**.
    - **p=2**: Expected cut \(\langle C \rangle = 5.5166\) (Approximation ratio **78.8%**).
      - `processor_A` (5Q Tree): High-level routed depth **18** (unmeasured native basis depth **62**), SWAP overhead **3**, CX count **29**.
      - `processor_B` (9Q Heavy-Hex): High-level routed depth **12** (unmeasured native basis depth **40**), SWAP overhead **0**, CX count **20**.
  - *(Note: In the 1000-shot / 25-iteration run used for synthetic noise evaluation in Section 5.4 and `main.ipynb`, ideal expected cuts evaluate to \(6.0060\) (85.80%) at \(p=1\) and \(5.3890\) (76.99%) at \(p=2\), with measured native basis depths of 40 / 24 and 63 / 41).*
- **Synthetic Noise-Model Evaluation ($p_{1q}=0.001$, $p_{2q}=0.005$, $p_{ro}=0.01$, 4,096 Shots)**:
  - **4-Node Graph at p=1** (Ideal \(\langle C \rangle = 6.006\)):
    - `processor_A` (16 CX): Noisy \(\langle C \rangle = 5.8074\), Approx Ratio **82.96%**, Expectation Drop **0.1986**, Quality Retention **96.69%**.
    - `processor_B` (10 CX): Noisy \(\langle C \rangle = 5.8660\), Approx Ratio **83.80%**, Expectation Drop **0.1400**, Quality Retention **97.67%**.
  - **4-Node Graph at p=2** (Ideal \(\langle C \rangle = 5.389\)):
    - `processor_A` (29 CX): Noisy \(\langle C \rangle = 5.1453\), Approx Ratio **73.50%**, Expectation Drop **0.2437**, Quality Retention **95.48%**.
    - `processor_B` (20 CX): Noisy \(\langle C \rangle = 5.2415\), Approx Ratio **74.88%**, Expectation Drop **0.1475**, Quality Retention **97.26%**.
  - **6-Node PS-O1 Instances**:
    - `processor_A`: **Unsupported by capacity limit** (6 nodes > 5 physical qubits); no metrics fabricated.
    - `processor_B`: Supported (Instance 1: 22 CX, noisy \(\langle C \rangle = 15.5554\), approx ratio **81.87%**, quality retention **95.91%**).
- **Hardware Capacity & Routing Sweep Scaling (5, 6, 7 Nodes)**:
  - **5 Logical Nodes**: Both `processor_A` (5Q) and `processor_B` (9Q) supported. Processor B achieves lower SWAPs (1 vs 3), lower depth (10 vs 11), and fewer CX gates (17 vs 23).
  - **6 Logical Nodes**: `processor_A` **unsupported by capacity** (6 > 5); `processor_B` supported (Transpiled Depth = 12, SWAP Overhead = 2, CX Count = 24).
  - **7 Logical Nodes**: `processor_A` **unsupported by capacity** (7 > 5); `processor_B` supported (Transpiled Depth = 12, SWAP Overhead = 2, CX Count = 26).

---

## 📜 Technical Submission Report & Walkthrough

- Full hackathon submission report: [report.md](report.md) / [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md).
- End-to-end interactive notebook walkthrough: [main.ipynb](main.ipynb).
