"""Analytics commands."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from joplin_utils.client import JoplinClient


def _monthly_creation_counts(client: JoplinClient) -> List[Dict[str, object]]:
    notes = client.list_notes(fields=["id", "created_time"])
    bucket = Counter()

    for note in notes:
        created_ms = note.get("created_time")
        if not created_ms:
            continue
        dt = datetime.fromtimestamp(created_ms / 1000)
        month_key = f"{dt.year:04d}-{dt.month:02d}"
        bucket[month_key] += 1

    rows = [{"month": month, "count": bucket[month]} for month in sorted(bucket.keys())]
    return rows


def _write_csv(rows: List[Dict[str, object]], output: Path) -> None:
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["month", "count"])
        writer.writeheader()
        writer.writerows(rows)


def _write_plot(rows: List[Dict[str, object]], output: Path) -> None:
    if not rows:
        return

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = [datetime.strptime(row["month"], "%Y-%m") for row in rows]
    y = [row["count"] for row in rows]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(x, y, marker="o", linewidth=1.5)
    ax.set_xlabel("Month")
    ax.set_ylabel("Created Notes")
    ax.set_title("Joplin Notes Created Per Month")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def handle_analytics_created(args, client: JoplinClient) -> int:
    rows = _monthly_creation_counts(client)

    if not rows:
        print("No notes found.")
        return 0

    print("Month    Count")
    print("-------  -----")
    for row in rows:
        print(f"{row['month']}  {row['count']}")

    if args.output_csv:
        csv_path = Path(args.output_csv)
        _write_csv(rows, csv_path)
        print(f"\nWrote CSV: {csv_path}")

    if args.output_plot:
        png_path = Path(args.output_plot)
        _write_plot(rows, png_path)
        print(f"Wrote plot: {png_path}")

    return 0
