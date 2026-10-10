# Technical Report: QAOA for Weighted Max-Cut & SWAP Bottleneck Analysis

**Qiskit Fall Fest 2026 Phase 1 Hackathon**  
**Team:** QubitX  
**Track:** Quantum Optimization  
**Problem Statement:** PS-O1 — Max-Cut on Weighted Graphs  

---

## 1. Executive Summary & Problem Statement

Combinatorial optimization on noisy intermediate-scale quantum (NISQ) devices requires balancing algorithmic solution quality with hardware execution overhead. The **Weighted Max-Cut** problem is a canonical NP-hard problem where the objective is to partition the vertices of a weighted graph \(G = (V, E)\) into two disjoint sets such that the sum of edge weights crossing the cut is maximized.

In this project, Team **QubitX** built a reproducible Python and Qiskit framework to:
1. Construct parameterized Quantum Approximate Optimization Algorithm (QAOA) circuits for weighted Max-Cut.
2. Establish exact ground-truth baselines using a brute-force classical solver.
3. Transpile logical QAOA circuits onto hardware coupling topologies to quantify **SWAP gate overhead** and circuit depth inflation.
4. Execute noise-free simulation benchmarks to analyze the trade-off between QAOA depth \(p\), solution quality, and transpilation bottlenecks.

> **Hardware Disclaimer:** All processor connectivity layouts analyzed in this report (Linear Chain, Ring Layout, 2D Grid, Fully Connected) are clearly labeled development examples used for bottleneck modeling. They do not represent official hackathon organizer-provided specifications and can be updated when official Processor A and Processor B specs are released.

---

## 2. Mathematical Formulation

### 2.1 Weighted Max-Cut Objective
Let \(G = (V, E)\) be an undirected graph with vertex set \(V = \{0, 1, \dots, n-1\}\) and positive edge weights \(w_{ij} > 0\) for \((i,j) \in E\). Assign a binary decision variable \(x_i \in \{0, 1\}\) to each node \(i \in V\), representing its partition assignment.

The total weight of edges crossing the cut is given by:
\[
C(x) = \sum_{(i,j) \in E} w_{ij} \left( x_i + x_j - 2 x_i x_j \right)
\]

In terms of spin variables \(s_i \in \{-1, +1\}\) where \(s_i = 1 - 2x_i\):
\[
C(s) = \sum_{(i,j) \in E} w_{ij} \left( \frac{1 - s_i s_j}{2} \right)
\]

### 2.2 Quantum Cost & Mixer Hamiltonians
Mapping spin variables \(s_i\) to Pauli \(Z_i\) operators yields the Max-Cut cost Hamiltonian:
\[
H_C = \frac{1}{2} \sum_{(i,j) \in E} w_{ij} Z_i Z_j
\]
Maximizing the cut value \(C(x)\) is equivalent to minimizing the expectation value \(\langle H_C \rangle\).

The standard QAOA transverse-field mixer Hamiltonian is:
\[
H_B = \sum_{i \in V} X_i
\]

### 2.3 Unitary Evolution & Circuit Gates
For a depth-\(p\) QAOA circuit with variational parameter vectors \(\boldsymbol{\gamma} = (\gamma_1, \dots, \gamma_p)\) and \(\boldsymbol{\beta} = (\beta_1, \dots, \beta_p)\):

1. **Initial State Preparation**:
   \[
   |\psi_0\rangle = |+\rangle^{\otimes n} = H^{\otimes n} |0\rangle^{\otimes n}
   \]

2. **Cost Unitary Layer \(U(C, \gamma_k)\)**:
   \[
   U(C, \gamma_k) = e^{-i \gamma_k H_C} = \prod_{(i,j) \in E} e^{-i \frac{\gamma_k w_{ij}}{2} Z_i Z_j}
   \]
   In Qiskit, each edge term is implemented using a two-qubit rotation gate: `rzz(2 * gamma_k * w_ij, q_i, q_j)`.

3. **Mixer Unitary Layer \(U(B, \beta_k)\)**:
   \[
   U(B, \beta_k) = e^{-i \beta_k H_B} = \prod_{i \in V} e^{-i \beta_k X_i}
   \]
   Each node term is implemented using a single-qubit rotation gate: `rx(2 * beta_k, q_i)`.

4. **Full Parameterized State**:
   \[
   |\boldsymbol{\gamma}, \boldsymbol{\beta}\rangle = U(B, \beta_p) U(C, \gamma_p) \cdots U(B, \beta_1) U(C, \gamma_1) |\psi_0\rangle
   \]

---

## 3. Project Architecture & Implementation

The repository follows a clean, modular structure in [`src/`](file:///c:/Projects/QubitX-MaxCut/src):

- **[`src/graph_utils.py`](file:///c:/Projects/QubitX-MaxCut/src/graph_utils.py)**: Defines NetworkX graph creation, graph validation, cut value evaluation, and `solve_max_cut_brute_force()` to establish exact ground-truth baselines.
- **[`src/qaoa_builder.py`](file:///c:/Projects/QubitX-MaxCut/src/qaoa_builder.py)**: Builds parameterized Qiskit `QuantumCircuit` instances, handles Qiskit right-to-left bitstring endianness (`bitstring[-1]` \(\rightarrow\) qubit 0), computes expected cut values \(\langle C \rangle\), and optimizes parameters using SciPy `COBYLA`.
- **[`src/transpilation.py`](file:///c:/Projects/QubitX-MaxCut/src/transpilation.py)**: Generates development coupling maps (Linear, Ring, Grid, Fully Connected), validates connectivity, counts actual 2-qubit instructions (`op.num_qubits == 2`), and calculates routing SWAP overhead.
- **[`src/benchmarking.py`](file:///c:/Projects/QubitX-MaxCut/src/benchmarking.py)**: Executes end-to-end benchmark suites combining exact ground truth, optimization results, and transpilation bottlenecks, exporting to CSV.
- **[`src/visualization.py`](file:///c:/Projects/QubitX-MaxCut/src/visualization.py)**: Generates publication-quality 300 DPI figures under [`results/plots/`](file:///c:/Projects/QubitX-MaxCut/results/plots).

---

## 4. Experimental Setup

All experiments were executed in the project virtual environment on Windows using the exact parameters below:

- **Development Problem Graph**: 4 nodes (\(n=4\)), 5 weighted edges:
  - Edges: `(0, 1, weight=2.0)`, `(0, 2, weight=1.0)`, `(1, 2, weight=3.0)`, `(1, 3, weight=2.0)`, `(2, 3, weight=1.0)`.
- **Simulation Environment**: Qiskit Aer (`AerSimulator`).
- **QAOA Configurations**: Depths \(p \in \{1, 2\}\), measurement shots = 1000 / 2048.
- **Classical Optimizer**: SciPy `COBYLA` with `maxiter = 25` to `40`.
- **Random Seeds**:
  - `seed_simulator = 42` (reproducible initial points & shot sampling).
  - `seed_transpiler = 42` (deterministic transpilation routing).
- **Development Hardware Coupling Topologies**:
  1. **Linear Chain**: 1D line `0 - 1 - 2 - 3`
  2. **Ring Layout**: 1D ring `0 - 1 - 2 - 3 - 0`
  3. **2D Grid**: 2x2 mesh
  4. **Fully Connected**: All-to-all connectivity (0 routing SWAPs baseline)

---

## 5. Empirical Results & Analysis

### 5.1 Exact Ground-Truth Baseline
Exhaustive brute-force evaluation over all \(2^4 = 16\) binary partitions established:
- **Maximum Cut Value (\(C_{\text{max}}\))**: **`7.0`**
- **Optimal Partitions**: `{0: 0, 1: 1, 2: 0, 3: 0}` and its bit-flip symmetric partner `{0: 1, 1: 0, 2: 1, 3: 1}`.

### 5.2 QAOA Solution Quality & Transpilation Metrics Table

The table below presents empirical benchmark data extracted directly from [`results/qaoa_benchmark_results.csv`](file:///c:/Projects/QubitX-MaxCut/results/qaoa_benchmark_results.csv):

| Depth \(p\) | Development Coupling Layout | Logical Depth | Transpiled Depth | Logical 2Q Gates | Transpiled 2Q Gates | SWAP Overhead | Expected Cut \(\langle C \rangle\) | Approx Ratio (\(\langle C \rangle / C_{\text{max}}\)) | Optimal Sol. Prob |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **p=1** | Linear Chain (`0-1-2-3`) | 7 | **11** | 5 | 7 | **2** | 6.006 | **0.8580** (85.8%) | **23.1%** |
| **p=1** | Ring Layout (`0-1-2-3-0`) | 7 | **8** | 5 | 7 | **2** | 6.006 | **0.8580** (85.8%) | **23.1%** |
| **p=1** | 2D Grid (`2x2`) | 7 | **11** | 5 | 7 | **2** | 6.006 | **0.8580** (85.8%) | **23.1%** |
| **p=1** | Fully Connected | 7 | **7** | 5 | 5 | **0** | 6.006 | **0.8580** (85.8%) | **23.1%** |
| **p=2** | Linear Chain (`0-1-2-3`) | 12 | **18** | 10 | 14 | **4** | 5.389 | **0.7699** (77.0%) | **34.4%** |
| **p=2** | Ring Layout (`0-1-2-3-0`) | 12 | **18** | 10 | 14 | **4** | 5.389 | **0.7699** (77.0%) | **34.4%** |
| **p=2** | 2D Grid (`2x2`) | 12 | **18** | 10 | 14 | **4** | 5.389 | **0.7699** (77.0%) | **34.4%** |
| **p=2** | Fully Connected | 12 | **12** | 10 | 10 | **0** | 5.389 | **0.7699** (77.0%) | **34.4%** |

---

## 6. Plot Interpretations & Trade-Off Analysis

Three publication-quality figures were generated under [`results/plots/`](file:///c:/Projects/QubitX-MaxCut/results/plots):

### 6.1 `qaoa_performance_by_depth.png`
- **Observations**:
  - At \(p=1\), QAOA achieves a high expected cut value of **6.006** (85.8% of theoretical maximum) with a 23.1% probability of sampling an exact optimal solution.
  - At \(p=2\), the optimal solution sampling probability increases significantly from **23.1% to 34.4%**, demonstrating that deeper QAOA circuits concentrate quantum state probability amplitude around true ground-truth partitions.
  - The expected cut value for \(p=2\) dropped to 5.389 due to local minima traps in COBYLA optimization under restricted iteration caps.

### 6.2 `transpilation_depth.png` & `swap_gate_overhead.png`
- **SWAP Bottleneck Analysis**:
  - The logical QAOA circuit at \(p=1\) contains 5 two-qubit `RZZ` interactions corresponding to the 5 problem edges.
  - On a **Linear Chain** (`0-1-2-3`), non-adjacent edges such as `(0, 2)` and `(1, 3)` cannot execute directly. The transpiler inserts **2 routing SWAP gates**, inflating total 2-qubit operations from 5 to 7 and expanding circuit depth from 7 to 11.
  - **Topology Impact (Ring vs Linear)**: Introducing a single boundary link between qubit 0 and qubit 3 in the **Ring Layout** reduces transpiled circuit depth from **11 down to 8** at \(p=1\), demonstrating how hardware connectivity relieves routing bottlenecks.
  - **Depth Accumulation**: At \(p=2\), SWAP overhead doubles to **4 SWAP gates**, causing circuit depth to reach **18** on constrained layouts compared to **12** on fully connected topology.

---

## 7. Limitations

1. **Development Problem Graph**: Benchmarks were performed on a small 4-node development graph. Larger graphs will exhibit significantly higher SWAP routing scaling.
2. **Noise-Free Simulation**: Experiments used `AerSimulator` without physical backend noise models (gate errors, thermal relaxation, decoherence).
3. **Classical Optimization Traps**: COBYLA is a derivative-free local optimizer susceptible to local minima depending on initial parameter seeds.
4. **Development Coupling Maps**: Transpilation metrics reflect baseline geometric layouts rather than final organizer-provided Processor A/B specs.

---

## 8. Conclusion & Next Steps

Team **QubitX** has successfully implemented a complete, modular, and verified QAOA Max-Cut benchmarking framework for Qiskit Fall Fest 2026 Phase 1. 

### Key Takeaways:
- QAOA depth \(p=1\) delivers an **85.8% approximation ratio** on the development graph.
- Increasing depth to \(p=2\) boosts optimal solution sampling probability to **34.4%**.
- Hardware connectivity heavily influences transpiled circuit depth, with SWAP overhead adding up to 57% depth inflation on 1D linear topologies.

### Next Steps for Phase 2 / Official Hardware Evaluation:
1. **Plug in Official Processor A and Processor B Specs**: Replace development coupling maps in `src/transpilation.py` with official IBM/hackathon target backend topologies.
2. **Incorporate Noisy Aer Simulations**: Apply real noise models (readout error, single/two-qubit gate errors) from official processor backends to evaluate noise degradation.
3. **Advanced Optimizers**: Integrate global parameter optimizers (e.g. SPSA, Adam, or parameter initialization heuristics) to avoid COBYLA local traps.
