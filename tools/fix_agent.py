"""Agentic fix loop.

Model directs context gathering via JSON actions, then emits a patch.
Every failure mode is explicit, named, and logged — no silent drops.
"""

import os
import json
import re
import time
import subprocess
from typing import Callable, Dict, List, Optional

from tools.nvidia_client import chat, _extract_json

try:
    import verbose_log
except Exception:
    verbose_log = None


def _vlog(label, data=None):
    if verbose_log is not None:
        verbose_log.log(label, data)

DEBUG = os.environ.get("PATCHY_DEBUG", "0") == "1"

MAX_TURNS = 4
MAX_FILES_PER_READ = 5
MAX_PATCH_CHARS = 100000
MAX_TOKENS_PER_TURN = 8192
MAX_FILE_BYTES = 64_000
MAX_INDEX_FILES = 400
TEMPERATURE = 0.3
GREP_MAX_MATCHES = 40
GREP_TIMEOUT = 10

SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".tar",
    ".gz", ".lock", ".min.js", ".map", ".woff", ".woff2", ".ttf", ".mp4",
    ".mp3", ".svg",
}
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__"}

OUTCOME_OK = "ok"
OUTCOME_BAD_JSON = "bad_json"
OUTCOME_UNKNOWN_ACTION = "unknown_action"
OUTCOME_TURN_LIMIT = "turn_limit"
OUTCOME_GAVE_UP = "llm_gave_up"
OUTCOME_API_ERROR = "api_error"
OUTCOME_EMPTY_PATCH = "empty_patch"
OUTCOME_PATCH_TOO_LARGE = "patch_too_large"
OUTCOME_LOW_CONFIDENCE = "low_confidence"
OUTCOME_BAD_REGEX = "bad_regex"
OUTCOME_BAD_EDIT = "bad_edit"

VALID_ACTIONS = {"read_files", "grep", "fix", "give_up"}

SYSTEM_PROMPT = f"""You are Patchy, a security-fix agent.

=== JSON OUTPUT RULES ===
Respond with EXACTLY ONE JSON object per turn. No prose, no markdown fences.
The "action" field MUST be one of: "read_files", "grep", "fix", "give_up"

=== ACTIONS ===

1) read_files — request file contents
{{"action":"read_files","files":["path1","path2"],"reason":"why"}}
   Max {MAX_FILES_PER_READ} files per call. Files must exist in the repo file list.

2) grep — search the repo with a regex
{{"action":"grep","pattern":"regex","reason":"why"}}
   Max {GREP_MAX_MATCHES} matches returned.

3) fix — emit the final patch (two shapes, prefer 3a)

3a) SURGICAL EDITS (preferred):
{{"action":"fix","file":"relative/path.py",
 "edits":[
   {{"old_string":"<exact text to find>","new_string":"<replacement>"}},
   {{"old_string":"...","new_string":"..."}}
 ],
 "explanation":"short note",
 "confidence":0.0-1.0}}
   - Each old_string MUST appear EXACTLY ONCE in the file.
     If not unique, include surrounding lines for disambiguation.
   - Copy old_string VERBATIM — exact whitespace, indent, quotes, newlines.

3b) FULL REWRITE (only when file <30 lines or >40% changed):
{{"action":"fix","file":"relative/path.py",
 "patched_content":"<entire new file>",
 "explanation":"short note",
 "confidence":0.0-1.0}}

4) give_up — false positive or unfixable
{{"action":"give_up","reason":"why"}}

Budget: {MAX_TURNS} turns max. Prefer fixing by turn 2.

=== EXAMPLES ===

{{"action":"read_files","files":["app.py"],"reason":"See debug flag at line 318"}}

{{"action":"fix","file":"app.py","edits":[{{"old_string":"    app.run(debug=True)","new_string":"    app.run(debug=False)"}}],"explanation":"Disabled debug mode.","confidence":0.95}}

{{"action":"fix","file":"templates/admin.html","edits":[{{"old_string":"<form action=/edit method=POST>","new_string":"<form action=/edit method=POST>\\n    {{% csrf_token %}}"}}],"explanation":"Added csrf_token to POST form.","confidence":0.95}}

{{"action":"give_up","reason":"Test file, not production code"}}
"""


def _log(msg):
    if DEBUG:
        print(msg)


def build_file_index(repo_path: str) -> List[str]:
    """Return list of relative file paths worth showing to the LLM."""
    out = []
    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in SKIP_EXTS:
                continue
            abs_p = os.path.join(dirpath, fname)
            try:
                if os.path.getsize(abs_p) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            rel = os.path.relpath(abs_p, repo_path)
            out.append(rel)
            if len(out) >= MAX_INDEX_FILES:
                return out
    return out


def _run_ripgrep(repo_path: str, pattern: str) -> List[str]:
    """Run ripgrep (fallback: grep -rE) and return 'path:line:content' strings."""
    excludes = [f"--glob=!{d}" for d in SKIP_DIRS]
    try:
        proc = subprocess.run(
            ["rg", "--no-heading", "--line-number", "--max-count", "20",
             "-e", pattern, *excludes, repo_path],
            capture_output=True, text=True, timeout=GREP_TIMEOUT
        )
        lines = (proc.stdout or "").splitlines()
    except FileNotFoundError:
        try:
            proc = subprocess.run(
                ["grep", "-rnE", pattern, repo_path],
                capture_output=True, text=True, timeout=GREP_TIMEOUT
            )
            lines = (proc.stdout or "").splitlines()
        except Exception:
            return []
    except Exception:
        return []

    out = []
    for ln in lines:
        stripped = ln.replace(repo_path + "/", "", 1).replace(repo_path, "", 1)
        out.append(stripped[:400])
    return out


def _read_file_safe(repo_path: str, rel: str) -> Optional[str]:
    abs_p = os.path.join(repo_path, rel)
    if not os.path.isfile(abs_p):
        return None
    try:
        # newline="" preserves original line endings (\r\n vs \n) so that
        # apply_edits produces content with identical endings, avoiding
        # full-file diffs on GitHub when only a few lines actually changed.
        with open(abs_p, "r", encoding="utf-8", errors="replace", newline="") as f:
            data = f.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            return data[:MAX_FILE_BYTES] + "\n...[truncated]"
        return data
    except Exception:
        return None


def apply_edits(original: str, edits: List[Dict]) -> Dict:
    """Apply surgical edits to original content.

    Returns dict: {ok: bool, content: str|None, applied: int, failed: list}
    failed items: {"index": i, "reason": "not_found"|"ambiguous"|"empty_old",
                   "old_preview": first 80 chars}
    Edits applied sequentially; each sees prior result.
    """
    content = original
    applied = 0
    failed = []

    # Detect the file's line ending style for fallback matching.
    # LLM always emits \n in JSON strings, but file may have \r\n.
    file_uses_crlf = "\r\n" in content

    for i, edit in enumerate(edits):
        if not isinstance(edit, dict):
            failed.append({"index": i, "reason": "not_dict", "old_preview": ""})
            continue
        old = edit.get("old_string", "")
        new = edit.get("new_string", "")
        preview = (old[:80] + "...") if len(old) > 80 else old
        if not old:
            failed.append({"index": i, "reason": "empty_old",
                           "old_preview": preview})
            continue

        count = content.count(old)

        # Fallback: if LLM used \n but file has \r\n (or vice versa),
        # adapt the edit strings to match the file's actual line endings.
        if count == 0 and file_uses_crlf and "\r\n" not in old:
            old_adapted = old.replace("\n", "\r\n")
            new_adapted = new.replace("\n", "\r\n")
            count = content.count(old_adapted)
            if count >= 1:
                old, new = old_adapted, new_adapted
        elif count == 0 and not file_uses_crlf and "\r\n" in old:
            old_adapted = old.replace("\r\n", "\n")
            new_adapted = new.replace("\r\n", "\n")
            count = content.count(old_adapted)
            if count >= 1:
                old, new = old_adapted, new_adapted

        if count == 0:
            failed.append({"index": i, "reason": "not_found",
                           "old_preview": preview})
            continue
        if count > 1:
            failed.append({"index": i, "reason": "ambiguous",
                           "old_preview": preview, "matches": count})
            continue
        content = content.replace(old, new, 1)
        applied += 1
    return {
        "ok": len(failed) == 0 and applied > 0,
        "content": content if len(failed) == 0 else None,
        "applied": applied,
        "failed": failed,
    }


def _parse_turn(raw: str):
    try:
        return json.loads(_extract_json(raw)), None
    except Exception as e:
        return None, str(e)


def _format_initial_prompt(finding: Dict, file_index: List[str]) -> str:
    files_listing = "\n".join(f"- {p}" for p in file_index)
    return f"""Security finding to fix:
{json.dumps({
    "check_id": finding.get("check_id"),
    "path": finding.get("path"),
    "line": finding.get("start", {}).get("line"),
    "severity": finding.get("extra", {}).get("severity"),
    "message": finding.get("extra", {}).get("message"),
}, indent=2)}

Repository files ({len(file_index)}):
{files_listing}

Respond now with your next action as a single JSON object."""


def _format_initial_prompt_group(findings: List[Dict],
                                 file_index: List[str],
                                 target_file: str) -> str:
    files_listing = "\n".join(f"- {p}" for p in file_index)
    compact = [{
        "check_id": f.get("check_id"),
        "line": f.get("start", {}).get("line"),
        "severity": f.get("extra", {}).get("severity"),
        "message": (f.get("extra", {}).get("message") or "").strip()[:400],
    } for f in findings]
    return f"""You must fix MULTIPLE security findings, ALL in the same file:

Target file: {target_file}
Findings ({len(findings)}):
{json.dumps(compact, indent=2)}

Rules for this group:
- One `fix` action that addresses ALL findings above in {target_file}.
- Prefer surgical `edits` - one edit per distinct location.
- Do NOT emit separate fix actions per finding.
- If some findings are duplicates (same rule, many sites), collapse into one set of edits covering every site.

Repository files ({len(file_index)}):
{files_listing}

Respond now with your next action as a single JSON object."""


class FixResult:
    def __init__(self, outcome, file=None, patched_content=None,
                 explanation=None, confidence=0.0, trace=None, turns=0,
                 detail=None):
        self.outcome = outcome
        self.ok = outcome == OUTCOME_OK
        self.file = file
        self.patched_content = patched_content
        self.explanation = explanation
        self.confidence = confidence
        self.trace = trace or []
        self.turns = turns
        self.detail = detail

    def to_dict(self):
        return {
            "outcome": self.outcome, "ok": self.ok, "file": self.file,
            "confidence": self.confidence, "turns": self.turns,
            "explanation": self.explanation, "trace": self.trace,
            "detail": self.detail,
        }


def run_fix_agent_for_file(findings: List[Dict], repo_path: str,
                           file_index: List[str],
                           scan_id: str = "-",
                           event_cb: Optional[Callable[[Dict], None]] = None
                           ) -> FixResult:
    """Grouped mode: fix ALL findings on a single file in one agent run."""
    if not findings:
        return FixResult(OUTCOME_EMPTY_PATCH, detail="empty finding group")
    target_file = findings[0].get("path", "?")
    return run_fix_agent(
        findings[0], repo_path, file_index,
        scan_id=scan_id, event_cb=event_cb, group=findings,
        target_file=target_file,
    )


def run_fix_agent(finding: Dict, repo_path: str,
                  file_index: List[str],
                  scan_id: str = "-",
                  event_cb: Optional[Callable[[Dict], None]] = None,
                  group: Optional[List[Dict]] = None,
                  target_file: Optional[str] = None) -> FixResult:
    """Run the agentic fix loop for a single finding or a group on one file.

    If `group` is provided, all findings in group are addressed in one LLM
    conversation. `finding` is used for metadata (scan log header, events).

    event_cb: optional callback for live UI; receives dicts like
      {"type":"finding_start", ...}, {"type":"turn", ...}, {"type":"finding_end", ...}
    """
    check_id = finding.get("check_id", "unknown")
    finding_path = target_file or finding.get("path", "?")
    line = finding.get("start", {}).get("line", "?")
    is_group = bool(group) and len(group) > 1

    def _emit(ev):
        if event_cb is None:
            return
        try:
            event_cb(ev)
        except Exception as e:
            _log(f"[SCAN {scan_id}]    ⚠ event_cb error: {e}")

    if is_group:
        _log(f"[SCAN {scan_id}] ┌─ FixAgent: {len(group)} findings in {finding_path}")
        _vlog("fix_agent.start_group", {
            "file": finding_path,
            "count": len(group),
            "findings": [{
                "check_id": f.get("check_id"),
                "line": f.get("start", {}).get("line"),
                "severity": f.get("extra", {}).get("severity"),
                "message": f.get("extra", {}).get("message", "")[:200],
            } for f in group],
        })
        _emit({
            "type": "finding_start", "check_id": check_id,
            "file": finding_path, "line": line,
            "severity": (finding.get("extra", {}).get("severity", "") or "").lower(),
            "message": f"{len(group)} findings grouped in {finding_path}",
            "group_size": len(group),
        })
        initial_user = _format_initial_prompt_group(
            group, file_index, finding_path)
    else:
        _log(f"[SCAN {scan_id}] ┌─ FixAgent: {check_id} at {finding_path}:{line}")
        _vlog("fix_agent.start", {
            "check_id": check_id,
            "file": finding_path, "line": line,
            "severity": finding.get("extra", {}).get("severity"),
            "message": finding.get("extra", {}).get("message", "")[:400],
        })
        _emit({
            "type": "finding_start", "check_id": check_id,
            "file": finding_path, "line": line,
            "severity": (finding.get("extra", {}).get("severity", "") or "").lower(),
            "message": finding.get("extra", {}).get("message", ""),
        })
        initial_user = _format_initial_prompt(finding, file_index)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": initial_user},
    ]
    trace = []
    t0 = time.time()

    for turn in range(MAX_TURNS):
        try:
            raw = chat(messages, temperature=TEMPERATURE)
        except Exception as e:
            _log(f"[SCAN {scan_id}] │  turn {turn} ✗ api_error: {e}")
            trace.append({"turn": turn, "ok": False, "error": f"api: {e}"})
            _emit({"type": "turn", "turn": turn, "action": "api_error",
                   "ok": False, "detail": str(e)[:200]})
            _log(f"[SCAN {scan_id}] └─ ✗ FAIL api_error after {turn} turns")
            _emit({"type": "finding_end", "outcome": OUTCOME_API_ERROR,
                   "turns": turn, "ok": False})
            return FixResult(OUTCOME_API_ERROR, trace=trace, turns=turn,
                             detail=str(e))

        obj, err = _parse_turn(raw)
        if err:
            preview = raw[:200].replace("\n", " ")
            _log(f"[SCAN {scan_id}] │  turn {turn} ✗ bad_json: {err}")
            _log(f"[SCAN {scan_id}] │    raw: {preview}")
            trace.append({"turn": turn, "ok": False, "error": f"bad_json: {err}",
                          "raw_preview": preview})
            _emit({"type": "turn", "turn": turn, "action": "bad_json",
                   "ok": False, "detail": preview})
            _log(f"[SCAN {scan_id}] └─ ✗ FAIL bad_json")
            _emit({"type": "finding_end", "outcome": OUTCOME_BAD_JSON,
                   "turns": turn, "ok": False})
            return FixResult(OUTCOME_BAD_JSON, trace=trace, turns=turn,
                             detail=preview)

        if not isinstance(obj, dict):
            _log(f"[SCAN {scan_id}] │  turn {turn} ✗ not_object: got {type(obj).__name__}")
            trace.append({"turn": turn, "ok": False, "error": "not_object"})
            return FixResult(OUTCOME_BAD_JSON, trace=trace, turns=turn,
                             detail="response was not a JSON object")

        action = obj.get("action")
        
        # Defensive: handle action being array (model mistake)
        if isinstance(action, list):
            if len(action) == 1:
                _log(f"[SCAN {scan_id}] │  turn {turn} ⚠ action was array, normalized: {action} → {action[0]}")
                action = action[0]
            elif len(action) == 0:
                _log(f"[SCAN {scan_id}] │  turn {turn} ✗ action is empty array")
                trace.append({"turn": turn, "ok": False, "error": "action_empty_array"})
                return FixResult(OUTCOME_BAD_JSON, trace=trace, turns=turn,
                                 detail="action field is empty array")
            else:
                _log(f"[SCAN {scan_id}] │  turn {turn} ✗ action is multi-element array: {action}")
                trace.append({"turn": turn, "ok": False, "error": "action_multi_array", "value": action})
                return FixResult(OUTCOME_BAD_JSON, trace=trace, turns=turn,
                                 detail=f"action field is array with {len(action)} elements")
        
        # Defensive: normalize action string (model quirk — Nemotron
        # sometimes outputs ": grep" instead of "grep" due to prompt
        # structure leaking colons into the value)
        if isinstance(action, str):
            cleaned = action.strip().lstrip(":").strip()
            if cleaned != action:
                _log(f"[SCAN {scan_id}] │  turn {turn} ⚠ action normalized: {action!r} → {cleaned!r}")
                action = cleaned
            # After stripping, action might be empty (e.g. model sent
            # {"action":":"} — common brain-melt when context has \r\n).
            if not action:
                _log(f"[SCAN {scan_id}] │  turn {turn} ✗ action empty after normalization")
                trace.append({"turn": turn, "ok": False, "error": "empty_action"})
                _emit({"type": "turn", "turn": turn, "action": "empty",
                       "ok": False})
                if turn < MAX_TURNS - 1:
                    valid_list = ", ".join(sorted(VALID_ACTIONS))
                    messages.append({"role": "user", "content":
                        f"Your action was empty. "
                        f"action MUST be one of: {valid_list}. "
                        f"Respond with a complete JSON object. Next action?"})
                    continue
                return FixResult(OUTCOME_BAD_JSON, trace=trace, turns=turn + 1,
                                 detail="action empty after normalization")
        
        messages.append({"role": "assistant", "content": json.dumps(obj)})

        if action == "read_files":
            requested = obj.get("files", []) or []
            if not isinstance(requested, list):
                requested = []
            requested = requested[:MAX_FILES_PER_READ]
            valid = [f for f in requested if f in file_index]
            halluc = [f for f in requested if f not in file_index]
            mark = "✓" if not halluc else "⚠"
            _log(f"[SCAN {scan_id}] │  turn {turn} → read_files {valid} {mark}")
            if halluc:
                _log(f"[SCAN {scan_id}] │    halluc dropped: {halluc}")
            trace.append({"turn": turn, "action": "read_files",
                          "files": valid, "halluc": halluc, "ok": True})
            _emit({"type": "turn", "turn": turn, "action": "read_files",
                   "files": valid, "halluc": halluc, "ok": True,
                   "reason": obj.get("reason", "")})

            if not valid:
                messages.append({"role": "user", "content":
                    f"None of those paths exist. Hallucinated: {halluc}. "
                    f"Pick from the repo file list only. Next action?"})
                continue

            blob_parts = []
            for rel in valid:
                content = _read_file_safe(repo_path, rel)
                if content is None:
                    blob_parts.append(f"=== {rel} ===\n[unreadable]")
                else:
                    # Strip \r before sending to LLM.  Raw \r\n in context
                    # confuses Nemotron into outputting garbage JSON
                    # (e.g. {"action":":"}).  apply_edits re-reads the file
                    # with preserved CRLF independently, so LLM needs \n only.
                    display = content.replace('\r', '')
                    blob_parts.append(f"=== {rel} ===\n{display}")
            blob = "\n\n".join(blob_parts)
            note = f" Ignored hallucinated: {halluc}." if halluc else ""
            messages.append({"role": "user", "content":
                f"File contents:\n\n{blob}\n\n{note}\nNext action?"})
            continue

        if action == "grep":
            pattern = (obj.get("pattern") or "").strip()
            if not pattern:
                _log(f"[SCAN {scan_id}] │  turn {turn} ✗ grep empty pattern")
                trace.append({"turn": turn, "action": "grep", "ok": False,
                              "error": "empty pattern"})
                messages.append({"role": "user", "content":
                    "Empty grep pattern. Provide a non-empty regex. Next action?"})
                continue
            try:
                re.compile(pattern)
            except re.error as e:
                _log(f"[SCAN {scan_id}] │  turn {turn} ✗ bad_regex: {e}")
                trace.append({"turn": turn, "action": "grep", "ok": False,
                              "error": f"bad_regex: {e}", "pattern": pattern})
                messages.append({"role": "user", "content":
                    f"Invalid regex ({e}). Fix pattern. Next action?"})
                continue

            matches = _run_ripgrep(repo_path, pattern)
            mark = "✓" if matches else "⚠"
            _log(f"[SCAN {scan_id}] │  turn {turn} → grep /{pattern}/ "
                 f"→ {len(matches)} hits {mark}")
            trace.append({"turn": turn, "action": "grep", "pattern": pattern,
                          "hits": len(matches), "ok": True})
            _emit({"type": "turn", "turn": turn, "action": "grep",
                   "pattern": pattern, "hits": len(matches), "ok": True,
                   "reason": obj.get("reason", "")})

            if not matches:
                messages.append({"role": "user", "content":
                    f"Pattern /{pattern}/ had no matches. Next action?"})
                continue

            shown = matches[:GREP_MAX_MATCHES]
            blob = "\n".join(shown)
            truncated = "" if len(matches) <= GREP_MAX_MATCHES else \
                f"\n[truncated; {len(matches) - GREP_MAX_MATCHES} more hits omitted]"
            messages.append({"role": "user", "content":
                f"grep /{pattern}/ matches ({len(shown)} shown):\n"
                f"{blob}{truncated}\n\nNext action?"})
            continue

        if action == "give_up":
            reason = obj.get("reason", "")
            _log(f"[SCAN {scan_id}] │  turn {turn} → give_up: {reason}")
            trace.append({"turn": turn, "action": "give_up",
                          "reason": reason, "ok": True})
            _emit({"type": "turn", "turn": turn, "action": "give_up",
                   "ok": True, "reason": reason})
            _log(f"[SCAN {scan_id}] └─ ✗ FAIL llm_gave_up: {reason}")
            _emit({"type": "finding_end", "outcome": OUTCOME_GAVE_UP,
                   "turns": turn + 1, "ok": False, "detail": reason})
            return FixResult(OUTCOME_GAVE_UP, trace=trace, turns=turn + 1,
                             detail=reason)

        if action == "fix":
            file = obj.get("file")
            patched = obj.get("patched_content", "") or ""
            edits = obj.get("edits") or []
            confidence = float(obj.get("confidence", 0) or 0)
            explanation = obj.get("explanation", "")
            edit_mode = None
            edit_applied = 0
            edit_failed = []

            if edits and isinstance(edits, list):
                edit_mode = "edits"
                if not file:
                    _log(f"[SCAN {scan_id}] │  turn {turn} ✗ empty_patch (edits, no file)")
                    trace.append({"turn": turn, "action": "fix",
                                  "ok": False, "error": "no_file"})
                    return FixResult(OUTCOME_EMPTY_PATCH, trace=trace,
                                     turns=turn + 1)
                original = _read_file_safe(repo_path, file)
                if original is None:
                    _log(f"[SCAN {scan_id}] │  turn {turn} ✗ bad_edit: target file unreadable: {file}")
                    trace.append({"turn": turn, "action": "fix", "ok": False,
                                  "error": "target_unreadable", "file": file})
                    _emit({"type": "turn", "turn": turn, "action": "fix",
                           "ok": False, "detail": f"cannot read {file}"})
                    return FixResult(OUTCOME_BAD_EDIT, trace=trace,
                                     turns=turn + 1,
                                     detail=f"cannot read target file {file}")
                res = apply_edits(original, edits)
                edit_applied = res["applied"]
                edit_failed = res["failed"]
                _vlog("fix_agent.apply_edits", {
                    "file": file,
                    "turn": turn,
                    "applied": edit_applied,
                    "failed_count": len(edit_failed),
                    "edits": edits,
                    "failures": edit_failed,
                })
                if not res["ok"]:
                    _log(f"[SCAN {scan_id}] │  turn {turn} ✗ bad_edit "
                         f"(applied={edit_applied}, failed={len(edit_failed)})")
                    for fe in edit_failed:
                        _log(f"[SCAN {scan_id}] │    ✗ edit#{fe['index']} "
                             f"{fe['reason']}: {fe.get('old_preview', '')!r}")
                    trace.append({"turn": turn, "action": "fix", "ok": False,
                                  "error": "bad_edit", "file": file,
                                  "applied": edit_applied,
                                  "failed": edit_failed})
                    _emit({"type": "turn", "turn": turn, "action": "fix",
                           "file": file, "ok": False,
                           "mode": "edits",
                           "applied": edit_applied,
                           "failed": len(edit_failed),
                           "detail": f"{len(edit_failed)} edit(s) did not apply"})
                    if turn < MAX_TURNS - 1:
                        hint_lines = []
                        for fe in edit_failed[:3]:
                            hint_lines.append(
                                f"  edit#{fe['index']} {fe['reason']}: "
                                f"{fe.get('old_preview','')!r}"
                            )
                        hint = "\n".join(hint_lines)
                        messages.append({"role": "user", "content":
                            f"apply_edits failed on {file}: "
                            f"{edit_applied} applied, {len(edit_failed)} failed.\n"
                            f"{hint}\n"
                            f"For 'not_found': re-read the file and copy the "
                            f"exact bytes. For 'ambiguous': include more "
                            f"surrounding context to make old_string unique. "
                            f"Retry with corrected edits. Next action?"})
                        continue
                    return FixResult(OUTCOME_BAD_EDIT, trace=trace,
                                     turns=turn + 1,
                                     detail=f"{len(edit_failed)} failed edits")
                patched = res["content"]
                _log(f"[SCAN {scan_id}] │  turn {turn} → fix {file} "
                     f"via {edit_applied} edit(s) ✓")

            if not file or not patched:
                _log(f"[SCAN {scan_id}] │  turn {turn} ✗ empty_patch")
                trace.append({"turn": turn, "action": "fix",
                              "ok": False, "error": "empty"})
                _log(f"[SCAN {scan_id}] └─ ✗ FAIL empty_patch")
                return FixResult(OUTCOME_EMPTY_PATCH, trace=trace,
                                 turns=turn + 1)

            if len(patched) > MAX_PATCH_CHARS:
                _log(f"[SCAN {scan_id}] │  turn {turn} ✗ patch_too_large "
                     f"({len(patched)} chars)")
                trace.append({"turn": turn, "action": "fix", "ok": False,
                              "error": "too_large", "size": len(patched)})
                _log(f"[SCAN {scan_id}] └─ ✗ FAIL patch_too_large")
                return FixResult(OUTCOME_PATCH_TOO_LARGE, trace=trace,
                                 turns=turn + 1)

            mode = edit_mode or "patched_content"
            _log(f"[SCAN {scan_id}] │  turn {turn} → fix {file} "
                 f"mode={mode} conf={confidence} ({len(patched)} chars) ✓")
            trace.append({"turn": turn, "action": "fix", "file": file,
                          "confidence": confidence,
                          "mode": mode,
                          "edits_applied": edit_applied,
                          "patch_chars": len(patched), "ok": True})
            _emit({"type": "turn", "turn": turn, "action": "fix",
                   "file": file, "confidence": confidence,
                   "mode": mode,
                   "edits_applied": edit_applied,
                   "patch_chars": len(patched), "ok": True,
                   "explanation": explanation or ""})

            if confidence < 0.3:
                _log(f"[SCAN {scan_id}] └─ ✗ FAIL low_confidence ({confidence})")
                _emit({"type": "finding_end", "outcome": OUTCOME_LOW_CONFIDENCE,
                       "turns": turn + 1, "ok": False,
                       "confidence": confidence})
                return FixResult(OUTCOME_LOW_CONFIDENCE, file=file,
                                 patched_content=patched,
                                 explanation=explanation,
                                 confidence=confidence, trace=trace,
                                 turns=turn + 1)

            dt = round(time.time() - t0, 1)
            _log(f"[SCAN {scan_id}] └─ ✓ OK ({turn + 1} turns, {dt}s, "
                 f"conf={confidence})")
            _emit({"type": "finding_end", "outcome": OUTCOME_OK,
                   "turns": turn + 1, "ok": True,
                   "confidence": confidence, "file": file,
                   "duration_s": dt})
            return FixResult(OUTCOME_OK, file=file, patched_content=patched,
                             explanation=explanation, confidence=confidence,
                             trace=trace, turns=turn + 1)

        _log(f"[SCAN {scan_id}] │  turn {turn} ✗ unknown_action: {action!r}")
        trace.append({"turn": turn, "ok": False,
                      "error": f"unknown_action: {action!r}"})
        _emit({"type": "turn", "turn": turn, "action": "unknown",
               "ok": False, "detail": str(action)[:100]})
        # Give model one chance to recover instead of instant-fail
        if turn < MAX_TURNS - 1:
            valid_list = ", ".join(sorted(VALID_ACTIONS))
            messages.append({"role": "user", "content":
                f"Invalid action: {action!r}. "
                f"action MUST be exactly one of: {valid_list}. "
                f"Respond with valid JSON. Next action?"})
            continue
        _log(f"[SCAN {scan_id}] └─ ✗ FAIL unknown_action")
        _emit({"type": "finding_end", "outcome": OUTCOME_UNKNOWN_ACTION,
               "turns": turn + 1, "ok": False})
        return FixResult(OUTCOME_UNKNOWN_ACTION, trace=trace, turns=turn + 1,
                         detail=str(action))

    _log(f"[SCAN {scan_id}] └─ ✗ FAIL turn_limit ({MAX_TURNS} turns)")
    _emit({"type": "finding_end", "outcome": OUTCOME_TURN_LIMIT,
           "turns": MAX_TURNS, "ok": False})
    return FixResult(OUTCOME_TURN_LIMIT, trace=trace, turns=MAX_TURNS)
