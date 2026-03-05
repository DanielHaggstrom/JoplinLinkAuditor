"""Environment loading helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def load_env_file(path: str = ".env") -> None:
    """Load KEY=VALUE pairs from a local .env file into os.environ (setdefault)."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            os.environ.setdefault(key, value)


def resolve_setting(
    explicit: Optional[str],
    env_key: str,
    default: Optional[str] = None,
    required: bool = False,
) -> Optional[str]:
    """Resolve a setting from explicit value, then environment, then default."""
    if explicit:
        return explicit
    value = os.getenv(env_key, default)
    if required and not value:
        raise ValueError(f"Missing required setting: {env_key}")
    return value
