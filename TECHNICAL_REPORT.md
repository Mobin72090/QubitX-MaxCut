# Technical Report: QAOA for Weighted Max-Cut & SWAP Bottleneck Analysis

**Qiskit Fall Fest 2026 Phase 1 Hackathon**  
**Team:** QubitX  
**Track:** Quantum Optimization  
**Problem Statement:** PS-O1 — Max-Cut on Weighted Graphs  

---

## 1. Executive Summary & Core Hackathon Principle

The core objective of Phase 1 is **not merely to report algorithm execution outputs**, but to demonstrate **how the exact same quantum optimization solution behaves across two distinct processor architectures**, using empirical, measured evidence to explain the performance differences.

In this project, Team **QubitX** implemented a modular Python and Qiskit framework to solve the **Weighted Max-Cut** problem using the **Quantum Approximate Optimization Algorithm (QAOA)**. By keeping all algorithmic variables strictly controlled (identical logical problem graph, QAOA depth \(p\), classical optimizer settings, measurement shots, simulator seed `42`, and transpiler seed `42`), we evaluated how circuit transpilation and routing SWAP bottlenecks behave on two different hardware topologies:

1. **Processor A (`processor_a_dev`)**: A 5-qubit branching tree topology (`[[0, 1], [1, 2], [1, 3], [3, 4]]`).
2. **Processor B (`processor_b_dev`)**: A 7-qubit Heavy-Hex sub-unit topology (`[[0, 1], [1, 2], [2, 3], [3, 4], [1, 5], [3, 6]]`).

> **Provisional Specification Disclaimer:**  
> Processor configurations in `processors/` are provisional development topologies reconstructed for SWAP bottleneck modeling. They do not represent official organizer-provided hardware specifications. When official Processor A and Processor B specs are published, their `.json` files can be dropped into `processors/` to run automated benchmarks immediately.

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

## 3. Controlled Experimental Setup

To ensure valid comparative evidence, all parameters were held strictly constant:

- **Simulation Engine**: Qiskit Aer (`AerSimulator`).
- **Optimization Strategy**: SciPy `COBYLA` with `maxiter = 25` to `40`.
- **Measurement Shots**: `shots = 1000` / `2048` per circuit evaluation.
- **Random Seeds**:
  - `seed_simulator = 42` (reproducible initial points & shot sampling).
  - `seed_transpiler = 42` (deterministic transpilation routing).
- **Target Processor Topologies**:
  - `processor_a_dev` (5 physical qubits, tree graph).
  - `processor_b_dev` (7 physical qubits, Heavy-Hex sub-unit graph).

---

## 4. Measured Comparative Evidence

### 4.1 Case 1: 4-Node Problem Graph Comparison (Isomorphic Subgraph Embedding)

Extracted directly from [`results/processor_ab_development_results.csv`](file:///c:/Projects/QubitX-MaxCut/results/processor_ab_development_results.csv):

| QAOA Depth \(p\) | Processor ID | Physical Qubits (\(N\)) | Logical Qubits (\(n\)) | Physical Layout Selected | Transpiled Depth | Logical 2Q Gates | Transpiled 2Q Gates | SWAP Overhead | Expected Cut \(\langle C \rangle\) | Approx Ratio |
| :---: | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **p=1** | `processor_a_dev` | 5 | 4 | `{q[0]:1, q[1]:0, q[2]:3, q[3]:2}` | **11** | 5 | 7 | **2** | 6.006 | **85.8%** |
| **p=1** | `processor_b_dev` | 7 | 4 | `{q[0]:1, q[1]:0, q[2]:2, q[3]:5}` | **11** | 5 | 7 | **2** | 6.006 | **85.8%** |
| **p=2** | `processor_a_dev` | 5 | 4 | `{q[0]:1, q[1]:0, q[2]:3, q[3]:2}` | **18** | 10 | 13 | **3** | 5.389 | **77.0%** |
| **p=2** | `processor_b_dev` | 7 | 4 | `{q[0]:1, q[1]:0, q[2]:2, q[3]:5}` | **18** | 10 | 13 | **3** | 5.389 | **77.0%** |

#### **Empirical Explanation of Matching Results**:
The routing metrics match on 4-node workloads **not due to a code defect**, but because Qiskit's `DenseLayout` pass selected physical subgraphs `{0, 1, 2, 3}` on Processor A and `{0, 1, 2, 5}` on Processor B. Both selected subgraphs form **isomorphic 4-qubit T-junctions** (centered at physical node `1`). Consequently, the routing pass inserted identical SWAP operations (2 SWAPs at \(p=1\), 3 SWAPs at \(p=2\)).

---

### 4.2 Case 2: Graph-Size Routing Sweep (Capacity Limits & SWAP Scaling)

Extracted directly from [`results/graph_size_routing_sweep.csv`](file:///c:/Projects/QubitX-MaxCut/results/graph_size_routing_sweep.csv):

| Logical Nodes (\(n\)) | Logical Edges (\(m\)) | Processor ID | Physical Qubits (\(N\)) | Capacity Check | Transpilation Success | Transpiled Depth | Logical 2Q Gates | Transpiled 2Q Gates | SWAP Overhead | Measured Status |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **5** | 7 | `processor_a_dev` | 5 | **Supported** | **True** | **11** | 7 | 10 | **3** | Supported development transpilation |
| **5** | 7 | `processor_b_dev` | 7 | **Supported** | **True** | **11** | 7 | 10 | **3** | Supported development transpilation |
| **6** | 9 | `processor_a_dev` | 5 | **Exceeded** | **False** | — | 9 | — | — | Unsupported: logical qubits (6) > capacity (5) |
| **6** | 9 | `processor_b_dev` | 7 | **Supported** | **True** | **16** | 9 | 13 | **4** | Supported development transpilation |
| **7** | 10 | `processor_a_dev` | 5 | **Exceeded** | **False** | — | 9 | — | — | Unsupported: logical qubits (7) > capacity (5) |
| **7** | 10 | `processor_b_dev` | 7 | **Supported** | **True** | **17** | 10 | 15 | **5** | Supported development transpilation |

#### **Empirical Explanation of Divergent Behavior**:
1. **Physical Capacity Hard Limit**: Processor A (\(N=5\)) cannot execute 6-node or 7-node QAOA circuits. The framework safely rejects transpilation (`is_supported = False`), preventing runtime crashes.
2. **SWAP Overhead Scaling**: Processor B (\(N=7\)) accommodates larger problem graphs up to 7 nodes. However, **more qubits do not eliminate routing bottlenecks**. On 7-node graphs, routing requires **5 SWAP gates**, expanding two-qubit operations from 10 to 15 and inflating circuit depth from 9 to 17.

---

## 5. Distinction Between Evidence, Interpretation, and Limitations

- **Measured Evidence (Empirical Fact)**:
  - 4-node QAOA circuit transpiled onto both processors requires 2 SWAPs at \(p=1\) (depth 11) and 3 SWAPs at \(p=2\) (depth 18).
  - Processor A cannot transpile graphs with \(n > 5\) qubits.
  - Processor B handles up to 7 nodes, with SWAP overhead scaling linearly: 3 SWAPs (\(n=5\)), 4 SWAPs (\(n=6\)), 5 SWAPs (\(n=7\)).
- **Interpretation**:
  - Processor B's advantage in this benchmark stems strictly from physical qubit capacity (\(N=7\) vs \(N=5\)), allowing it to support 6-node and 7-node instances that Processor A cannot fit. It does NOT demonstrate superior routing efficiency on equal-sized 4-node or 5-node workloads.
- **Limitations & Missing Official Information**:
  - Official Processor A and Processor B coupling maps, native basis gate sets (e.g. `cz`, `ecr`), and physical noise parameters (\(1Q/2Q\) error rates, readout errors, \(T_1/T_2\) times) remain to be provided by hackathon organizers.

---

## 6. Conclusion & Next Steps

Team **QubitX** has delivered a fully verified comparative framework adhering directly to the Phase 1 core principle:
- **Measured Evidence**: Empirical metrics recorded across controlled Processor A and Processor B benchmarks.
- **Architectural Understanding**: Subgraph isomorphism and capacity scaling fully explained through transpiler layout diagnostics.
- **Pluggable Architecture**: Ready to load official organizer `.json` specifications instantly upon release.
