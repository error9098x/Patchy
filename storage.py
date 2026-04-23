"""
JSON File Storage with filelock
Enhanced with step logging for real-time scan progress.
"""

import json
import os
import time
import uuid
from filelock import FileLock

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCANS_FILE = os.path.join(BASE_DIR, "scans.json")
METRICS_FILE = os.path.join(BASE_DIR, "metrics.json")

MAX_AGENT_EVENTS = 400


PIPELINE_STEPS = [
    {"step": 1, "name": "clone",    "label": "Clone Repository"},
    {"step": 2, "name": "semgrep",  "label": "Semgrep Analysis"},
    {"step": 3, "name": "fixing",   "label": "AI Fix Generation"},
    {"step": 4, "name": "validate", "label": "Validate Fixes"},
    {"step": 5, "name": "branch",   "label": "Create Branch"},
    {"step": 6, "name": "pr",       "label": "Open Pull Request"},
]


def _generate_scan_hash():
    return f"PTY-{uuid.uuid4().hex[:7]}"


def _read_json(filepath):
    if not os.path.exists(filepath):
        return {"scans": []}
    lock = FileLock(filepath + ".lock", timeout=5)
    with lock:
        with open(filepath, 'r') as f:
            return json.load(f)


def _write_json(filepath, data):
    lock = FileLock(filepath + ".lock", timeout=5)
    with lock:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)


def create_scan(scan_id, repo_name):
    """Create new scan record with unique hash and step timeline."""
    scan_hash = _generate_scan_hash()
    steps = []
    for s in PIPELINE_STEPS:
        steps.append({
            "step": s["step"], "name": s["name"], "label": s["label"],
            "status": "pending", "message": "", "detail": "",
            "started_at": None, "completed_at": None, "duration": None,
        })

    scan = {
        "id": scan_id, "scan_hash": scan_hash, "repo": repo_name,
        "status": "cloning",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "completed_at": None,
        "findings_count": 0, "fixes_generated": 0, "fixes_valid": 0,
        "findings": [], "pr_url": None, "pr_branch": None, "pr_number": None,
        "error": None, "progress": 5, "steps": steps,
        "agent_events": [], "current_finding": None,
    }
    data = _read_json(SCANS_FILE)
    data["scans"].insert(0, scan)
    _write_json(SCANS_FILE, data)
    return scan


def update_scan(scan_id, **updates):
    data = _read_json(SCANS_FILE)
    for scan in data["scans"]:
        if scan["id"] == scan_id:
            scan.update(updates)
            break
    _write_json(SCANS_FILE, data)


def add_scan_step(scan_id, step_name, status, message="", detail=""):
    """Update a pipeline step's status. Tracks timing automatically."""
    data = _read_json(SCANS_FILE)
    for scan in data["scans"]:
        if scan["id"] == scan_id:
            for step in scan.get("steps", []):
                if step["name"] == step_name:
                    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    if status == "running" and step["status"] != "running":
                        step["started_at"] = now
                    if status in ("complete", "failed", "skipped"):
                        step["completed_at"] = now
                        if step.get("started_at"):
                            try:
                                t0 = time.mktime(time.strptime(step["started_at"], "%Y-%m-%dT%H:%M:%SZ"))
                                t1 = time.mktime(time.strptime(now, "%Y-%m-%dT%H:%M:%SZ"))
                                step["duration"] = round(t1 - t0, 1)
                            except Exception:
                                pass
                    step["status"] = status
                    if message:
                        step["message"] = message
                    if detail:
                        step["detail"] = detail
                    break
            break
    _write_json(SCANS_FILE, data)


def append_agent_event(scan_id, event):
    """Append a granular agent event (turn/action). Caps list at MAX_AGENT_EVENTS."""
    event = dict(event)
    event.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    data = _read_json(SCANS_FILE)
    for scan in data["scans"]:
        if scan["id"] == scan_id:
            events = scan.setdefault("agent_events", [])
            events.append(event)
            if len(events) > MAX_AGENT_EVENTS:
                del events[: len(events) - MAX_AGENT_EVENTS]
            break
    _write_json(SCANS_FILE, data)


def set_current_finding(scan_id, info):
    """Record which finding agent is working on (or None when idle)."""
    data = _read_json(SCANS_FILE)
    for scan in data["scans"]:
        if scan["id"] == scan_id:
            scan["current_finding"] = info
            break
    _write_json(SCANS_FILE, data)


def get_scan(scan_id):
    data = _read_json(SCANS_FILE)
    for scan in data["scans"]:
        if scan["id"] == scan_id:
            return scan
    return None


def get_all_scans():
    data = _read_json(SCANS_FILE)
    return data.get("scans", [])


def get_scan_status(scan_id):
    """Full status with steps for live progress UI."""
    scan = get_scan(scan_id)
    if not scan:
        return {"status": "not_found", "progress": 0}
    return {
        "id": scan["id"], "scan_hash": scan.get("scan_hash", ""),
        "repo": scan.get("repo", ""), "status": scan["status"],
        "progress": scan.get("progress", 0),
        "findings_count": scan.get("findings_count", 0),
        "fixes_generated": scan.get("fixes_generated", 0),
        "fixes_valid": scan.get("fixes_valid", 0),
        "pr_url": scan.get("pr_url"), "error": scan.get("error"),
        "steps": scan.get("steps", []),
        "started_at": scan.get("started_at"),
        "completed_at": scan.get("completed_at"),
        "agent_events": scan.get("agent_events", []),
        "current_finding": scan.get("current_finding"),
        "pr_branch": scan.get("pr_branch"),
        "pr_number": scan.get("pr_number"),
    }


def log_metric(scan_id, repo, findings_count, fixes_generated, fixes_valid,
               pr_created, scan_duration, llm_calls, llm_duration):
    """Log scan metrics for dissertation analysis."""
    metric = {
        "scan_id": scan_id, "repo": repo,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "findings_count": findings_count, "fixes_generated": fixes_generated,
        "fixes_valid": fixes_valid, "pr_created": pr_created,
        "scan_duration_seconds": round(scan_duration, 2),
        "llm_calls": llm_calls, "llm_duration_seconds": round(llm_duration, 2)
    }
    data = _read_json(METRICS_FILE)
    data.setdefault("scans", []).append(metric)
    _write_json(METRICS_FILE, data)
    return metric
