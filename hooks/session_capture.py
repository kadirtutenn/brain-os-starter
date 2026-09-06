#!/usr/bin/env python3
"""Capture Claude-style session lifecycle events into a Brain daily log.

This hook deliberately does not call a model.  It stores a bounded, redacted
transcript excerpt so a later agent or an explicit consolidation job can do
semantic promotion through the normal Brain write gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_TRANSCRIPT_CHARS = 12000
LOCK_WAIT_SECONDS = 2.0
_SECRET = re.compile(
    r"(?i)(?:bearer\s+|password\s*[:=]\s*|token\s*[:=]\s*|"
    r"api[_-]?key\s*[:=]\s*|sk-[A-Za-z0-9_-]{12,})[^\s,;]+"
)


def _redact(value: str) -> str:
    return _SECRET.sub("[REDACTED]", value)


def _text_values(value: Any) -> list[str]:
    """Extract human-readable text from common JSONL transcript shapes."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_text_values(item))
        return result
    if isinstance(value, dict):
        if value.get("type") in {"tool_result", "tool_use", "image"}:
            return []
        result: list[str] = []
        for key in ("text", "content"):
            if key in value:
                result.extend(_text_values(value[key]))
        return result
    return []


def _transcript_excerpt(path: str) -> str:
    if not path or not os.path.isfile(path):
        return ""
    messages: list[str] = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except (TypeError, ValueError):
                    continue
                role = str(item.get("role") or item.get("message", {}).get("role") or "").lower()
                payload = item.get("message", item)
                texts = [text.strip() for text in _text_values(payload) if text.strip()]
                if texts and role in {"user", "assistant"}:
                    messages.append(f"{role}: {_redact(' '.join(texts))}")
    except OSError:
        return ""
    return "\n\n".join(messages)[-MAX_TRANSCRIPT_CHARS:]


def _acquire_lock(lock: Path) -> bool:
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            lock.mkdir()
            return True
        except FileExistsError:
            time.sleep(0.03)
    return False


def capture(event: dict[str, Any], store: str, now: datetime | None = None) -> Path | None:
    """Append one idempotent lifecycle event to ``daily/YYYY-MM-DD.md``."""
    if not store:
        return None
    current = now or datetime.now(timezone.utc)
    daily = Path(store) / "daily"
    daily.mkdir(parents=True, exist_ok=True)
    target = daily / f"{current.date().isoformat()}.md"
    session_id = str(event.get("session_id") or "unknown")
    event_name = str(event.get("hook_event_name") or event.get("event") or "SessionEnd")
    transcript = str(event.get("transcript_path") or "")
    marker = hashlib.sha256(
        f"{event_name}|{session_id}|{transcript}".encode("utf-8")
    ).hexdigest()[:16]
    excerpt = _transcript_excerpt(transcript)
    lines = [
        f"## {event_name} — {current.isoformat()}",
        f"- session_id: `{_redact(session_id)}`",
        f"- event_id: `{marker}`",
        f"- reason: {_redact(str(event.get('reason') or event.get('trigger') or 'unspecified'))}",
        "",
    ]
    if excerpt:
        lines.extend(["### Transcript excerpt", "", excerpt, ""])
    else:
        lines.extend(["Transcript content was unavailable; lifecycle event recorded.", ""])
    entry = "\n".join(lines)
    lock = target.with_name(target.name + ".lock")
    if not _acquire_lock(lock):
        return None
    try:
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        if not existing:
            existing = (
                "---\n"
                "type: Session\n"
                f"description: Automatic lifecycle log for {current.date().isoformat()}\n"
                f"timestamp: {current.date().isoformat()}\n"
                "---\n\n"
                f"# Daily log — {current.date().isoformat()}\n\n"
            )
            target.write_text(existing, encoding="utf-8")
        if f"event_id: `{marker}`" not in existing:
            with target.open("a", encoding="utf-8") as handle:
                if existing and not existing.endswith("\n"):
                    handle.write("\n")
                handle.write(entry)
    finally:
        try:
            lock.rmdir()
        except OSError:
            pass
    return target


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        event = {}
    if not isinstance(event, dict):
        event = {}
    capture(event, os.environ.get("BRAIN_STORE_PATH") or os.environ.get("BRAIN_VAULT_PATH", ""))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Lifecycle hooks must never break the agent session.
        pass
