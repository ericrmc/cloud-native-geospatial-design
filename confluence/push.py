#!/usr/bin/env python3
"""
Push the converted Confluence storage-format pages to a Confluence Cloud space.

First run creates the pages: page 0 (index.xml) becomes the parent; pages
01–15 are created as children of it. Subsequent runs update the same pages
in place (idempotent), keyed by the page IDs stored in ./state.json.

Required environment variables:
    CONF_URL      Confluence Cloud base URL, e.g. https://acme.atlassian.net
    CONF_EMAIL    Atlassian account email used for the API token
    CONF_TOKEN    Atlassian API token (https://id.atlassian.com/manage-profile/security/api-tokens)
    SPACE_KEY     Space key, e.g. "DESIGN"

Optional:
    PARENT_ID     ID of an existing Confluence page to be the parent of the
                  index page. If unset, the index page is created at the
                  space root.
    DRY_RUN=1     Print what would be sent without making any HTTP calls.

Usage:
    python push.py
    DRY_RUN=1 python push.py

State:
    ./state.json   Maps output filename -> {"id": "...", "version": N}.
                   Created on first successful run. Delete it to force
                   re-creation of pages (which will fail if titles still
                   exist in the space — Confluence requires unique titles
                   per space).
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGES_DIR = HERE / "pages"
MANIFEST_PATH = HERE / "manifest.json"
STATE_PATH = HERE / "state.json"

# Files in upload order. The first entry becomes the parent of the rest.
PAGE_ORDER = [
    "index.xml",
    "01_principles.xml",
    "02_architecture.xml",
    "03_authorisation.xml",
    "04_data_layout.xml",
    "05_vector_tiles.xml",
    "06_ogc_features_api.xml",
    "07_query_layer.xml",
    "08_raster_services.xml",
    "09_routing.xml",
    "10_discovery.xml",
    "11_editing_pipeline.xml",
    "12_deployment.xml",
    "13_operations.xml",
    "14_client_integration.xml",
    "15_map_client.xml",
    "16_design_decisions.xml",
    "17_further_directions.xml",
]


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None and default is None:
        return None
    return v if v is not None else default


def require_env(name: str) -> str:
    v = env(name)
    if not v:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return v


class Confluence:
    def __init__(self, base_url: str, email: str, token: str, dry_run: bool = False) -> None:
        self.base = base_url.rstrip("/")
        self.dry_run = dry_run
        auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        self.headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self.base}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        if self.dry_run:
            print(f"  [DRY] {method} {url}")
            if body is not None:
                preview = {k: v for k, v in body.items() if k != "body"}
                print(f"        body keys: {list(body.keys())} (preview: {preview})")
            return {"id": "DRYRUN", "version": {"number": 0}}
        req = urllib.request.Request(url, data=data, method=method, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(
                f"  HTTP {e.code} on {method} {path}\n  Response: {err_body[:1000]}",
                file=sys.stderr,
            )
            raise

    def create_page(
        self, space_key: str, title: str, body_storage: str, parent_id: str | None
    ) -> dict:
        payload: dict = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {"storage": {"value": body_storage, "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        return self._request("POST", "/wiki/rest/api/content", payload)

    def update_page(
        self,
        page_id: str,
        title: str,
        body_storage: str,
        version_number: int,
        parent_id: str | None,
    ) -> dict:
        payload: dict = {
            "id": page_id,
            "type": "page",
            "title": title,
            "version": {"number": version_number},
            "body": {"storage": {"value": body_storage, "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        return self._request("PUT", f"/wiki/rest/api/content/{page_id}", payload)


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(
            f"Manifest not found at {MANIFEST_PATH}. Run convert.py first.",
            file=sys.stderr,
        )
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    base_url = require_env("CONF_URL")
    email = require_env("CONF_EMAIL")
    token = require_env("CONF_TOKEN")
    space_key = require_env("SPACE_KEY")
    parent_root = env("PARENT_ID")
    dry_run = env("DRY_RUN") == "1"

    if dry_run:
        print("DRY RUN — no HTTP calls will be made.\n")

    client = Confluence(base_url, email, token, dry_run=dry_run)
    state = load_state()

    # Resolve the parent for child pages: it's the page corresponding to
    # index.xml once that exists.
    root_filename = "index.xml"
    root_state = state.get(root_filename)
    root_page_id: str | None = root_state["id"] if root_state else None

    for filename in PAGE_ORDER:
        page_path = PAGES_DIR / filename
        if not page_path.exists():
            print(f"  Skipping {filename} (not found)")
            continue
        body = page_path.read_text(encoding="utf-8")
        meta = manifest.get(filename, {})
        title = meta.get("title", filename)

        is_root = filename == root_filename
        parent_id = parent_root if is_root else root_page_id

        existing = state.get(filename)
        if existing:
            new_version = int(existing.get("version", 1)) + 1
            print(f"  Updating: {title}  (page id {existing['id']}, version -> {new_version})")
            result = client.update_page(
                existing["id"], title, body, new_version, parent_id
            )
            state[filename] = {
                "id": result.get("id", existing["id"]),
                "version": new_version,
                "title": title,
            }
        else:
            print(f"  Creating: {title}  (parent {parent_id or 'space root'})")
            result = client.create_page(space_key, title, body, parent_id)
            page_id = result.get("id", "DRYRUN")
            state[filename] = {
                "id": page_id,
                "version": 1,
                "title": title,
            }
            if is_root and not dry_run:
                root_page_id = page_id

        # Persist after each page so an interrupted run can resume.
        if not dry_run:
            save_state(state)

    print(f"\nDone. State written to {STATE_PATH.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
