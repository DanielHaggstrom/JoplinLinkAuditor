"""Link-structure analytics for a Joplin note graph."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Iterable

import networkx as nx

from joplin_utils.client import JoplinClient
from joplin_utils.link_graph import NoteLinkGraph, build_note_link_graph


def _shannon_entropy(probabilities: Iterable[float]) -> float:
    probs = [value for value in probabilities if value > 0]
    return -sum(value * math.log2(value) for value in probs)


def _bernoulli_entropy(probability: float) -> float:
    if probability <= 0 or probability >= 1:
        return 0.0
    return -probability * math.log2(probability) - (1 - probability) * math.log2(1 - probability)


def _distribution_entropy(values: Iterable[int]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if not total:
        return 0.0
    return _shannon_entropy(count / total for count in counts.values())


def _local_branching_entropy(graph: nx.DiGraph) -> dict[str, float]:
    entropies: dict[str, float] = {}
    for node in graph.nodes:
        out_degree = graph.out_degree(node)
        entropies[node] = math.log2(out_degree) if out_degree > 1 else 0.0
    return entropies


def _component_sizes(graph: nx.Graph) -> list[int]:
    return sorted((len(component) for component in nx.connected_components(graph)), reverse=True)


def _community_structure(graph: nx.Graph) -> tuple[list[set[str]], float]:
    if graph.number_of_edges() == 0:
        communities = [{node} for node in graph.nodes]
        return communities, 0.0

    communities = [set(group) for group in nx.community.greedy_modularity_communities(graph)]
    modularity = nx.community.modularity(graph, communities)
    return communities, modularity


def _pagerank_distribution(
    graph: nx.DiGraph,
    *,
    alpha: float,
    tol: float = 1.0e-12,
    max_iter: int = 1000,
) -> dict[str, float]:
    nodes = list(graph.nodes)
    node_count = len(nodes)
    if node_count == 0:
        return {}

    ranks = {node: 1.0 / node_count for node in nodes}
    dangling_nodes = [node for node in nodes if graph.out_degree(node) == 0]
    base_mass = (1.0 - alpha) / node_count

    for _ in range(max_iter):
        updated = {node: base_mass for node in nodes}

        dangling_mass = alpha * sum(ranks[node] for node in dangling_nodes) / node_count
        if dangling_mass:
            for node in nodes:
                updated[node] += dangling_mass

        for source_id in nodes:
            out_degree = graph.out_degree(source_id)
            if out_degree == 0:
                continue
            share = alpha * ranks[source_id] / out_degree
            for target_id in graph.successors(source_id):
                updated[target_id] += share

        delta = sum(abs(updated[node] - ranks[node]) for node in nodes)
        ranks = updated
        if delta < tol:
            break

    total = sum(ranks.values())
    if total > 0:
        ranks = {node: value / total for node, value in ranks.items()}
    return ranks


def _er_description_length_bits(graph: nx.DiGraph) -> tuple[float, float]:
    node_count = graph.number_of_nodes()
    possible_edges = node_count * (node_count - 1)
    if possible_edges <= 0:
        return 0.0, 0.0

    edge_probability = graph.number_of_edges() / possible_edges
    bits = possible_edges * _bernoulli_entropy(edge_probability)
    return bits, edge_probability


def _block_model_description_length_bits(graph: nx.DiGraph, communities: list[set[str]]) -> tuple[float, float, float]:
    node_count = graph.number_of_nodes()
    if node_count <= 1:
        return 0.0, 0.0, 0.0

    community_index = {}
    for idx, community in enumerate(communities):
        for node in community:
            community_index[node] = idx

    community_sizes = [len(community) for community in communities]
    edge_counts: dict[tuple[int, int], int] = defaultdict(int)
    for source_id, target_id in graph.edges:
        edge_counts[(community_index[source_id], community_index[target_id])] += 1

    label_bits = 0.0
    community_count = len(communities)
    if community_count > 1:
        label_bits = node_count * math.log2(community_count)

    structure_bits = 0.0
    for source_comm, source_size in enumerate(community_sizes):
        for target_comm, target_size in enumerate(community_sizes):
            possible_edges = source_size * target_size
            if source_comm == target_comm:
                possible_edges -= source_size
            if possible_edges <= 0:
                continue

            probability = edge_counts[(source_comm, target_comm)] / possible_edges
            structure_bits += possible_edges * _bernoulli_entropy(probability)

    total_bits = label_bits + structure_bits
    return structure_bits, label_bits, total_bits


def _rounded(value: float) -> float:
    return round(value, 6)


def _top_rows(
    *,
    values: dict[str, float],
    id_to_title: dict[str, str],
    graph: nx.DiGraph | nx.Graph,
    top_k: int,
    extra_key: str | None = None,
) -> list[dict[str, object]]:
    def sort_key(item: tuple[str, float]) -> tuple[float, float, str]:
        node_id, value = item
        degree_hint = 0.0
        if isinstance(graph, nx.DiGraph):
            degree_hint = float(graph.out_degree(node_id) + graph.in_degree(node_id))
        else:
            degree_hint = float(graph.degree(node_id))
        return (-value, -degree_hint, id_to_title[node_id].lower())

    rows = []
    for node_id, value in sorted(values.items(), key=sort_key)[:top_k]:
        row = {
            "id": node_id,
            "title": id_to_title[node_id],
            "value": _rounded(value),
        }
        if extra_key == "out_degree" and isinstance(graph, nx.DiGraph):
            row["out_degree"] = graph.out_degree(node_id)
        if extra_key == "total_degree":
            if isinstance(graph, nx.DiGraph):
                row["total_degree"] = graph.out_degree(node_id) + graph.in_degree(node_id)
            else:
                row["total_degree"] = graph.degree(node_id)
        rows.append(row)
    return rows


def build_link_analytics_report(
    client: JoplinClient,
    *,
    top_k: int = 10,
    pagerank_alpha: float = 0.85,
) -> dict[str, object]:
    link_data: NoteLinkGraph = build_note_link_graph(client)
    directed = link_data.directed_graph
    undirected = link_data.undirected_graph
    node_count = directed.number_of_nodes()
    directed_edge_count = directed.number_of_edges()
    undirected_edge_count = undirected.number_of_edges()
    possible_directed_edges = node_count * (node_count - 1)
    density = directed_edge_count / possible_directed_edges if possible_directed_edges else 0.0

    out_degrees = [directed.out_degree(node) for node in directed.nodes]
    in_degrees = [directed.in_degree(node) for node in directed.nodes]
    degrees = [undirected.degree(node) for node in undirected.nodes]
    local_branching = _local_branching_entropy(directed)
    pagerank = _pagerank_distribution(directed, alpha=pagerank_alpha) if node_count else {}
    entropy_rate = sum(pagerank.get(node, 0.0) * local_branching[node] for node in directed.nodes)

    communities, modularity = _community_structure(undirected)
    er_bits, edge_probability = _er_description_length_bits(directed)
    block_structure_bits, block_label_bits, block_bits = _block_model_description_length_bits(directed, communities)
    raw_adjacency_bits = float(possible_directed_edges)

    branching_values = list(local_branching.values())
    positive_branching_values = [value for value in branching_values if value > 0]
    betweenness = nx.betweenness_centrality(undirected, normalized=True) if node_count else {}

    report = {
        "assumptions": {
            "links_are_unique_per_note_pair": True,
            "local_branching_uses_uniform_outgoing_probabilities": True,
            "entropy_rate_uses_pagerank_stationary_distribution": True,
            "community_detection": "greedy_modularity_communities on undirected projection",
            "compression_proxy": "compare global Bernoulli edge model vs community block model",
            "pagerank_alpha": pagerank_alpha,
        },
        "summary": {
            "note_count": node_count,
            "directed_link_count": directed_edge_count,
            "undirected_connection_count": undirected_edge_count,
            "density": _rounded(density),
            "isolated_note_count": sum(1 for value in degrees if value == 0),
            "sink_note_count": sum(1 for value in out_degrees if value == 0),
            "largest_components": _component_sizes(undirected)[:10],
        },
        "edge_entropy": {
            "naive_edge_probability": _rounded(edge_probability),
            "naive_bernoulli_entropy_per_possible_edge_bits": _rounded(_bernoulli_entropy(edge_probability)),
            "naive_total_edge_entropy_bits": _rounded(er_bits),
        },
        "degree_entropy": {
            "undirected_degree_entropy_bits": _rounded(_distribution_entropy(degrees)),
            "out_degree_entropy_bits": _rounded(_distribution_entropy(out_degrees)),
            "in_degree_entropy_bits": _rounded(_distribution_entropy(in_degrees)),
        },
        "branching_entropy": {
            "mean_all_notes_bits": _rounded(sum(branching_values) / node_count if node_count else 0.0),
            "mean_linking_notes_bits": _rounded(
                sum(positive_branching_values) / len(positive_branching_values) if positive_branching_values else 0.0
            ),
            "median_all_notes_bits": _rounded(median(branching_values) if branching_values else 0.0),
            "max_bits": _rounded(max(branching_values) if branching_values else 0.0),
            "entropy_rate_bits": _rounded(entropy_rate),
        },
        "community_structure": {
            "community_count": len(communities),
            "modularity": _rounded(modularity),
            "largest_communities": sorted((len(community) for community in communities), reverse=True)[:10],
        },
        "compression_proxy": {
            "raw_adjacency_bits": _rounded(raw_adjacency_bits),
            "global_bernoulli_description_length_bits": _rounded(er_bits),
            "community_block_structure_bits": _rounded(block_structure_bits),
            "community_label_bits": _rounded(block_label_bits),
            "community_block_description_length_bits": _rounded(block_bits),
            "community_structure_savings_vs_global_bits": _rounded(er_bits - block_structure_bits),
            "community_model_savings_vs_global_bits": _rounded(er_bits - block_bits),
            "community_model_savings_vs_raw_bits": _rounded(raw_adjacency_bits - block_bits),
            "community_model_ratio_vs_global": _rounded(block_bits / er_bits) if er_bits else 0.0,
        },
        "top_notes": {
            "branching_entropy": _top_rows(
                values=local_branching,
                id_to_title=link_data.id_to_title,
                graph=directed,
                top_k=top_k,
                extra_key="out_degree",
            ),
            "pagerank": _top_rows(
                values=pagerank,
                id_to_title=link_data.id_to_title,
                graph=directed,
                top_k=top_k,
                extra_key="total_degree",
            ),
            "bridge_value": _top_rows(
                values=betweenness,
                id_to_title=link_data.id_to_title,
                graph=undirected,
                top_k=top_k,
                extra_key="total_degree",
            ),
        },
    }
    return report


def _print_top_rows(rows: list[dict[str, object]], value_label: str) -> None:
    for row in rows:
        extras = []
        if "out_degree" in row:
            extras.append(f"out={row['out_degree']}")
        if "total_degree" in row:
            extras.append(f"deg={row['total_degree']}")
        extras_text = f" ({', '.join(extras)})" if extras else ""
        print(f"- {row['title']} [{row['id']}]  {value_label}={row['value']}{extras_text}")


def handle_analytics_links(args, client: JoplinClient) -> int:
    report = build_link_analytics_report(
        client,
        top_k=args.top_k,
        pagerank_alpha=args.pagerank_alpha,
    )

    summary = report["summary"]
    edge_entropy = report["edge_entropy"]
    degree_entropy = report["degree_entropy"]
    branching = report["branching_entropy"]
    communities = report["community_structure"]
    compression = report["compression_proxy"]

    print("Link Structure Summary")
    print("----------------------")
    print(f"Notes: {summary['note_count']}")
    print(f"Directed links: {summary['directed_link_count']}")
    print(f"Undirected connections: {summary['undirected_connection_count']}")
    print(f"Density: {summary['density']}")
    print(f"Isolated notes: {summary['isolated_note_count']}")
    print(f"Sink notes (no outgoing links): {summary['sink_note_count']}")
    print(f"Largest components: {', '.join(str(size) for size in summary['largest_components'])}")

    print("\nEntropy")
    print("-------")
    print(f"Naive edge entropy per possible edge (bits): {edge_entropy['naive_bernoulli_entropy_per_possible_edge_bits']}")
    print(f"Naive total edge entropy (bits): {edge_entropy['naive_total_edge_entropy_bits']}")
    print(f"Undirected degree entropy (bits): {degree_entropy['undirected_degree_entropy_bits']}")
    print(f"Out-degree entropy (bits): {degree_entropy['out_degree_entropy_bits']}")
    print(f"In-degree entropy (bits): {degree_entropy['in_degree_entropy_bits']}")
    print(f"Mean local branching entropy, all notes (bits): {branching['mean_all_notes_bits']}")
    print(f"Mean local branching entropy, linking notes only (bits): {branching['mean_linking_notes_bits']}")
    print(f"Entropy rate (bits/step): {branching['entropy_rate_bits']}")

    print("\nStructure")
    print("---------")
    print(f"Communities: {communities['community_count']}")
    print(f"Modularity: {communities['modularity']}")
    print(f"Largest communities: {', '.join(str(size) for size in communities['largest_communities'])}")
    print(f"Raw adjacency description (bits): {compression['raw_adjacency_bits']}")
    print(f"Global Bernoulli description length (bits): {compression['global_bernoulli_description_length_bits']}")
    print(f"Community block structure bits (without labels): {compression['community_block_structure_bits']}")
    print(f"Community label bits: {compression['community_label_bits']}")
    print(f"Community block description length (bits): {compression['community_block_description_length_bits']}")
    print(f"Community-structure savings vs global (bits): {compression['community_structure_savings_vs_global_bits']}")
    print(f"Community-model savings vs global (bits): {compression['community_model_savings_vs_global_bits']}")

    print("\nTop Notes by Branching Entropy")
    print("------------------------------")
    _print_top_rows(report["top_notes"]["branching_entropy"], "H")

    print("\nTop Notes by PageRank")
    print("---------------------")
    _print_top_rows(report["top_notes"]["pagerank"], "PR")

    print("\nTop Notes by Bridge Value")
    print("-------------------------")
    _print_top_rows(report["top_notes"]["bridge_value"], "B")

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWrote JSON report: {output_path}")

    return 0
