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

Export every note to one text file, including title, id, tags, created/updated timestamps, and body.

```bash
joplin-utils export-full [--output full_zettelkasten.txt]
```

Options:

- `--output` output text path (default: `full_zettelkasten.txt`)

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
