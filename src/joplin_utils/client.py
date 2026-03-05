"""Thin Joplin Data API client with pagination."""

from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Optional

import requests
from requests.adapters import HTTPAdapter, Retry


class JoplinClient:
    def __init__(self, base_url: str, token: str):
        if not token:
            raise ValueError("Joplin token is required.")

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.mount(
            "http://",
            HTTPAdapter(
                max_retries=Retry(
                    total=5,
                    backoff_factor=0.3,
                    status_forcelist=[429, 500, 502, 503, 504],
                )
            ),
        )

    def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> dict:
        query: Dict[str, str] = dict(params or {})
        query["token"] = self.token
        response = self.session.get(f"{self.base_url}{path}", params=query, timeout=30)
        response.raise_for_status()
        return response.json()

    def paginate(
        self,
        path: str,
        fields: Iterable[str],
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Iterator[dict]:
        params: Dict[str, str] = dict(extra_params or {})
        params["fields"] = ",".join(fields)

        page = 1
        while True:
            params["page"] = str(page)
            data = self._get(path, params=params)
            for item in data.get("items", []) or []:
                yield item
            if not data.get("has_more"):
                break
            page += 1

    def list_notes(self, fields: Iterable[str]) -> List[dict]:
        return list(self.paginate("/notes", fields=fields, extra_params={"type": "note"}))

    def list_tags(self, fields: Iterable[str]) -> List[dict]:
        return list(self.paginate("/tags", fields=fields))

    def list_notes_for_tag(self, tag_id: str, fields: Iterable[str]) -> List[dict]:
        return list(self.paginate(f"/tags/{tag_id}/notes", fields=fields))
