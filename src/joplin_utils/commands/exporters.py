"""Export commands."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from joplin_utils.client import JoplinClient


def _ms_to_iso(ms: int) -> str:
    if not ms:
        return "-"
    return datetime.fromtimestamp(ms / 1000).isoformat(sep=" ", timespec="minutes")


def _build_note_tag_map(client: JoplinClient) -> Dict[str, List[str]]:
    note_tags: Dict[str, List[str]] = {}
    tags = client.list_tags(fields=["id", "title"])

    for tag in tags:
        tag_title = (tag.get("title") or "").strip()
        if not tag_title:
            continue
        tag_note_ids = client.list_notes_for_tag(tag["id"], fields=["id"])
        for note in tag_note_ids:
            note_tags.setdefault(note["id"], []).append(tag_title)

    for note_id in note_tags:
        note_tags[note_id] = sorted(set(note_tags[note_id]))

    return note_tags


def export_full_dump(client: JoplinClient, output: Path) -> int:
    notes = client.list_notes(fields=["id", "title", "body", "created_time", "updated_time"])
    notes.sort(key=lambda note: note.get("created_time") or 0)
    note_tags = _build_note_tag_map(client)

    sep = "=" * 40
    chunks = []
    for note in notes:
        note_id = note["id"]
        title = (note.get("title") or "").strip()
        body = (note.get("body") or "").strip()
        tags = ", ".join(note_tags.get(note_id, [])) or "—"
        created = _ms_to_iso(note.get("created_time"))
        updated = _ms_to_iso(note.get("updated_time"))

        chunks.append(
            f"[{note_id}] {title}\n"
            f"Tags: {tags}\n"
            f"Created: {created}  |  Updated: {updated}\n\n"
            f"{body}"
        )

    output.write_text(("\n\n" + sep + "\n\n").join(chunks), encoding="utf-8")
    return len(notes)


def export_retrospectives(
    client: JoplinClient,
    output: Path,
    title_contains: str,
) -> int:
    needle = (title_contains or "").lower()
    notes = client.list_notes(fields=["id", "title", "body", "created_time"])
    filtered = [
        note
        for note in notes
        if needle in (note.get("title") or "").lower()
    ]
    filtered.sort(key=lambda note: note.get("created_time") or 0)

    sep = "=" * 40
    chunks = []
    for note in filtered:
        title = (note.get("title") or "").strip()
        body = (note.get("body") or "").strip()
        chunks.append(f"{title}\n\n{body}")

    output.write_text(("\n\n" + sep + "\n\n").join(chunks), encoding="utf-8")
    return len(filtered)


def handle_export_full(args, client: JoplinClient) -> int:
    output = Path(args.output)
    count = export_full_dump(client, output)
    print(f"Exported {count} notes to {output}")
    return 0


def handle_export_retrospectives(args, client: JoplinClient) -> int:
    output = Path(args.output)
    count = export_retrospectives(client, output, args.title_contains)
    print(f"Exported {count} retrospective notes to {output}")
    return 0
