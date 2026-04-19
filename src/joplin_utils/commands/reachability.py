"""Reachability audit command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import networkx as nx

from joplin_utils.client import JoplinClient
from joplin_utils.link_graph import build_note_link_graph


def build_reachability_report(client: JoplinClient, index_note_id: str) -> Dict[str, object]:
    link_data = build_note_link_graph(client)
    graph = link_data.undirected_graph
    note_ids = set(link_data.id_to_title.keys())
    id_to_title = link_data.id_to_title

    if index_note_id not in graph:
        raise ValueError(f"Index note id {index_note_id} not found in note set.")

    connected = nx.node_connected_component(graph, index_note_id)
    unreachable_ids = sorted(
        [note_id for note_id in note_ids if note_id not in connected],
        key=lambda note_id: (id_to_title.get(note_id, "").lower(), note_id),
    )
    unreachable = [{"id": note_id, "title": id_to_title.get(note_id, "")} for note_id in unreachable_ids]

    return {
        "index_note_id": index_note_id,
        "total_notes": len(link_data.notes),
        "connected_count": len(connected),
        "unreachable_count": len(unreachable),
        "unreachable": unreachable,
    }


def handle_reachability(args, client: JoplinClient) -> int:
    report = build_reachability_report(client, args.index_note_id)

    print(f"Index note id: {report['index_note_id']}")
    print(f"Total notes: {report['total_notes']}")
    print(f"Connected notes: {report['connected_count']}")
    print(f"Unreachable notes: {report['unreachable_count']}")
    print("")

    for row in report["unreachable"]:
        print(f"- {row['title']} ({row['id']})")

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nWrote JSON report: {output_path}")

    return 0
