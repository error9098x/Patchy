#!/usr/bin/env python3
"""Agent-harness test for MiniMax-M2 on NVIDIA endpoint.

Runs progressively harder tests to measure:
  1. connection
  2. plain JSON object reliability
  3. plain JSON array reliability
  4. single-turn file-selection (classifier)
  5. multi-turn agent loop (ask-files -> read -> fix)
  6. fix JSON quality

Each test runs N trials and reports pass rate so we can tune prompts.
"""

import os
import sys
import json
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if not os.environ.get("NVIDIA_API_KEY"):
    print("NVIDIA_API_KEY missing"); sys.exit(1)

from tools.nvidia_client import chat, _extract_json, test_connection

TRIALS = int(os.environ.get("TRIALS", "3"))
VERBOSE = os.environ.get("VERBOSE", "0") == "1"

FAKE_REPO = {
    "app.py": "from flask import Flask, request\nimport sqlite3\nfrom auth import verify_token\napp = Flask(__name__)\n\n@app.route('/user')\ndef user():\n    uid = request.args.get('id')\n    token = request.headers.get('Authorization')\n    if not verify_token(token):\n        return 'nope', 401\n    conn = sqlite3.connect('db.sqlite')\n    cur = conn.cursor()\n    cur.execute(f\"SELECT * FROM users WHERE id = {uid}\")\n    return str(cur.fetchall())\n",
    "auth.py": "import jwt\nSECRET = 'hardcoded-secret-123'\ndef verify_token(tok):\n    try:\n        jwt.decode(tok, SECRET, algorithms=['HS256'])\n        return True\n    except Exception:\n        return False\n",
    "db.py": "import sqlite3\ndef get_conn():\n    return sqlite3.connect('db.sqlite')\n",
    "utils.py": "def slugify(s):\n    return s.lower().replace(' ', '-')\n",
    "readme.md": "# demo app",
}

FAKE_FINDING = {
    "check_id": "python.sqlalchemy.security.audit.avoid-sqlalchemy-raw-query",
    "path": "app.py",
    "start": {"line": 13},
    "extra": {
        "message": "User input is interpolated directly into SQL query — SQL injection risk.",
        "severity": "HIGH",
    },
}


def _parse_json(text):
    try:
        return json.loads(_extract_json(text)), None
    except Exception as e:
        return None, str(e)


def _run(label, fn):
    print(f"\n── {label} ──")
    passes, fails, durs = 0, 0, []
    for i in range(TRIALS):
        t0 = time.time()
        try:
            ok, detail = fn()
            dt = time.time() - t0
            durs.append(dt)
            mark = "PASS" if ok else "FAIL"
            print(f"  trial {i+1}: {mark} [{dt:.1f}s] {detail or ''}")
            if ok: passes += 1
            else: fails += 1
        except Exception as e:
            dt = time.time() - t0
            durs.append(dt)
            print(f"  trial {i+1}: ERROR [{dt:.1f}s] {e}")
            fails += 1
    avg = sum(durs) / len(durs) if durs else 0
    print(f"  → {passes}/{TRIALS} pass, avg {avg:.1f}s")
    return passes == TRIALS


def test_connection_step():
    return _run("connection", lambda: (test_connection(), "pong"))


def test_json_object():
    def trial():
        sys_msg = "Respond ONLY with a JSON object. No prose. No markdown fences."
        user = 'Give a JSON object with keys "name" (string) and "age" (integer). Use name="patchy" age=1.'
        resp = chat([{"role": "system", "content": sys_msg}, {"role": "user", "content": user}], temperature=0.2, max_tokens=200)
        if VERBOSE: print(f"    RAW: {resp[:200]}")
        obj, err = _parse_json(resp)
        if err: return False, f"parse: {err}"
        ok = isinstance(obj, dict) and obj.get("name") == "patchy" and obj.get("age") == 1
        return ok, "" if ok else f"bad obj: {obj}"
    return _run("json object", trial)


def test_json_array():
    def trial():
        sys_msg = "Respond ONLY with a JSON array. No prose."
        user = 'Return a JSON array of 3 objects, each with "id" (int 1..3) and "label" (string "a","b","c").'
        resp = chat([{"role": "system", "content": sys_msg}, {"role": "user", "content": user}], temperature=0.2, max_tokens=300)
        if VERBOSE: print(f"    RAW: {resp[:200]}")
        arr, err = _parse_json(resp)
        if err: return False, f"parse: {err}"
        ok = isinstance(arr, list) and len(arr) == 3 and all("id" in x and "label" in x for x in arr)
        return ok, "" if ok else f"bad arr: {arr}"
    return _run("json array", trial)


def test_file_classifier():
    """Single-turn: give LLM finding + file tree, ask which files to read."""
    file_list = "\n".join(f"- {p}" for p in FAKE_REPO.keys())
    sys_msg = (
        "You are a security auditor. You respond ONLY with valid JSON. "
        "No prose outside JSON. No markdown fences."
    )
    user = f"""Finding:
{json.dumps(FAKE_FINDING, indent=2)}

Repository files:
{file_list}

Task: choose up to 5 files you must read to confidently fix this issue.
Return JSON: {{"files_to_read": ["path1", "path2"], "reason": "short"}}"""

    def trial():
        resp = chat([{"role": "system", "content": sys_msg}, {"role": "user", "content": user}], temperature=0.2, max_tokens=500)
        if VERBOSE: print(f"    RAW: {resp[:300]}")
        obj, err = _parse_json(resp)
        if err: return False, f"parse: {err}"
        files = obj.get("files_to_read") if isinstance(obj, dict) else None
        if not isinstance(files, list) or not files:
            return False, f"no files: {obj}"
        hallucinated = [f for f in files if f not in FAKE_REPO]
        if hallucinated:
            return False, f"hallucinated: {hallucinated}"
        picked_app = "app.py" in files
        picked_auth = "auth.py" in files
        return picked_app and picked_auth, f"picked={files}"
    return _run("file classifier (agent tick 1)", trial)


def test_agent_loop():
    """Multi-turn: LLM picks files, we feed them, LLM returns fix JSON."""
    sys_msg = (
        "You are Patchy, a security-fix agent. Each turn you respond with ONE JSON object, "
        "no prose, no markdown fences. Allowed actions:\n"
        '  {"action":"read_files","files":[...],"reason":"..."}\n'
        '  {"action":"fix","file":"path","patched_content":"...","explanation":"...","confidence":0.0-1.0}\n'
        "Use read_files at most twice, then emit fix."
    )
    file_list = "\n".join(f"- {p}" for p in FAKE_REPO.keys())
    user0 = f"""Finding:
{json.dumps(FAKE_FINDING, indent=2)}

Repo files:
{file_list}

Respond with your next action as a single JSON object."""

    def trial():
        messages = [{"role": "system", "content": sys_msg}, {"role": "user", "content": user0}]
        for turn in range(4):
            resp = chat(messages, temperature=0.3, max_tokens=2000)
            if VERBOSE: print(f"    turn {turn} RAW: {resp[:250]}")
            obj, err = _parse_json(resp)
            if err: return False, f"turn {turn} parse: {err}"
            if not isinstance(obj, dict): return False, f"turn {turn} not dict"
            action = obj.get("action")
            messages.append({"role": "assistant", "content": json.dumps(obj)})
            if action == "read_files":
                files = obj.get("files", [])
                bad = [f for f in files if f not in FAKE_REPO]
                if bad: return False, f"halluc files: {bad}"
                blob = "\n\n".join(f"=== {f} ===\n{FAKE_REPO[f]}" for f in files if f in FAKE_REPO)
                messages.append({"role": "user", "content": f"File contents:\n{blob}\n\nNext action?"})
                continue
            if action == "fix":
                patched = obj.get("patched_content", "")
                conf = obj.get("confidence", 0)
                file = obj.get("file")
                if file not in FAKE_REPO: return False, f"bad file: {file}"
                if "f\"SELECT" in patched or "f'SELECT" in patched:
                    return False, "still has f-string SQL"
                has_param = "?" in patched or "%s" in patched or "execute(" in patched and "," in patched
                return has_param and conf > 0.4, f"file={file} conf={conf}"
            return False, f"unknown action: {action}"
        return False, "loop limit without fix"
    return _run("agent loop (ask -> read -> fix)", trial)


def test_fix_quality():
    """Direct fix with full context — upper bound on quality."""
    sys_msg = "You are a security engineer. Respond ONLY with a JSON object. No prose."
    user = f"""Fix this vulnerability.

Finding: {json.dumps(FAKE_FINDING)}

File app.py:
{FAKE_REPO['app.py']}

File auth.py:
{FAKE_REPO['auth.py']}

Return JSON: {{"patched_content": "full new app.py content", "explanation": "...", "confidence": 0.0-1.0}}"""

    def trial():
        resp = chat([{"role": "system", "content": sys_msg}, {"role": "user", "content": user}], temperature=0.3, max_tokens=3000)
        if VERBOSE: print(f"    RAW: {resp[:300]}")
        obj, err = _parse_json(resp)
        if err: return False, f"parse: {err}"
        patched = obj.get("patched_content", "")
        if "f\"SELECT" in patched or "f'SELECT" in patched:
            return False, "still has f-string SQL"
        if "?" not in patched and "%s" not in patched:
            return False, "no parameterization"
        return obj.get("confidence", 0) > 0.4, f"conf={obj.get('confidence')}"
    return _run("fix quality (full context)", trial)


if __name__ == "__main__":
    print(f"MiniMax-M2 agent harness | TRIALS={TRIALS} VERBOSE={VERBOSE}")
    print("=" * 55)
    results = {
        "connection": test_connection_step(),
        "json_obj": test_json_object(),
        "json_arr": test_json_array(),
        "classifier": test_file_classifier(),
        "agent_loop": test_agent_loop(),
        "fix_quality": test_fix_quality(),
    }
    print("\n" + "=" * 55)
    print("SUMMARY")
    for k, v in results.items():
        print(f"  {'OK  ' if v else 'FAIL'}  {k}")
    all_pass = all(results.values())
    print(f"\n{'ALL PASS' if all_pass else 'SOME FAIL — tune prompts before agent-loop rollout'}")
    sys.exit(0 if all_pass else 1)
