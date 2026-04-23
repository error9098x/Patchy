"""
Verbose per-scan log file.

When PATCHY_DEBUG=1, every stage of the pipeline can stream deep diagnostics
(full LLM inputs/outputs, raw Semgrep JSON, every edit with full old_string)
into logs/scan_<id>.log. Safe to tail -f.

Thread-local target so concurrent scans don't cross-write. Silent no-op when
debug is off or no file has been set for the current thread.
"""

import os
import json
import threading
import time
from typing import Any, Optional

_local = threading.local()


def enabled() -> bool:
    return os.environ.get("PATCHY_DEBUG", "0") == "1"


def set_file(path: str) -> None:
    """Start logging to path for current thread. No-op if debug off."""
    if not enabled():
        _local.path = None
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass
    _local.path = path
    try:
        with open(path, "w", encoding="utf-8") as f:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"=== patchy verbose log started {ts} ===\n\n")
    except Exception:
        _local.path = None


def clear() -> None:
    _local.path = None


def get_path() -> Optional[str]:
    return getattr(_local, "path", None)


def _append(text: str) -> None:
    path = get_path()
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
            if not text.endswith("\n"):
                f.write("\n")
    except Exception:
        pass


def section(title: str) -> None:
    ts = time.strftime("%H:%M:%S")
    bar = "=" * 70
    _append(f"\n{bar}\n[{ts}] {title}\n{bar}\n")


def log(label: str, data: Any = None) -> None:
    """Write a labeled entry. data can be dict/list (json) or any str-able."""
    if not get_path():
        return
    ts = time.strftime("%H:%M:%S")
    _append(f"\n--- [{ts}] {label} ---")
    if data is None:
        return
    if isinstance(data, (dict, list)):
        try:
            _append(json.dumps(data, indent=2, default=str, ensure_ascii=False))
            return
        except Exception:
            pass
    _append(str(data))
