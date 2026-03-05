"""Reachability audit command."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

import networkx as nx

from joplin_utils.client import JoplinClient

LINK_RE = re.compile(r"\[.*?\]\(:/([a-fA-F0-9]{32})\)")


def _extract_note_links(body: str) -> List[str]:
    return LINK_RE.findall(body or "")


def build_reachability_report(client: JoplinClient, index_note_id: str) -> Dict[str, object]:
    notes = client.list_notes(fields=["id", "title", "body"])
    note_ids = {note["id"] for note in notes}
    id_to_title = {note["id"]: (note.get("title") or "").strip() for note in notes}

    graph = nx.Graph()
    graph.add_nodes_from(note_ids)

    for note in notes:
        source_id = note["id"]
        for target_id in _extract_note_links(note.get("body", "")):
            if target_id in note_ids:
                graph.add_edge(source_id, target_id)

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
        "total_notes": len(notes),
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
