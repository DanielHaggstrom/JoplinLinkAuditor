"""Command line entrypoint for joplin-utils."""

from __future__ import annotations

import argparse
import sys

from joplin_utils.client import JoplinClient
from joplin_utils.commands.analytics import handle_analytics_created
from joplin_utils.commands.exporters import handle_export_full, handle_export_retrospectives
from joplin_utils.commands.reachability import handle_reachability
from joplin_utils.env import load_env_file, resolve_setting

DEFAULT_BASE_URL = "http://localhost:41184"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="joplin-utils",
        description="CLI utilities for Joplin reachability audit, exports, and creation analytics.",
    )
    parser.add_argument("--env-file", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument("--base-url", help="Joplin base URL (overrides env)")
    parser.add_argument("--token", help="Joplin API token (overrides env)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_reachability = subparsers.add_parser(
        "reachability",
        help="Audit notes unreachable from an index note.",
    )
    p_reachability.add_argument("--index-note-id", required=True, help="Index/root note id")
    p_reachability.add_argument("--output-json", help="Optional JSON report output path")
    p_reachability.set_defaults(handler=handle_reachability)

    p_export_full = subparsers.add_parser(
        "export-full",
        help="Export full vault text with tags and metadata.",
    )
    p_export_full.add_argument("--output", default="full_zettelkasten.txt", help="Output path")
    p_export_full.set_defaults(handler=handle_export_full)

    p_export_retro = subparsers.add_parser(
        "export-retrospectives",
        help="Export retrospective notes by title match.",
    )
    p_export_retro.add_argument("--output", default="journals.txt", help="Output path")
    p_export_retro.add_argument(
        "--title-contains",
        default="Retrospectiva",
        help="Case-insensitive title filter",
    )
    p_export_retro.set_defaults(handler=handle_export_retrospectives)

    p_analytics = subparsers.add_parser(
        "analytics-created",
        help="Compute monthly note creation counts.",
    )
    p_analytics.add_argument("--output-csv", help="Optional CSV output path")
    p_analytics.add_argument("--output-plot", help="Optional PNG chart output path")
    p_analytics.set_defaults(handler=handle_analytics_created)

    return parser


def _build_client_from_args(args: argparse.Namespace) -> JoplinClient:
    load_env_file(args.env_file)
    base_url = resolve_setting(args.base_url, "JOPLIN_BASE_URL", default=DEFAULT_BASE_URL, required=True)
    token = resolve_setting(args.token, "JOPLIN_TOKEN", required=True)
    return JoplinClient(base_url=base_url, token=token)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        client = _build_client_from_args(args)
        return args.handler(args, client)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
