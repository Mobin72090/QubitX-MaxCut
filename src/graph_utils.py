
"""Utilities for creating and validating weighted Max-Cut graphs."""

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
    """Create PS-O1 specified 6-node weighted graphs with integer weights 1-5.

    The PS-O1 problem statement requires providing 2-3 example graphs with 6 nodes
    and integer weights in range 1 to 5.

    Args:
        instance_id: Identifier for the example graph (1, 2, or 3).

    Returns:
        nx.Graph: 6-node connected graph with integer edge weights 1-5.
    """
    g = nx.Graph()
    if instance_id == 1:
        # 6 nodes, 8 edges, integer weights 1-5
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
        # 6 nodes, 9 edges, integer weights 1-5
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
        # 6 nodes, 7 edges, integer weights 1-5
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
        raise ValueError(f"Instance ID {instance_id} must be 1, 2, or 3.")

    g.add_weighted_edges_from(edges)
    return g



def create_synthetic_graph(num_nodes: int, seed: int = 42) -> nx.Graph:
    """Create a reproducible connected weighted Max-Cut graph of arbitrary size.

    Args:
        num_nodes: Number of vertices (must be >= 2).
        seed: Random seed for deterministic graph structure and weights.

    Returns:
        nx.Graph: Connected undirected graph with positive float weights.
    """
    if num_nodes < 2:
        raise ValueError("Synthetic graph must have at least 2 nodes.")

    # Create connectedErdos-Renyi graph or ring + random edges for guaranteed connectivity
    g = nx.cycle_graph(num_nodes)
    rng = np.random.default_rng(seed)

    # Add extra random edges for density
    possible_edges = [
        (u, v) for u in range(num_nodes) for v in range(u + 2, num_nodes)
        if not (u == 0 and v == num_nodes - 1)
    ]
    if possible_edges:
        extra_count = max(1, num_nodes // 2)
        selected_indices = rng.choice(len(possible_edges), size=min(extra_count, len(possible_edges)), replace=False)
        for idx in selected_indices:
            u, v = possible_edges[idx]
            g.add_edge(u, v)

    # Assign deterministic positive float weights
    for u, v in g.edges():
        weight = float(rng.uniform(1.0, 3.0))
        g[u][v]["weight"] = round(weight, 2)

    return g



def validate_graph(graph: nx.Graph) -> None:
    """Validate that a graph is suitable for weighted Max-Cut."""
    if graph.number_of_nodes() < 2:
        raise ValueError("The graph must contain at least two nodes.")

    if graph.number_of_edges() == 0:
        raise ValueError("The graph must contain at least one edge.")

    if graph.is_directed():
        raise ValueError("Max-Cut requires an undirected graph.")

    for u, v, data in graph.edges(data=True):
        if u == v:
            raise ValueError("Self-loops are not allowed.")

        weight = data.get("weight")

        if weight is None:
            raise ValueError(f"Edge ({u}, {v}) is missing a weight.")

        if not isinstance(weight, (int, float)):
            raise ValueError(f"Edge ({u}, {v}) must have a numeric weight.")

        if weight <= 0 or not float(weight) < float("inf"):
            raise ValueError(
                f"Edge ({u}, {v}) must have a finite positive weight."
            )


def calculate_cut_value(graph: nx.Graph, partition: dict) -> float:
    """Calculate the total weight of edges crossing two partitions."""
    validate_graph(graph)

    if set(partition.keys()) != set(graph.nodes()):
        raise ValueError("Every graph node must have a partition assignment.")

    if not all(side in (0, 1) for side in partition.values()):
        raise ValueError("Partition assignments must be 0 or 1.")

    cut_value = sum(
        data["weight"]
        for u, v, data in graph.edges(data=True)
        if partition[u] != partition[v]
    )

    return float(cut_value)


def solve_max_cut_brute_force(
    graph: nx.Graph,
) -> tuple[float, dict[int, int], list[dict[int, int]]]:
    """Find the exact ground-truth Max-Cut value and partition(s) via exhaustive search.

    Args:
        graph: NetworkX graph with numeric edge weights.

    Returns:
        A tuple containing:
            - max_cut_value (float): The maximum cut value found.
            - best_partition (dict): One optimal partition mapping node -> 0 or 1.
            - all_optimal_partitions (list[dict]): All partitions achieving max_cut_value.
    """
    validate_graph(graph)
    nodes = list(graph.nodes())
    n = len(nodes)

    if n > 20:
        raise ValueError(
            "Brute-force exact solver is restricted to graphs with <= 20 nodes for performance."
        )

    max_cut_value = -1.0
    best_partition = {}
    all_optimal_partitions = []

    # Iterate over all 2^n binary partitions
    for i in range(1 << n):
        # Map bit i to partition assignment for each node index
        partition = {nodes[k]: (i >> k) & 1 for k in range(n)}
        val = calculate_cut_value(graph, partition)

        if val > max_cut_value + 1e-9:
            max_cut_value = val
            best_partition = partition
            all_optimal_partitions = [partition]
        elif abs(val - max_cut_value) <= 1e-9:
            all_optimal_partitions.append(partition)

    return max_cut_value, best_partition, all_optimal_partitions

