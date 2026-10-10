"""Processor configuration loader, validator, and Qiskit CouplingMap builder."""

import json
from pathlib import Path
from typing import Any
import networkx as nx
from qiskit.transpiler import CouplingMap

# Project root directory relative to this module (src/processors.py -> root/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSORS_DIR = PROJECT_ROOT / "processors"

REQUIRED_FIELDS = (
    "processor_id",
    "processor_name",
    "num_qubits",
    "edges",
    "configuration_status",
    "is_official_specification",
)


def load_processor_config(file_path: str | Path) -> dict[str, Any]:
    """Load and parse a processor JSON specification file.

    Args:
        file_path: Relative (to PROJECT_ROOT) or absolute path to the processor JSON file.

    Returns:
        dict: Raw JSON dictionary.
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        raise FileNotFoundError(f"Processor configuration file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as err:
        raise ValueError(f"Malformed JSON in processor configuration '{path}': {err}")

    return data


def validate_processor_data(
    data: dict[str, Any], file_label: str = "processor config"
) -> dict[str, Any]:
    """Validate JSON schema, qubit range, duplicate edges, self-loops, and graph connectivity.

    Args:
        data: Parsed processor specification dictionary.
        file_label: Descriptive label for error messages.

    Returns:
        dict: Validated processor dictionary.
    """
    # 1. Validate required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Missing required field '{field}' in {file_label}.")

    num_qubits = data["num_qubits"]
    if not isinstance(num_qubits, int) or num_qubits <= 0:
        raise ValueError(
            f"Field 'num_qubits' must be a positive integer in {file_label}, got {num_qubits}."
        )

    edges = data["edges"]
    if not isinstance(edges, list):
        raise ValueError(f"Field 'edges' must be a list in {file_label}.")

    # 2. Validate edge endpoints, self-loops, duplicate edges, and bounds
    seen_edges = set()
    g = nx.Graph()
    g.add_nodes_from(range(num_qubits))

    for idx, edge in enumerate(edges):
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError(
                f"Edge entry {idx} {edge} must be a 2-element list in {file_label}."
            )
        u, v = edge
        if not isinstance(u, int) or not isinstance(v, int):
            raise ValueError(
                f"Edge endpoints ({u}, {v}) must be integers in {file_label}."
            )
        if u < 0 or u >= num_qubits or v < 0 or v >= num_qubits:
            raise ValueError(
                f"Edge ({u}, {v}) has endpoints outside valid range [0, {num_qubits - 1}] in {file_label}."
            )
        if u == v:
            raise ValueError(f"Self-loop edge ({u}, {v}) is invalid in {file_label}.")

        sorted_edge = tuple(sorted((u, v)))
        if sorted_edge in seen_edges:
            raise ValueError(
                f"Duplicate undirected edge ({u}, {v}) in {file_label}."
            )
        seen_edges.add(sorted_edge)
        g.add_edge(u, v)

    # 3. Validate graph connectivity
    if not nx.is_connected(g):
        raise ValueError(f"Coupling graph is disconnected in {file_label}.")

    return data


def create_coupling_map_from_config(data: dict[str, Any]) -> tuple[CouplingMap, str]:
    """Convert validated processor data into a Qiskit CouplingMap with bidirectional edges.

    Args:
        data: Validated processor configuration dictionary.

    Returns:
        tuple[CouplingMap, str]: Qiskit CouplingMap object and descriptive label.
    """
    validate_processor_data(data)

    bidirectional_edges = []
    for u, v in data["edges"]:
        bidirectional_edges.append((u, v))
        bidirectional_edges.append((v, u))

    cm = CouplingMap(bidirectional_edges)

    is_official = data.get("is_official_specification", False)
    status_tag = (
        "Official Specification"
        if is_official
        else "Development Example (Provisional)"
    )
    desc = f"{data['processor_name']} ({data['num_qubits']} qubits) [{status_tag}]"

    return cm, desc


def load_development_processors() -> dict[str, tuple[dict[str, Any], CouplingMap, str]]:
    """Load both Processor A and Processor B development configurations.

    Checks for processor_A.json and processor_B.json first, falling back to
    processor_a_dev.json and processor_b_dev.json if needed.

    Returns:
        dict mapping processor_id -> (data_dict, coupling_map, descriptive_label).
    """
    configs = {}
    processor_pairs = [
        ("processor_A.json", "processor_a_dev.json"),
        ("processor_B.json", "processor_b_dev.json"),
    ]

    for primary_name, dev_name in processor_pairs:
        primary_path = PROCESSORS_DIR / primary_name
        dev_path = PROCESSORS_DIR / dev_name

        pfile = primary_path if primary_path.exists() else dev_path
        raw_data = load_processor_config(pfile)
        val_data = validate_processor_data(raw_data, file_label=pfile.name)
        cm, desc = create_coupling_map_from_config(val_data)
        configs[val_data["processor_id"]] = (val_data, cm, desc)

    return configs



def inspect_processor_transpilation_layouts(
    logical_circuit: Any, seed_transpiler: int = 42
) -> dict[str, dict[str, Any]]:
    """Inspect the physical qubit layout and transpiled instruction breakdown for each processor.

    Args:
        logical_circuit: Logical Qiskit QuantumCircuit.
        seed_transpiler: Random seed for deterministic transpilation pass.

    Returns:
        dict mapping processor_id -> diagnostic information dictionary.
    """
    from qiskit.compiler import transpile

    dev_processors = load_development_processors()
    diagnostics = {}

    for pid, (data_dict, cm, desc_label) in dev_processors.items():
        transpiled_qc = transpile(
            logical_circuit,
            coupling_map=cm,
            optimization_level=1,
            seed_transpiler=seed_transpiler,
        )

        initial_layout = (
            dict(transpiled_qc.layout.initial_layout.get_virtual_bits())
            if transpiled_qc.layout
            else {}
        )
        final_layout = (
            dict(transpiled_qc.layout.final_layout.get_virtual_bits())
            if transpiled_qc.layout and transpiled_qc.layout.final_layout
            else None
        )

        ops = dict(transpiled_qc.count_ops())

        diagnostics[pid] = {
            "processor_name": data_dict["processor_name"],
            "physical_qubits": data_dict["num_qubits"],
            "coupling_edges": data_dict["edges"],
            "initial_layout": {str(k): v for k, v in initial_layout.items()},
            "final_layout": str(final_layout) if final_layout else "N/A",
            "transpiled_depth": transpiled_qc.depth(),
            "op_counts": ops,
            "swap_count": ops.get("swap", 0),
        }

    return diagnostics

