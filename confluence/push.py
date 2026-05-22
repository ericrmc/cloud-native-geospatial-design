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
    ./state-<host>-<space>.json
                   Maps output filename -> {"id": "...", "version": N} for a
                   specific Confluence space (one file per (host, space) pair,
                   so pushing to multiple spaces does not clobber the page
                   IDs of any one of them). Created on first successful run.
                   Delete to force re-creation (which will fail if titles
                   still exist in the space — Confluence requires unique
                   titles per space).
"""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGES_DIR = HERE / "pages"
DIAGRAMS_DIR = HERE / "diagrams"
MANIFEST_PATH = HERE / "manifest.json"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_multipart(file_path: Path, comment: str = "") -> tuple[bytes, str]:
    """Construct a multipart/form-data body for Confluence attachment upload.

    Returns (body_bytes, content_type_header).
    """
    boundary = "----PushPyMultipart" + secrets.token_hex(16)
    mime, _ = mimetypes.guess_type(file_path.name)
    if mime is None:
        mime = "application/octet-stream"

    parts: list[bytes] = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode()
    )
    parts.append(f"Content-Type: {mime}\r\n\r\n".encode())
    parts.append(file_path.read_bytes())
    if comment:
        parts.append(f"\r\n--{boundary}\r\n".encode())
        parts.append(b'Content-Disposition: form-data; name="comment"\r\n\r\n')
        parts.append(comment.encode("utf-8"))
    parts.append(f"\r\n--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="minorEdit"\r\n\r\n')
    parts.append(b"true")
    parts.append(f"\r\n--{boundary}--\r\n".encode())

    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def state_path(base_url: str, space_key: str) -> Path:
    """Per-(host, space) state file path.

    Each (Confluence host, space key) pair gets its own state file so the
    same local edits can be pushed to multiple spaces without their page
    ID mappings interfering. Filenames are gitignored.
    """
    host = urllib.parse.urlparse(base_url).hostname or "unknown"
    safe_host = host.replace(".", "_")
    return HERE / f"state-{safe_host}-{space_key}.json"

# Files in upload order. The first entry becomes the parent of the rest.
PAGE_ORDER = [
    "index.xml",
    "00_index.xml",
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
    "18_glossary_and_references.xml",
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

    def _multipart_request(
        self, method: str, path: str, file_path: Path, comment: str
    ) -> dict:
        url = f"{self.base}{path}"
        if self.dry_run:
            size = file_path.stat().st_size
            print(f"    [DRY] {method} {url}  (multipart upload: {file_path.name}, {size} bytes)")
            return {"results": [{"id": f"DRYRUN_ATT_{file_path.name}"}]}
        body, content_type = build_multipart(file_path, comment=comment)
        headers = {
            "Authorization": self.headers["Authorization"],
            "Content-Type": content_type,
            "Accept": "application/json",
            # Confluence requires this header to disable XSRF check on attachment uploads.
            "X-Atlassian-Token": "no-check",
        }
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            e.response_body = err_body  # type: ignore[attr-defined]
            print(
                f"    HTTP {e.code} on {method} {path}\n    Response: {err_body[:1000]}",
                file=sys.stderr,
            )
            raise

    def get_attachment(self, attachment_id: str) -> dict:
        """Fetch attachment metadata, including size and version."""
        return self._request(
            "GET",
            f"/wiki/rest/api/content/{attachment_id}?expand=extensions,version",
        )

    def create_attachment(self, page_id: str, file_path: Path) -> str:
        """Upload a new attachment to a page. Returns the attachment ID."""
        result = self._multipart_request(
            "POST",
            f"/wiki/rest/api/content/{page_id}/child/attachment",
            file_path,
            comment="Diagram rendered by convert.py",
        )
        results = result.get("results", []) if isinstance(result, dict) else []
        if results and "id" in results[0]:
            return results[0]["id"]
        return ""

    def update_attachment(
        self, page_id: str, attachment_id: str, file_path: Path
    ) -> str:
        """Replace an existing attachment's binary data. Returns the attachment ID.

        Confluence Cloud sometimes returns HTTP 500 with an
        `UnexpectedRollbackException` from this endpoint:

        1. When the uploaded bytes are byte-identical to the current attachment
           content, its inner version-bump transaction marks itself
           rollback-only and the outer transaction throws. The attachment is
           unchanged in that case, so we verify by size and treat the upload
           as a no-op success.
        2. When the attachment's server-side version chain is in a degraded
           state (a previous upload was partial, or a manual deletion left
           stranded metadata). In that case the local and server sizes
           disagree, the version-bump can't proceed, and we fall back to
           deleting the broken attachment record and creating a new one with
           the same filename. Pages reference attachments by filename in
           storage XML, so the page keeps rendering against the new
           attachment ID — only the ID stored in our state file changes.
        """
        try:
            result = self._multipart_request(
                "POST",
                f"/wiki/rest/api/content/{page_id}/child/attachment/{attachment_id}/data",
                file_path,
                comment="Diagram re-rendered by convert.py",
            )
        except urllib.error.HTTPError as e:
            body = getattr(e, "response_body", "") or ""
            if e.code == 500 and "UnexpectedRollbackException" in body:
                meta = None
                try:
                    meta = self.get_attachment(attachment_id)
                except urllib.error.HTTPError:
                    print(
                        f"    Rollback received and metadata fetch failed; falling back to delete + recreate.",
                        file=sys.stderr,
                    )
                if meta is not None:
                    server_size = meta.get("extensions", {}).get("fileSize")
                    local_size = file_path.stat().st_size
                    if server_size is not None and int(server_size) == local_size:
                        print(
                            f"    Rollback recovered: attachment {attachment_id} already matches local content ({local_size} bytes). Continuing."
                        )
                        return attachment_id
                    print(
                        f"    Rollback received and server size ({server_size}) != local size ({local_size}); attachment record is degraded. Falling back to delete + recreate.",
                        file=sys.stderr,
                    )
                # Delete the broken attachment and recreate.
                try:
                    self.delete_attachment(attachment_id)
                except urllib.error.HTTPError as de:
                    if de.code not in (404, 410):
                        print(
                            f"    Delete of degraded attachment {attachment_id} failed ({de.code}); re-raising.",
                            file=sys.stderr,
                        )
                        raise e
                new_id = self.create_attachment(page_id, file_path)
                if not new_id:
                    print(
                        f"    Recreate did not return an attachment ID; re-raising original error.",
                        file=sys.stderr,
                    )
                    raise e
                print(
                    f"    Rollback recovered via recreate: {attachment_id} → {new_id}."
                )
                return new_id
            raise
        if isinstance(result, dict):
            if "id" in result:
                return result["id"]
            results = result.get("results", [])
            if results and "id" in results[0]:
                return results[0]["id"]
        return attachment_id

    def delete_attachment(self, attachment_id: str) -> None:
        """Delete an attachment (which is a content object in Confluence)."""
        self._request("DELETE", f"/wiki/rest/api/content/{attachment_id}")

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


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict, path: Path) -> None:
    path.write_text(
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

    state_file = state_path(base_url, space_key)
    print(f"Target: {base_url}  space={space_key}")
    print(f"State:  {state_file.name}\n")

    client = Confluence(base_url, email, token, dry_run=dry_run)
    state = load_state(state_file)

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
        prior_attachments = (existing or {}).get("attachments", {}) if existing else {}

        if existing:
            new_version = int(existing.get("version", 1)) + 1
            print(f"  Updating: {title}  (page id {existing['id']}, version -> {new_version})")
            client.update_page(
                existing["id"], title, body, new_version, parent_id
            )
            # Update returns the same id; keep the real one for attachment ops.
            page_id = existing["id"]
            state[filename] = {
                "id": page_id,
                "version": new_version,
                "title": title,
                "attachments": prior_attachments,
            }
        else:
            print(f"  Creating: {title}  (parent {parent_id or 'space root'})")
            result = client.create_page(space_key, title, body, parent_id)
            page_id = result.get("id", "DRYRUN")
            state[filename] = {
                "id": page_id,
                "version": 1,
                "title": title,
                "attachments": {},
            }
            if is_root and not dry_run:
                root_page_id = page_id

        # Sync diagram attachments for this page.
        wanted = meta.get("attachments", [])
        if wanted or prior_attachments:
            state[filename]["attachments"] = sync_attachments(
                client, page_id, wanted, prior_attachments, dry_run=dry_run
            )

        # Persist after each page so an interrupted run can resume.
        if not dry_run:
            save_state(state, state_file)

    print(f"\nDone. State written to {state_file.name}.")
    return 0


def sync_attachments(
    client: Confluence,
    page_id: str,
    wanted: list[str],
    prior: dict,
    dry_run: bool = False,
) -> dict:
    """Upload, update, or delete attachments so the page matches `wanted`.

    `prior` is the previous {filename: {"id": ..., "hash": ...}} for this page.
    Returns the new attachments dict to persist in state.
    """
    new_attachments: dict = {}

    for name in wanted:
        path = DIAGRAMS_DIR / name
        if not path.exists():
            print(f"    Missing local diagram file: {name}", file=sys.stderr)
            continue
        current_hash = file_sha256(path)
        prev = prior.get(name)
        if prev and prev.get("hash") == current_hash and prev.get("id"):
            print(f"    Attachment unchanged: {name}")
            new_attachments[name] = prev
            continue
        if prev and prev.get("id"):
            print(f"    Updating attachment: {name}")
            att_id = client.update_attachment(page_id, prev["id"], path)
        else:
            print(f"    Uploading attachment: {name}")
            att_id = client.create_attachment(page_id, path)
        new_attachments[name] = {"id": att_id, "hash": current_hash}

    # Delete attachments no longer referenced.
    orphans = set(prior) - set(wanted)
    for name in orphans:
        att_id = prior[name].get("id")
        if not att_id or att_id.startswith("DRYRUN"):
            continue
        print(f"    Deleting orphan attachment: {name}")
        try:
            if not dry_run:
                client.delete_attachment(att_id)
        except urllib.error.HTTPError as e:
            # 404 means it was already removed manually; ignore.
            if e.code != 404:
                print(f"    Failed to delete {name}: {e}", file=sys.stderr)

    return new_attachments


if __name__ == "__main__":
    sys.exit(main())
