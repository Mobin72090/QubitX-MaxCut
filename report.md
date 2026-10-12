# Technical Report: QAOA for Weighted Max-Cut & SWAP Bottleneck Analysis

**Qiskit Fall Fest 2026 Phase 1 Hackathon**  
**Team:** QubitX  
**Track:** Quantum Optimization  
**Problem Statement:** PS-O1 — Max-Cut on Weighted Graphs  

---

## 1. Executive Summary & Core Hackathon Principle

The primary objective of Phase 1 is **not merely to report algorithm outputs**, but to demonstrate **how the exact same quantum optimization solution behaves across two distinct processor architectures**, using empirical, measured evidence to explain the performance differences.

In this project, Team **QubitX** implemented a modular Python and Qiskit framework to solve the **Weighted Max-Cut** problem using the **Quantum Approximate Optimization Algorithm (QAOA)**. By keeping all algorithmic variables strictly controlled (identical logical problem graph, QAOA depth \(p\), classical optimizer settings, measurement shots, simulator seed `42`, and transpiler seed `42`), we evaluated how circuit transpilation and routing SWAP bottlenecks behave on the two official Phase 1 hardware topologies documented in the Challenge Kit (`Processor_AB_Benchmark_Configuration_FINAL.pdf`):

1. **Processor A (`processors/processor_A.json`)**: Authoritative 5-qubit branching tree topology (`[[0, 1], [1, 2], [1, 3], [3, 4]]`).
2. **Processor B (`processors/processor_B.json`)**: Authoritative 9-qubit Heavy-Hex topology (`[[0, 1], [1, 2], [1, 6], [2, 3], [2, 6], [2, 5], [3, 4], [4, 5], [5, 6], [6, 7], [6, 8], [8, 0]]`).

> **Specification & Simulation Modes Status:**
> The physical coupling maps for Processor A (5 qubits) and Processor B (9 qubits) are verified directly from the authoritative Challenge Kit configuration. As noted in the Challenge Kit documentation, official hardware noise parameters (device calibration data, gate crosstalk, relaxation times) are not verified by processor map diagrams. Therefore, benchmarks in this report represent **ideal/noiseless simulator execution on Qiskit `AerSimulator`** (Sections 5.1–5.3), complemented by a dedicated **synthetic noise simulation** (Section 5.4) calibrated to the official QFF 2026 Master Guide ($p_{1q}=0.001$, $p_{2q}=0.005$, $p_{ro}=0.01$). **No physical quantum hardware execution or organizer approval is claimed.**

---

## 2. Mathematical Formulation

### 2.1 Weighted Max-Cut Objective
Let \(G = (V, E)\) be an undirected graph with vertex set \(V = \{0, 1, \dots, n-1\}\) and positive edge weights \(w_{ij} > 0\) for \((i,j) \in E\). Assign a binary decision variable \(x_i \in \{0, 1\}\) to each node \(i \in V\).

The total weight of edges crossing the cut is:
\[
C(x) = \sum_{(i,j) \in E} w_{ij} \left( x_i + x_j - 2 x_i x_j \right)
\]

In terms of spin variables \(s_i = 1 - 2x_i \in \{-1, +1\}\):
\[
C(s) = \sum_{(i,j) \in E} w_{ij} \left( \frac{1 - s_i s_j}{2} \right)
\]

### 2.2 Quantum Cost & Mixer Hamiltonians
Mapping spin variables \(s_i\) to Pauli \(Z_i\) operators yields the Max-Cut cost Hamiltonian:
\[
H_C = \frac{1}{2} \sum_{(i,j) \in E} w_{ij} Z_i Z_j
\]
Maximizing cut value \(C(x)\) corresponds to minimizing expectation value \(\langle H_C \rangle\).

The standard QAOA transverse-field mixer Hamiltonian is:
\[
H_B = \sum_{i \in V} X_i
\]

### 2.3 Unitary Evolution & Circuit Gates
For a depth-\(p\) QAOA circuit with parameter vectors \(\boldsymbol{\gamma} = (\gamma_1, \dots, \gamma_p)\) and \(\boldsymbol{\beta} = (\beta_1, \dots, \beta_p)\):

1. **Initial State**: \(|\psi_0\rangle = |+\rangle^{\otimes n} = H^{\otimes n} |0\rangle^{\otimes n}\).
2. **Cost Unitary \(U(C, \gamma_k)\)**: Implemented using Qiskit `rzz(2 * gamma_k * w_ij, q_i, q_j)` gates for each weighted edge.
3. **Mixer Unitary \(U(B, \beta_k)\)**: Implemented using Qiskit `rx(2 * beta_k, q_i)` gates for each node.
4. **State Vector**: \(|\boldsymbol{\gamma}, \boldsymbol{\beta}\rangle = U(B, \beta_p) U(C, \gamma_p) \cdots U(B, \beta_1) U(C, \gamma_1) |\psi_0\rangle\).

---

## 3. Project Architecture & Implementation

The repository follows a clean, modular structure in [`src/`](src/):

- **[`src/graph_utils.py`](src/graph_utils.py)**: Defines NetworkX graph creation (`create_sample_graph`, `create_pso1_6node_graph`, `create_synthetic_graph`), graph validation, cut value evaluation, and `solve_max_cut_brute_force()` to establish exact ground-truth baselines.
- **[`src/qaoa_builder.py`](src/qaoa_builder.py)**: Builds parameterized Qiskit `QuantumCircuit` instances, handles Qiskit right-to-left bitstring endianness (`bitstring[-1]` \(\rightarrow\) qubit 0), computes expected cut values \(\langle C \rangle\), and optimizes parameters using SciPy `COBYLA`.
- **[`src/processors.py`](src/processors.py)**: Loads JSON processor specifications (`processors/processor_A.json`, `processors/processor_B.json`), validates node range/self-loops/duplicates/connectivity, converts to bidirectional Qiskit `CouplingMap`s, and provides layout inspection diagnostics (`inspect_processor_transpilation_layouts`).
- **[`src/transpilation.py`](src/transpilation.py)**: Generates coupling maps, validates connectivity, counts actual 2-qubit instructions (`op.num_qubits == 2`), exports basis gates `DOCUMENTED_BASIS_GATES = ['rz', 'sx', 'x', 'cx']`, and calculates routing SWAP overhead.
- **[`src/noise.py`](src/noise.py)**: Provides a reusable noise-model factory calibrated to the QFF 2026 Master Guide ($p_{1q}=0.001$, $p_{2q}=0.005$, $p_{ro}=0.01$) and executes transpiled physical circuits under synthetic noise.
- **[`src/benchmarking.py`](src/benchmarking.py)**: Executes end-to-end benchmark suites (`run_qaoa_benchmark`, `run_processor_ab_benchmark`, `run_processor_ab_noisy_comparison`, `run_graph_size_routing_sweep`), exporting to CSV.
- **[`src/visualization.py`](src/visualization.py)**: Generates publication-quality 300 DPI figures under `results/figures/` and `results/plots/`.

---

## 4. Controlled Experimental Setup

To ensure valid comparative evidence, parameters were held strictly constant across experiments:

- **Problem Instances**:
  1. **Development Instance (4 nodes, 5 edges)**: Edge weights in \(\{1.0, 2.0, 3.0\}\). Exact ground-truth cut = **7.0**.
  2. **Official PS-O1 Specification Instances (6 nodes, integer weights 1–5)** (independently verified via exhaustive enumeration of all 64 bitstrings):
     - Instance 1 (6 nodes, 8 edges, weights \(\{2, 4, 1, 5, 3, 2, 4, 1\}\)): Exact ground-truth cut = **19.0** (4 optimal bitstrings: `001100`, `011001`, `100110`, `110011`).
     - Instance 2 (6 nodes, 9 edges, weights \(\{3, 2, 5, 1, 4, 2, 3, 1, 4\}\)): Exact ground-truth cut = **25.0** (2 optimal bitstrings: `010101`, `101010`).
     - Instance 3 (6 nodes, 7 edges, weights \(\{5, 4, 3, 2, 1, 4, 3\}\)): Exact ground-truth cut = **22.0** (2 optimal bitstrings: `010101`, `101010`).
  3. **Synthetic Scaling Sweep Graphs (5, 6, 7 nodes)**: Connected graphs with seed `42`.
- **Simulation Engine**: Qiskit Aer (`AerSimulator`, in ideal/noiseless mode and calibrated synthetic-noise mode).
- **Optimization Strategy**: SciPy `COBYLA` with deterministic seeds.
- **Random Seeds**:
  - `seed_simulator = 42` (reproducible initial points & shot sampling).
  - `seed_transpiler = 42` (deterministic transpilation routing).
- **Hardware Topologies & Basis Gate Set**:
  - `processors/processor_A.json`: 5 physical qubits, tree topology (`[[0, 1], [1, 2], [1, 3], [3, 4]]`).
  - `processors/processor_B.json`: 9 physical qubits, Heavy-Hex topology (`[[0, 1], [1, 2], [1, 6], [2, 3], [2, 6], [2, 5], [3, 4], [4, 5], [5, 6], [6, 7], [6, 8], [8, 0]]`).
  - Documented Native Basis Gate Set: `['cx', 'rz', 'sx', 'x']` (as specified in Universal Challenge Framework).

---

## 5. Measured Comparative Evidence

### 5.1 Case 1: 4-Node Problem Graph Comparison (Ideal Simulation Benchmark)

Extracted directly from [`results/tables/processor_ab_development_results.csv`](results/tables/processor_ab_development_results.csv):
*(Benchmark configuration: Ideal noiseless simulation on `AerSimulator`, `shots = 2048`, `maxiter = 40`, `seed_simulator = 42`, `seed_transpiler = 42`, `optimization_level = 1`)*

| QAOA Depth \(p\) | Processor ID | Physical Qubits (\(N\)) | Logical Qubits (\(n\)) | Transpiled Depth (Routed / Native Basis) | Logical 2Q Gates | Transpiled 2Q Gates (RZZ+SWAP) | Transpiled CX Count | SWAP Overhead | Expected Cut \(\langle C \rangle\) | Approx Ratio |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **p=1** | `processor_A` | 5 | 4 | **11** / 39 | 5 | 7 | **16** | **2** | **5.9678** | **85.3%** |
| **p=1** | `processor_B` | 9 | 4 | **8** / 23 | 5 | 6 | **10** | **1** | **5.9678** | **85.3%** |
| **p=2** | `processor_A` | 5 | 4 | **18** / 62 | 10 | 13 | **29** | **3** | **5.5166** | **78.8%** |
| **p=2** | `processor_B` | 9 | 4 | **12** / 40 | 10 | 10 | **20** | **0** | **5.5166** | **78.8%** |

> **Audit Note on Depth and Expectation Metrics:**
> - **Circuit Depth Metrics**: We report two distinct depths:
>   1. **Routed Circuit Depth** (11 vs 8 at $p=1$; 18 vs 12 at $p=2$): Measured on the routed circuit before native basis gate decomposition, where logical `rzz` and inserted `swap` gates are retained.
>   2. **Native Basis Depth (Unmeasured)** (39 vs 23 at $p=1$; 62 vs 40 at $p=2$): Measured after decomposing into native basis `['cx', 'rz', 'sx', 'x']` without measurement operations. When measurement operations are attached for execution (as in Section 5.4), basis depth becomes 40 vs 24 at $p=1$ and 63 vs 41 at $p=2$.
> - **Expectation Value Across Runs**: In this full 2048-shot benchmark (`maxiter=40`), COBYLA converged to $\langle C \rangle = 5.9678$ ($85.25\%$). In the lighter 1000-shot run (`maxiter=25`, used in Section 5.4 and `main.ipynb`), COBYLA converged to $\langle C \rangle = 6.0060$ ($85.80\%$). Both values represent valid ideal baseline optimizations under their respective iteration budgets and shot configurations.

#### **Empirical Explanation of Architectural Difference**:
- **Metric Verification**: We report both the **high-level two-qubit interaction gates** (5 logical `rzz` interactions + inserted `swap` gates) and the **native two-qubit CX gates** after decomposing into the challenge-documented basis `['cx', 'rz', 'sx', 'x']`. Each `rzz` decomposes into 2 CXs, and each uncancelled `swap` contributes up to 3 CXs.
- On `processor_A` (5-qubit tree), the graph contains no cycles. Routing the 4-qubit cyclic problem graph requires routing across bottleneck node `1`, inserting **2 SWAPs** (16 CX, depth 11 / 39) at \(p=1\) and **3 SWAPs** (29 CX, depth 18 / 62) at \(p=2\).
- On `processor_B` (9-qubit Heavy-Hex), the hardware contains multiple embedded cycles (`(0,1,6,8)`, `(1,2,6)`, `(2,5,6)`). Qiskit's layout pass embeds the 4 logical qubits directly into a cyclic sub-lattice, reducing SWAP overhead to **1 SWAP** (10 CX, depth 8 / 23) at \(p=1\), and completely eliminating routing SWAPs (**0 SWAPs**, 20 CX, depth 12 / 40) at \(p=2\)!

---

### 5.2 Case 2: PS-O1 6-Node Instance Benchmark (Capacity Limit & Hardware Routing)

Extracted directly from [`results/tables/pso1_six_node_processor_ab.csv`](results/tables/pso1_six_node_processor_ab.csv):
*(Benchmark configuration: Ideal noiseless simulation on `AerSimulator`, `p = 1`, `maxiter = 25`, `shots = 1000`, `seed_simulator = 42`, `seed_transpiler = 42`)*

All three six-node weighted graph instances were evaluated using QAOA with **p = 1**, a maximum of 25 optimizer iterations, 1,000 measurement shots, and seed 42. Exact Max-Cut values were obtained through classical brute-force enumeration. Processor results below are development transpilation and ideal-simulation results on `AerSimulator`, not measurements on physical quantum hardware.

| Instance | Processor ID | Physical Qubits | Capacity Status | Exact Max-Cut | Best Sampled Cut | Approximation Ratio | Transpiled Depth | Transpiled CX Count | SWAP Count | Execution Status |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Inst 1 (8 edges) | `processor_A` | 5 | Exceeded | 19 | — | — | — | — | — | Unsupported: 6 logical qubits exceed capacity |
| Inst 1 (8 edges) | `processor_B` | 9 | Supported | 19 | 19 | 100.00% | 13 | 22 | 2 | Supported development transpilation |
| Inst 2 (9 edges) | `processor_A` | 5 | Exceeded | 25 | — | — | — | — | — | Unsupported: 6 logical qubits exceed capacity |
| Inst 2 (9 edges) | `processor_B` | 9 | Supported | 25 | 12 | 48.00% | 13 | 24 | 2 | Supported development transpilation |
| Inst 3 (7 edges) | `processor_A` | 5 | Exceeded | 22 | — | — | — | — | — | Unsupported: 6 logical qubits exceed capacity |
| Inst 3 (7 edges) | `processor_B` | 9 | Supported | 22 | 21 | 95.45% | 10 | 17 | 1 | Supported development transpilation |

**Architectural observations:**
- **Processor A capacity limitation:** The six-node logical instances require six logical qubits, exceeding Processor A's five-qubit capacity. These cases are marked unsupported, and no physical circuit metrics are fabricated for them. No vertex reduction or circuit cutting is assumed.
- **Processor B development results:** The nine-qubit configuration accommodates all three six-node instances under the current transpilation workflow. The recorded SWAP counts are 2, 2, and 1, respectively.
- **Solution quality:** At p = 1, the best sampled cuts reached 100.00% of the exact optimum for Instance 1, 48.00% for Instance 2, and 95.45% for Instance 3.
- **Metric interpretation:** CX counts are based on the documented transpilation basis `['cx', 'rz', 'sx', 'x']`. These counts and SWAP values are development metrics, not verified physical-hardware resource measurements.
- **Configuration caveat:** Processor configurations and topology are development specifications. The results do not establish organizer approval, official device noise characteristics, or execution on physical hardware.

---

### 5.3 Case 3: Graph-Size Routing Sweep (5, 6, 7 Nodes)

Extracted directly from [`results/tables/graph_size_routing_sweep.csv`](results/tables/graph_size_routing_sweep.csv):

| Logical Nodes (\(n\)) | Logical Edges (\(m\)) | Processor ID | Physical Qubits (\(N\)) | Supported? | Transpiled Depth | Logical 2Q Gates | Transpiled 2Q Gates | Transpiled CX Count | SWAP Overhead | Measured Status |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **5** | 7 | `processor_A` | 5 | **True** | **11** | 7 | 10 | **23** | **3** | Supported development transpilation |
| **5** | 7 | `processor_B` | 9 | **True** | **10** | 7 | 8 | **17** | **1** | Supported development transpilation |
| **6** | 9 | `processor_A` | 5 | **False** | — | 9 | — | — | — | Unsupported: logical qubits (6) > capacity (5) |
| **6** | 9 | `processor_B` | 9 | **True** | **12** | 9 | 11 | **24** | **2** | Supported development transpilation |
| **7** | 10 | `processor_A` | 5 | **False** | — | 10 | — | — | — | Unsupported: logical qubits (7) > capacity (5) |
| **7** | 10 | `processor_B` | 9 | **True** | **12** | 10 | 12 | **26** | **2** | Supported development transpilation |

---

### 5.4 Case 4: Synthetic Noise-Model Evaluation (Master Guide Calibration)

To assess algorithm robustness under realistic physical device imperfections, we implemented a reusable synthetic noise-model factory calibrated to the official **Qiskit Fall Fest 2026 Master Guide**:
- **1-Qubit Depolarizing Error ($p_{1q} = 0.001$):** Applied to physical microwave drive gates (`sx`, `x`). Virtual $R_Z$ rotations are software frame updates executed without pulse duration or physical gate infidelity, and are modeled as error-free.
- **2-Qubit CX Depolarizing Error ($p_{2q} = 0.005$):** Applied to native `cx` interactions.
- **Symmetric Readout Bit-Flip Error ($p_{ro} = 0.01$):** Modeled with classical confusion matrices ($P(0|1) = P(1|0) = 0.01$).

Both processors were benchmarked with **identical synthetic noise rates**, transpiler optimization level 1, seed 42, and **4,096 measurement shots** on the transpiled physical circuits. Ideal QAOA parameters pre-optimized on the problem graph (`shots = 1000`, `maxiter = 25`, $\langle C \rangle_{\text{ideal}} = 6.0060$ at $p=1$, $5.3890$ at $p=2$) were evaluated directly on the noisy simulated circuits to isolate connectivity and SWAP-overhead effects.

#### **Noisy Benchmark Results (4-Node Problem, Ideal vs. Synthetic Noise)**
Extracted from [`results/tables/processor_ab_noisy_comparison.csv`](results/tables/processor_ab_noisy_comparison.csv):

| Processor ID | Depth $p$ | Native CX Count | Transpiled Depth (Measured Basis) | Opt Expected Cut $\langle C \rangle_{\text{ideal}}$ | Noisy Expected Cut $\langle C \rangle_{\text{noisy}}$ | Noisy Approx Ratio | Expectation Drop | Solution Quality Retention |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `processor_A` | 1 | 16 | 40 | 6.006 | 5.8074 | 82.96% | 0.1986 | 96.69% |
| `processor_B` | 1 | 10 | 24 | 6.006 | 5.8660 | 83.80% | 0.1400 | 97.67% |
| `processor_A` | 2 | 29 | 63 | 5.389 | 5.1453 | 73.50% | 0.2437 | 95.48% |
| `processor_B` | 2 | 20 | 41 | 5.389 | 5.2415 | 74.88% | 0.1475 | 97.26% |

#### **PS-O1 6-Node Instance 1 Noisy Evaluation (Capacity Limit Check)**
| Processor ID | Physical Qubits | Capacity Status | Native CX Count | Transpiled Depth | Opt Expected Cut $\langle C \rangle_{\text{ideal}}$ | Noisy Expected Cut $\langle C \rangle_{\text{noisy}}$ | Noisy Approx Ratio | Notes |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `processor_A` | 5 | Exceeded | — | — | 16.219 | — | — | Unsupported: 6 logical qubits exceed capacity |
| `processor_B` | 9 | Supported | 22 | 46 | 16.219 | 15.5554 | 81.87% | Supported noisy development simulation |

#### **Empirical Observations & Hardware Implications**:
1. **Measured Quality Retention**: Under identical noise channels, Processor B retains 97.67% of ideal cut expectation at $p=1$ compared to 96.69% for Processor A. At $p=2$, Processor B retains 97.26% compared to 95.48% for Processor A.
2. **Noise-CX Correlation**: Because 2-qubit CX gates suffer 5× higher error rates ($p_{2q}=0.005$) than 1-qubit gates, the 6 additional CX gates incurred by Processor A at $p=1$ (16 vs 10 CX) and 9 additional CX gates at $p=2$ (29 vs 20 CX) account directly for the larger expectation drop (0.1986 vs 0.1400 at $p=1$, 0.2437 vs 0.1475 at $p=2$).
3. **Capacity Boundaries Strictly Enforced**: For the 6-node instance, Processor A cannot map the 6 logical qubits onto its 5 physical qubits. Rather than fabricating synthetic metrics, Processor A is explicitly marked unsupported. Processor B successfully executes with 22 CX gates and achieves an approximation ratio of 81.87%.
4. **Development Disclaimer**: These results reflect synthetic Aer simulation based on Master Guide calibration parameters. They do not constitute execution on physical quantum hardware or official organizer-approved device parameters.

---

## 6. Distinction Between Evidence, Interpretation, and Limitations

- **Measured Evidence (Empirical Fact)**:
  - On the 4-node problem, Processor B reduces high-level routing depth by 27% at \(p=1\) (8 vs 11) and by 33% at \(p=2\) (12 vs 18), requiring 0 SWAPs at \(p=2\).
  - Native CX gate counts after basis transpilation are 10 on Processor B vs 16 on Processor A at $p=1$ (a 37.5% reduction), and 20 vs 29 at $p=2$ (a 31.0% reduction).
  - Under synthetic noise ($p_{1q}=0.001$, $p_{2q}=0.005$, $p_{ro}=0.01$), Processor B incurs a lower expectation drop (0.1400 vs 0.1986 at $p=1$, 0.1475 vs 0.2437 at $p=2$) due directly to this reduced CX overhead.
  - On the 5-node problem, Processor B requires only 1 SWAP compared to 3 SWAPs on Processor A.
  - On 6-node and 7-node graphs, Processor A cannot fit the problem graph due to its 5-qubit physical capacity. Processor B executes 6- and 7-node instances with only 2 SWAPs.
- **Interpretation**:
  - Processor B's advantage stems from both **capacity** (\(N=9\) allows up to 9-qubit graphs) and **connectivity** (embedded Heavy-Hex cycles provide redundant routing paths that tree topologies lack).
- **Limitations & Missing Official Information**:
  - Official Challenge Kit noise models (physical device calibration data, gate crosstalk, $T_1/T_2$ times) are unverified in current materials; simulations are conducted under ideal conditions and synthetic Master Guide noise models on `AerSimulator`. No physical hardware execution or organizer approval is claimed.

---

## 7. Conclusion & Next Steps

Team **QubitX** has delivered an end-to-end, reproducible solution aligned directly with the Phase 1 rubric:
- **Measured Evidence**: Demonstrates concrete routing differences between 5-qubit tree (Processor A) and 9-qubit Heavy-Hex (Processor B).
- **Full Problem Coverage**: Implements both development instances and official PS-O1 6-node weighted graphs.
- **Synthetic Noise Integration**: Verifies algorithm robustness under Master Guide noise parameters while respecting hardware capacity boundaries.
- **Automated Validation**: All results exported to `results/tables/` and `results/figures/` and verified via `main.ipynb` and `tests/test_noise.py`.
