# Processor Configuration Specifications

This directory contains JSON configuration specifications for hardware coupling topologies used in SWAP bottleneck analysis for Qiskit Fall Fest 2026 Phase 1.

> **Status from Challenge Kit Documentation (`Processor_AB_Benchmark_Configuration_FINAL.pdf`):**
> Coupling maps for Processor A (5 qubits) and Processor B (9 qubits) are verified from the official simulation configuration supplied for the hackathon. Hardware noise models (gate errors, readout errors, relaxation times) remain unverified and must be frozen separately when official Challenge Kit noise models are finalized.

---

## Configuration Schema

Each processor JSON specification contains the following fields:
- `processor_id` (str): Unique identifier string (`"processor_A"` or `"processor_B"`).
- `processor_name` (str): Human-readable name.
- `num_qubits` (int): Total physical qubit count (5 for Processor A; 9 for Processor B).
- `edges` (list[list[int]]): Undirected edge list of physical qubit connections.
- `configuration_status` (str): `"challenge_kit_supported"`.
- `is_official_specification` (bool): `false` (topology verified from simulation config; noise model unverified).
- `notes` (str): General documentation and source reference.

---

## Included Files

1. **[`processor_A.json`](processor_A.json)** (alias `processor_a_dev.json`):
   - 5-qubit tree topology (`[[0, 1], [1, 2], [1, 3], [3, 4]]`).
2. **[`processor_B.json`](processor_B.json)** (alias `processor_b_dev.json`):
   - 9-qubit Heavy-Hex topology (`[[0, 1], [1, 2], [1, 6], [2, 3], [2, 6], [2, 5], [3, 4], [4, 5], [5, 6], [6, 7], [6, 8], [8, 0]]`).
