# CLI Reference

All commands support these global options:

- `--env-file` path to `.env` file (default: `.env`)
- `--base-url` Joplin API base URL (overrides env)
- `--token` Joplin API token (overrides env)

## `reachability`

Audit which notes are disconnected from an index note in the undirected link graph.

```bash
joplin-utils reachability [--index-note-id <NOTE_ID>] [--output-json report.json]
```

Options:

- `--index-note-id` optional note id used as the root of connectivity
- `JOPLIN_REACHABILITY_INDEX_NOTE_ID` env fallback when `--index-note-id` is omitted
- `--output-json` optional JSON report output path

## `export-full`

Export every note with title, id, tags, created/updated timestamps, and body.

```bash
joplin-utils export-full [--mode combined] [--output full_zettelkasten.txt]
joplin-utils export-full --mode per-note [--output .exports/full_zettelkasten]
```

Options:

- `--mode` export mode: `combined` for one file, `per-note` for one file per note id (default: `combined`)
- `--output` output file path for `combined`, or target directory for `per-note`; when omitted, `combined` defaults to `full_zettelkasten.txt` and `per-note` defaults to `.exports/full_zettelkasten`

Per-note mode writes files as `NOTE_ID.md`.

## `export-retrospectives`

Export notes with titles containing a term (default: `Retrospectiva`) into one text file.

```bash
joplin-utils export-retrospectives [--output journals.txt] [--title-contains Retrospectiva]
```

Options:

- `--output` output text path (default: `journals.txt`)
- `--title-contains` title substring filter, case-insensitive

## `analytics-created`

Build month-by-month counts of created notes and optionally save CSV + PNG.

```bash
joplin-utils analytics-created [--output-csv note_creation.csv] [--output-plot note_creation.png]
```

Options:

- `--output-csv` optional CSV output path
- `--output-plot` optional PNG chart output path

## `analytics-links`

Compute link-graph entropy, local branching, community structure, and a simple compression proxy.

```bash
joplin-utils analytics-links [--output-json link_metrics.json] [--top-k 10] [--pagerank-alpha 0.85]
```

Options:

- `--output-json` optional JSON report output path
- `--top-k` number of ranked notes to show in the terminal output (default: `10`)
- `--pagerank-alpha` PageRank damping factor used to weight the entropy-rate summary (default: `0.85`)
