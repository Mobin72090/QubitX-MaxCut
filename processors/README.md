# Processor Configuration Specifications

This directory contains JSON configuration specifications for hardware coupling topologies used in SWAP bottleneck analysis for Qiskit Fall Fest 2026 Phase 1.

> **Development Disclaimer:**  
> Configurations in this directory with `"is_official_specification": false` are development examples reconstructed for SWAP bottleneck analysis. They do not represent official organizer-provided hardware specifications.

---

## Configuration Schema

Each processor JSON specification contains the following fields:
- `processor_id` (str): Unique identifier string (e.g. `"processor_a_dev"`).
- `processor_name` (str): Human-readable name.
- `num_qubits` (int): Total physical qubit count.
- `edges` (list[list[int]]): Undirected edge list of physical qubit connections.
- `configuration_status` (str): `"provisional_development_example"` or `"official_specification"`.
- `is_official_specification` (bool): `false` for development examples, `true` for official organizer specs.
- `ambiguity_note` (str, optional): Explanatory documentation regarding topology inferences.
- `notes` (str): General project notes.

---

## Included Files

1. **[`processor_a_dev.json`](processor_a_dev.json)**:
   - 5-qubit tree topology (`[[0, 1], [1, 2], [1, 3], [3, 4]]`).
2. **[`processor_b_dev.json`](processor_b_dev.json)**:
   - Provisional 7-qubit Heavy-Hex sub-unit topology (`[[0, 1], [1, 2], [2, 3], [3, 4], [1, 5], [3, 6]]`).

When organizers release official backend specifications for Processor A and Processor B, save their `.json` files in this directory to run automated benchmarks against them.
