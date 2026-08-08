"""memo_attach 저장소 — SQLite(메타/표/서식텍스트) + 파일(이미지)."""

from __future__ import annotations

import base64
import json
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH = Path("memo_data") / "attachments.db"
_FILES_DIR = Path("memo_data") / "files"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS blocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    memo_id     TEXT    NOT NULL,
    ord         INTEGER NOT NULL DEFAULT 0,
    kind        TEXT    NOT NULL,          -- table | image | html | text
    caption     TEXT    NOT NULL DEFAULT '',
    payload     TEXT,                      -- JSON (table/html/text)
    file_path   TEXT,                      -- 이미지 파일 경로
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_blocks_memo ON blocks(memo_id, ord, id);
"""

_MIME_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


# --------------------------------------------------------------------------- #
# 설정
# --------------------------------------------------------------------------- #
def configure(db_path: str | Path | None = None, files_dir: str | Path | None = None) -> None:
    """저장 위치를 바꾼다. 앱 시작 시 1회만 호출하면 된다."""
    global _DB_PATH, _FILES_DIR
    if db_path is not None:
        _DB_PATH = Path(db_path)
    if files_dir is not None:
        _FILES_DIR = Path(files_dir)
    _init()


def db_path() -> Path:
    return _DB_PATH


def files_dir() -> Path:
    return _FILES_DIR


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_initialized = False


def _init() -> None:
    global _initialized
    _FILES_DIR.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(_SCHEMA)
    _initialized = True


def _ensure() -> None:
    if not _initialized:
        _init()


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
def _next_ord(conn: sqlite3.Connection, memo_id: str) -> int:
    row = conn.execute("SELECT COALESCE(MAX(ord), -1) AS m FROM blocks WHERE memo_id = ?", (memo_id,)).fetchone()
    return int(row["m"]) + 1


def add_block(memo_id: str, value: Dict[str, Any]) -> Optional[int]:
    """붙여넣기 컴포넌트가 돌려준 값을 블록으로 저장하고 id를 반환."""
    _ensure()
    kind = value.get("kind")
    if kind not in ("table", "image", "html", "text"):
        return None

    payload: Optional[str] = None
    file_path: Optional[str] = None

    if kind == "image":
        data_url = value.get("data") or ""
        m = re.match(r"^data:([^;]+);base64,(.*)$", data_url, re.S)
        if not m:
            return None
        mime, b64 = m.group(1), m.group(2)
        ext = _MIME_EXT.get(mime.lower(), ".png")
        _FILES_DIR.mkdir(parents=True, exist_ok=True)
        name = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}{ext}"
        target = _FILES_DIR / name
        target.write_bytes(base64.b64decode(b64))
        file_path = str(target)
        payload = json.dumps(
            {"mime": mime, "w": value.get("w"), "h": value.get("h"), "bytes": value.get("bytes")},
            ensure_ascii=False,
        )
    elif kind == "table":
        payload = json.dumps(
            {
                "grid": value.get("grid") or [],
                "widths": value.get("widths") or [],
                "rows": value.get("rows"),
                "cols": value.get("cols"),
                "plain": value.get("plain") or "",
            },
            ensure_ascii=False,
        )
    elif kind == "html":
        payload = json.dumps({"html": value.get("html") or "", "plain": value.get("plain") or ""}, ensure_ascii=False)
    else:  # text
        payload = json.dumps({"text": value.get("text") or ""}, ensure_ascii=False)

    with _connect() as conn:
        ordv = _next_ord(conn, memo_id)
        cur = conn.execute(
            "INSERT INTO blocks (memo_id, ord, kind, caption, payload, file_path, created_at)"
            " VALUES (?, ?, ?, '', ?, ?, ?)",
            (memo_id, ordv, kind, payload, file_path, datetime.now().isoformat(timespec="seconds")),
        )
        return int(cur.lastrowid)


def _row_to_block(row: sqlite3.Row) -> Dict[str, Any]:
    try:
        payload = json.loads(row["payload"]) if row["payload"] else {}
    except Exception:
        payload = {}
    return {
        "id": int(row["id"]),
        "memo_id": row["memo_id"],
        "ord": int(row["ord"]),
        "kind": row["kind"],
        "caption": row["caption"] or "",
        "payload": payload,
        "file_path": row["file_path"],
        "created_at": row["created_at"],
    }


def list_blocks(memo_id: str) -> List[Dict[str, Any]]:
    _ensure()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM blocks WHERE memo_id = ? ORDER BY ord ASC, id ASC", (memo_id,)
        ).fetchall()
    return [_row_to_block(r) for r in rows]


def count_blocks(memo_id: str) -> int:
    _ensure()
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM blocks WHERE memo_id = ?", (memo_id,)).fetchone()
    return int(row["c"])


def counts_by_memo() -> Dict[str, int]:
    """{메모ID: 첨부 개수} — 사이드바 배지 등에 쓰기 좋다."""
    _ensure()
    with _connect() as conn:
        rows = conn.execute("SELECT memo_id, COUNT(*) AS c FROM blocks GROUP BY memo_id").fetchall()
    return {r["memo_id"]: int(r["c"]) for r in rows}


def update_payload(block_id: int, payload: Dict[str, Any]) -> None:
    """표 내용을 편집했을 때 저장."""
    _ensure()
    with _connect() as conn:
        conn.execute(
            "UPDATE blocks SET payload = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), block_id),
        )


def update_caption(block_id: int, caption: str) -> None:
    _ensure()
    with _connect() as conn:
        conn.execute("UPDATE blocks SET caption = ? WHERE id = ?", (caption, block_id))


def delete_block(block_id: int) -> None:
    _ensure()
    with _connect() as conn:
        row = conn.execute("SELECT file_path FROM blocks WHERE id = ?", (block_id,)).fetchone()
        if row and row["file_path"]:
            try:
                Path(row["file_path"]).unlink(missing_ok=True)
            except Exception:
                pass
        conn.execute("DELETE FROM blocks WHERE id = ?", (block_id,))


def move_block(memo_id: str, block_id: int, delta: int) -> None:
    """delta=-1 위로, +1 아래로."""
    _ensure()
    blocks = list_blocks(memo_id)
    ids = [b["id"] for b in blocks]
    if block_id not in ids:
        return
    i = ids.index(block_id)
    j = i + delta
    if j < 0 or j >= len(ids):
        return
    ids[i], ids[j] = ids[j], ids[i]
    with _connect() as conn:
        for new_ord, bid in enumerate(ids):
            conn.execute("UPDATE blocks SET ord = ? WHERE id = ?", (new_ord, bid))


def delete_memo(memo_id: str) -> None:
    """메모를 지울 때 함께 호출 — 첨부와 이미지 파일까지 정리한다."""
    _ensure()
    with _connect() as conn:
        rows = conn.execute("SELECT file_path FROM blocks WHERE memo_id = ?", (memo_id,)).fetchall()
        for r in rows:
            if r["file_path"]:
                try:
                    Path(r["file_path"]).unlink(missing_ok=True)
                except Exception:
                    pass
        conn.execute("DELETE FROM blocks WHERE memo_id = ?", (memo_id,))


def rename_memo(old_id: str, new_id: str) -> None:
    """메모 제목(= memo_id)을 바꿀 때 첨부도 따라가게 한다."""
    _ensure()
    with _connect() as conn:
        conn.execute("UPDATE blocks SET memo_id = ? WHERE memo_id = ?", (new_id, old_id))


def clear_memo(memo_id: str) -> None:
    delete_memo(memo_id)
