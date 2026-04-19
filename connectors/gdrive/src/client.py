"""Google Drive + Docs HTTP client — full read + write wrapper.

Decrypted OAuth token is injected at call time; never stored.

Read: list files, get metadata, EXPORT Doc/Sheet/Slide content as text.
Write: create new Google Doc, append/update content, upload file.

Scopes needed:
  drive.readonly  — read any file in the user's Drive
  drive.file      — create + edit files that Axis created

Docs: https://developers.google.com/drive/api/v3/reference
      https://developers.google.com/docs/api/reference/rest
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DOCS_API_BASE = "https://docs.googleapis.com/v1"


class GDriveClient:
    def __init__(self, *, access_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {access_token}",
        }
        self._token = access_token

    # ── Read: list + search ─────────────────────────────────────────────

    async def list_files(
        self, query: str = "", *, limit: int = 10
    ) -> list[dict[str, Any]]:
        q = _to_drive_query(query)
        params = {
            "q": q,
            "pageSize": limit,
            "fields": (
                "files(id,name,mimeType,webViewLink,iconLink,"
                "modifiedTime,owners,description),nextPageToken"
            ),
            "orderBy": "modifiedTime desc",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{DRIVE_API_BASE}/files",
                headers=self._headers,
                params=params,
            )
            resp.raise_for_status()
            body = resp.json()
        return body.get("files", [])

    async def list_all_files(
        self, query: str = "", *, max_files: int = 1000
    ) -> list[dict[str, Any]]:
        """Paginate through ALL files matching the query (up to max_files)."""
        q = _to_drive_query(query)
        all_files: list[dict[str, Any]] = []
        page_token: str | None = None
        while len(all_files) < max_files:
            params: dict[str, Any] = {
                "q": q,
                "pageSize": min(100, max_files - len(all_files)),
                "fields": (
                    "files(id,name,mimeType,webViewLink,modifiedTime,owners,description),"
                    "nextPageToken"
                ),
                "orderBy": "modifiedTime desc",
            }
            if page_token:
                params["pageToken"] = page_token
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{DRIVE_API_BASE}/files",
                    headers=self._headers,
                    params=params,
                )
                resp.raise_for_status()
                body = resp.json()
            files = body.get("files", [])
            all_files.extend(files)
            page_token = body.get("nextPageToken")
            if not page_token or not files:
                break
        return all_files[:max_files]

    async def list_recent(
        self,
        *,
        since: "datetime | None" = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return files modified in the time window, newest first.

        Uses Drive's `files.list` with a `modifiedTime` filter and ordering.
        Each result includes `id`, `name`, `mimeType`, `modifiedTime`,
        `webViewLink`, and `lastModifyingUser` (with `emailAddress`).

        Phase 2 will replace this with `changes.list` for true delta sync
        via Drive push notifications. For Phase 1 this is sufficient.
        """
        params: dict[str, Any] = {
            "pageSize": min(100, limit),
            "fields": (
                "files(id,name,mimeType,modifiedTime,webViewLink,"
                "lastModifyingUser(emailAddress,displayName))"
            ),
            "orderBy": "modifiedTime desc",
        }
        if since is not None:
            iso = since.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
            params["q"] = f"modifiedTime > '{iso}' and trashed = false"
        else:
            params["q"] = "trashed = false"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{DRIVE_API_BASE}/files",
                headers=self._headers,
                params=params,
            )
            resp.raise_for_status()
            return resp.json().get("files", [])

    async def get_file(self, file_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{DRIVE_API_BASE}/files/{file_id}",
                headers=self._headers,
                params={
                    "fields": "id,name,mimeType,webViewLink,modifiedTime,owners,description",
                },
            )
            resp.raise_for_status()
            return resp.json()

    # ── Read: export content as plain text ──────────────────────────────

    async def export_as_text(self, file_id: str, mime_type: str = "text/plain") -> str:
        """Export a Google Doc/Sheet/Slide as plain text.

        Only works for Google Workspace files (application/vnd.google-apps.*).
        For uploaded PDFs/images, use download_file instead.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{DRIVE_API_BASE}/files/{file_id}/export",
                headers=self._headers,
                params={"mimeType": mime_type},
            )
            if resp.status_code == 200:
                return resp.text
            resp.raise_for_status()
            return ""

    async def read_doc_content(self, file_id: str) -> str:
        """Read a Google Doc's full text content. Convenience wrapper."""
        return await self.export_as_text(file_id, "text/plain")

    async def read_sheet_content(self, file_id: str) -> str:
        """Read a Google Sheet as CSV."""
        return await self.export_as_text(file_id, "text/csv")

    # ── Write: create + update ──────────────────────────────────────────

    async def create_doc(
        self,
        *,
        title: str,
        content: str = "",
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Google Doc with optional initial text content.

        Uses the Docs API to create the doc, then inserts text if provided.
        Returns {id, url, title}.
        """
        # Step 1: Create the doc via Docs API
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{DOCS_API_BASE}/documents",
                headers={**self._headers, "Content-Type": "application/json"},
                json={"title": title},
            )
            resp.raise_for_status()
            doc = resp.json()

        doc_id = doc["documentId"]
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

        # Step 2: If there's initial content, insert it
        if content.strip():
            await self.append_to_doc(doc_id=doc_id, text=content)

        # Step 3: Move to folder if specified
        if folder_id:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.patch(
                        f"{DRIVE_API_BASE}/files/{doc_id}",
                        headers=self._headers,
                        params={"addParents": folder_id},
                    )
            except Exception:  # noqa: BLE001
                pass  # folder move is best-effort

        return {"id": doc_id, "url": doc_url, "title": title}

    async def append_to_doc(self, *, doc_id: str, text: str) -> dict[str, Any]:
        """Append text at the end of a Google Doc via the Docs API batchUpdate."""
        requests = [
            {
                "insertText": {
                    "location": {"index": 1},  # index 1 = start of body
                    "text": text,
                }
            }
        ]
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{DOCS_API_BASE}/documents/{doc_id}:batchUpdate",
                headers={**self._headers, "Content-Type": "application/json"},
                json={"requests": requests},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_sheet(self, *, title: str) -> dict[str, Any]:
        """Create a new Google Sheet. Returns {id, url, title}."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://sheets.googleapis.com/v4/spreadsheets",
                headers={**self._headers, "Content-Type": "application/json"},
                json={"properties": {"title": title}},
            )
            resp.raise_for_status()
            sheet = resp.json()
        return {
            "id": sheet["spreadsheetId"],
            "url": sheet["spreadsheetUrl"],
            "title": title,
        }


def _to_drive_query(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return "trashed = false"
    if "=" in q or " contains " in q or " and " in q:
        return q
    escaped = q.replace("'", "\\'")
    return f"fullText contains '{escaped}' and trashed = false"
