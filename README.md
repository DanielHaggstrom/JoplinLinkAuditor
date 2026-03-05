# Joplin Utilities

`joplin-utils` is a focused CLI toolkit for:

- Reachability audit of note links
- Text export (full vault export with tags)
- Text export for retrospectives/journals
- Note creation analytics (monthly counts + optional chart)

This repository intentionally excludes the old tagging pipeline and related state files.

## Features

- Uses the local Joplin Data API (`http://localhost:41184` by default)
- Reads secrets from `.env` (no hardcoded tokens in source)
- Supports paginated Joplin endpoints
- Provides one CLI with consistent flags and outputs

## Installation

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .
```

## Configuration

1. Copy `.env.example` to `.env`
2. Fill in your Joplin API token

```env
JOPLIN_BASE_URL=http://localhost:41184
JOPLIN_TOKEN=your_token_here
```

You can also override values with CLI flags:

- `--base-url`
- `--token`
- `--env-file`

## CLI Quick Start

```bash
joplin-utils --help
```

### Reachability audit

```bash
joplin-utils reachability --index-note-id <NOTE_ID>
joplin-utils reachability --index-note-id <NOTE_ID> --output-json unreachable.json
```

### Full export with tags

```bash
joplin-utils export-full --output full_zettelkasten.txt
```

### Retrospective export

```bash
joplin-utils export-retrospectives --output journals.txt --title-contains Retrospectiva
```

### Note creation analytics

```bash
joplin-utils analytics-created --output-csv note_creation.csv --output-plot note_creation.png
```

See [CLI reference](docs/CLI.md) for complete command options.

## Security

- `.env` is ignored by git.
- API tokens are read at runtime and never stored in source code.

## Publishing as a public repository

```bash
git init
git add .
git commit -m "Initial commit: joplin-utils CLI"
```

Then create a GitHub repo and push:

```bash
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## License

[MIT](LICENSE) - Copyright (c) 2026 Daniel Häggström
