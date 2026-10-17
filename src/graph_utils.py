
"""Utilities for creating and validating weighted Max-Cut graphs."""

import random

import networkx as nx
import numpy as np


def create_sample_graph() -> nx.Graph:
    """Create a small weighted graph for development and testing.

    This is an example graph, not official hackathon-provided data.
    """
    graph = nx.Graph()
    graph.add_weighted_edges_from(
        [
            (0, 1, 2.0),
            (0, 2, 1.0),
            (1, 2, 3.0),
            (1, 3, 2.0),
            (2, 3, 1.0),
        ]
    )
    return graph


def create_pso1_6node_graph(instance_id: int = 1) -> nx.Graph:
    """Create one of three predefined six-node weighted test graphs.

    These are custom example graphs, not randomly generated reference graphs.

    Args:
        instance_id: Graph identifier: 1, 2, or 3.

    Returns:
        An undirected graph with integer edge weights from 1 to 5.
    """
    if instance_id == 1:
        edges = [
            (0, 1, 2),
            (0, 2, 4),
            (1, 2, 1),
            (1, 3, 5),
            (2, 4, 3),
            (3, 4, 2),
            (3, 5, 4),
            (4, 5, 1),
        ]
    elif instance_id == 2:
        edges = [
            (0, 1, 3),
            (1, 2, 2),
            (2, 3, 5),
            (3, 4, 1),
            (4, 5, 4),
            (5, 0, 2),
            (0, 3, 3),
            (1, 4, 1),
            (2, 5, 4),
        ]
    elif instance_id == 3:
        edges = [
            (0, 1, 5),
            (1, 2, 4),
            (2, 3, 3),
            (3, 4, 2),
            (4, 5, 1),
            (0, 3, 4),
            (1, 4, 3),
        ]
    else:
        raise ValueError(
            f"Instance ID {instance_id} must be 1, 2, or 3."
        )

    graph = nx.Graph()
    graph.add_weighted_edges_from(edges)
    validate_graph(graph)
    return graph


def create_pso1_reference_graph(
    seed: int = 42,
    weight_seed: int = 42,
) -> nx.Graph:
    """Create the guide-based six-node PS-O1 reference graph.

    The graph topology follows G(n=6, p=0.5), using seed=42 by
    default. Integer edge weights from 1 to 5 are generated using
    a separate, explicit seed for reproducibility.

    Note:
        The guide specifies the topology seed but does not specify
        a separate seed for assigning edge weights.
    """
    graph = nx.erdos_renyi_graph(
        n=6,
        p=0.5,
        seed=seed,
    )

    rng = random.Random(weight_seed)

    for u, v in graph.edges():
        graph[u][v]["weight"] = rng.randint(1, 5)

    validate_graph(graph)
    return graph


def create_synthetic_graph(
    num_nodes: int,
    seed: int = 42,
) -> nx.Graph:
    """Create a reproducible connected weighted graph.

    This function uses a cycle plus additional random edges.
    It is not the PS-O1 Erdős–Rényi reference generator.

    Args:
        num_nodes: Number of vertices; must be at least 2.
        seed: Random seed for deterministic structure and weights.

    Returns:
        A connected undirected graph with positive float weights.
    """
    if num_nodes < 2:
        raise ValueError(
            "Synthetic graph must have at least 2 nodes."
        )

    graph = nx.cycle_graph(num_nodes)
    rng = np.random.default_rng(seed)

    possible_edges = [
        (u, v)
        for u in range(num_nodes)
        for v in range(u + 2, num_nodes)
        if not (u == 0 and v == num_nodes - 1)
    ]

    if possible_edges:
        extra_count = max(1, num_nodes // 2)
        selected_indices = rng.choice(
            len(possible_edges),
            size=min(extra_count, len(possible_edges)),
            replace=False,
        )

        for idx in selected_indices:
            u, v = possible_edges[idx]
            graph.add_edge(u, v)

    for u, v in graph.edges():
        weight = float(rng.uniform(1.0, 3.0))
        graph[u][v]["weight"] = round(weight, 2)

    validate_graph(graph)
    return graph


def validate_graph(graph: nx.Graph) -> None:
    """Validate a graph for weighted Max-Cut."""
    if graph.number_of_nodes() < 2:
        raise ValueError(
            "The graph must contain at least two nodes."
        )

    if graph.number_of_edges() == 0:
        raise ValueError(
            "The graph must contain at least one edge."
        )

    if graph.is_directed():
        raise ValueError(
            "Max-Cut requires an undirected graph."
        )

    for u, v, data in graph.edges(data=True):
        if u == v:
            raise ValueError("Self-loops are not allowed.")

        weight = data.get("weight")

        if weight is None:
            raise ValueError(
                f"Edge ({u}, {v}) is missing a weight."
            )

        if not isinstance(weight, (int, float)):
            raise ValueError(
                f"Edge ({u}, {v}) must have a numeric weight."
            )

        if not np.isfinite(weight) or weight <= 0:
            raise ValueError(
                f"Edge ({u}, {v}) must have a finite positive weight."
            )


def calculate_cut_value(
    graph: nx.Graph,
    partition: dict,
) -> float:
    """Calculate the total weight of edges crossing two partitions."""
    validate_graph(graph)

    if set(partition.keys()) != set(graph.nodes()):
        raise ValueError(
            "Every graph node must have a partition assignment."
        )

    if not all(side in (0, 1) for side in partition.values()):
        raise ValueError(
            "Partition assignments must be 0 or 1."
        )

    cut_value = sum(
        data["weight"]
        for u, v, data in graph.edges(data=True)
        if partition[u] != partition[v]
    )

    return float(cut_value)


def solve_max_cut_brute_force(
    graph: nx.Graph,
) -> tuple[float, dict[int, int], list[dict[int, int]]]:
    """Find the exact Max-Cut value and all optimal partitions.

    Exhaustively checks all binary partitions. Intended for small graphs.

    Returns:
        A tuple containing:
        - The maximum cut value.
        - One optimal partition mapping node to 0 or 1.
        - All optimal partitions.
    """
    validate_graph(graph)

    nodes = list(graph.nodes())
    n = len(nodes)

    if n > 20:
        raise ValueError(
            "Brute-force exact solver is restricted to graphs "
            "with <= 20 nodes for performance."
        )

    max_cut_value = -1.0
    best_partition = {}
    all_optimal_partitions = []

    for i in range(1 << n):
        partition = {
            nodes[k]: (i >> k) & 1
            for k in range(n)
        }
        value = calculate_cut_value(graph, partition)

        if value > max_cut_value + 1e-9:
            max_cut_value = value
            best_partition = partition
            all_optimal_partitions = [partition]
        elif abs(value - max_cut_value) <= 1e-9:
            all_optimal_partitions.append(partition)

    return (
        max_cut_value,
        best_partition,
        all_optimal_partitions,
    )
