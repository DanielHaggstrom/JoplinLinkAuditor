"""Helpers for building note-link graphs from the Joplin API."""

from __future__ import annotations

from dataclasses import dataclass
import re

import networkx as nx

from joplin_utils.client import JoplinClient

LINK_RE = re.compile(r"\[.*?\]\(:/([a-fA-F0-9]{32})\)")


@dataclass(slots=True)
class NoteLinkGraph:
    """Structured note/link data used by graph-based analytics."""

    notes: list[dict]
    id_to_title: dict[str, str]
    directed_graph: nx.DiGraph

    @property
    def undirected_graph(self) -> nx.Graph:
        return self.directed_graph.to_undirected()


def extract_note_links(body: str) -> list[str]:
    return LINK_RE.findall(body or "")


def build_note_link_graph(client: JoplinClient) -> NoteLinkGraph:
    notes = client.list_notes(fields=["id", "title", "body"])
    id_to_title = {note["id"]: (note.get("title") or "").strip() for note in notes}

    graph = nx.DiGraph()
    graph.add_nodes_from(id_to_title.keys())

    for note in notes:
        source_id = note["id"]
        # Repeated links inside a note are treated as a single structural edge.
        targets = {
            target_id
            for target_id in extract_note_links(note.get("body", ""))
            if target_id in id_to_title and target_id != source_id
        }
        for target_id in targets:
            graph.add_edge(source_id, target_id)

    return NoteLinkGraph(
        notes=notes,
        id_to_title=id_to_title,
        directed_graph=graph,
    )
