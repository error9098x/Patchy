# Patchy Agent Workflow Plan

Sequential agent pipeline. Railway deploy. Cerebras LLM via OpenAI-compatible SDK. Minimal file scanning.

---

## Goals

- Scan repo, find vulns, generate fixes, open PR. Sequential agents.
- Deploy Flask app to Railway. Background worker for scans (long task).
- Cheap: only scan changed/code files. Skip vendored, binaries, lockfiles.
- Simple: each agent = class with tools. Shared `Context` object.

---

## Architecture

```
User clicks "Scan" on dashboard
        │
        ▼
 POST /api/scan  ──► enqueue job (RQ + Redis)
        │
        ▼
┌─────────────────────────────────────────────┐
│  Worker process runs AgentPipeline          │
│                                             │
│  [CloneAgent] → [ScannerAgent]              │
│        → [ValidatorAgent] → [FixAgent]      │
│        → [PRAgent]                          │
│                                             │
│  Each step writes status to Redis + JSON    │
└─────────────────────────────────────────────┘
        │
        ▼
Frontend polls /api/scans/<id>/status
```

Two Railway services:
1. `web` — Flask (gunicorn). Serves UI + API.
2. `worker` — RQ worker. Runs pipeline.
3. `redis` — Railway Redis plugin. Queue + status cache.

---

## File Layout

```
patchy/
├── app.py                      # Flask routes (thin)
├── worker.py                   # RQ worker entrypoint
├── agents/
│   ├── __init__.py
│   ├── base.py                 # BaseAgent, Context
│   ├── clone_agent.py
│   ├── scanner_agent.py
│   ├── validator_agent.py
│   ├── fix_agent.py
│   └── pr_agent.py
├── tools/
│   ├── __init__.py
│   ├── git_tools.py            # clone, branch, commit, push
│   ├── semgrep_tool.py         # run semgrep, parse JSON
│   ├── file_filter.py          # which files to scan
│   ├── cerebras_client.py      # OpenAI-spec client → Cerebras
│   └── github_tool.py          # PyGithub wrapper
├── pipeline.py                 # AgentPipeline orchestrator
├── storage.py                  # scans.json read/write
├── requirements.txt
├── Procfile                    # web + worker commands
├── railway.json
└── .env.example
```

---

## Context Object

Single mutable dict-like object passed agent → agent.

```python
@dataclass
class Context:
    scan_id: str
    repo_full_name: str          # "user/repo"
    github_token: str
    repo_path: str | None = None          # filled by CloneAgent
    files_to_scan: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)   # raw semgrep
    validated: list[dict] = field(default_factory=list)  # after LLM triage
    fixes: list[dict] = field(default_factory=list)      # {file, patch, finding_id}
    branch: str | None = None
    pr_url: str | None = None
    status: str = "pending"
    error: str | None = None
```

---

## Base Agent

```python
class BaseAgent:
    name = "base"

    def execute(self, ctx: Context) -> Context:
        raise NotImplementedError

    def log(self, ctx, msg):
        redis.hset(f"scan:{ctx.scan_id}", self.name, msg)
```

---

## Agents

### 1. CloneAgent
- Tools: `git_tools.clone_shallow(repo, token)`
- Shallow clone (`--depth=1`) to `/tmp/patchy/<scan_id>`.
- Writes `ctx.repo_path`.

### 2. ScannerAgent
- Tools: `file_filter.pick_files()`, `semgrep_tool.run()`
- **File filter rules** (keeps scan cheap):
  - Include: `*.py *.js *.ts *.jsx *.tsx *.go *.java *.rb *.php`
  - Exclude dirs: `node_modules venv .venv dist build .git __pycache__ vendor .next`
  - Exclude: binary files, files > 500 KB, lockfiles (`package-lock.json`, `yarn.lock`, `poetry.lock`)
  - Cap: 200 files max per scan (sort by recent mtime if over)
- Runs semgrep: `semgrep --config=p/security-audit --config=p/secrets --json --timeout=30 <files>`
- Writes `ctx.findings`.

### 3. ValidatorAgent (LLM-powered)
- Tools: `cerebras_client.chat()`, code context fetch
- For each finding: send code snippet + rule to Cerebras. Ask: real issue? severity?
- Drops false positives. Writes `ctx.validated`.
- Batches 5-10 findings per LLM call to save tokens.

### 4. FixAgent (LLM-powered)
- Tools: `cerebras_client.chat()`, syntax check
- For each validated finding: prompt LLM for unified-diff patch.
- Validates patch applies cleanly (`git apply --check`).
- Writes `ctx.fixes`.

### 5. PRAgent
- Tools: `git_tools`, `github_tool`
- Creates branch `patchy/fix-<scan_id>`. Applies patches. Commits per fix. Pushes. Opens PR via GitHub API. Labels `security`, `automated`.
- Writes `ctx.pr_url`.

---

## Pipeline

```python
class AgentPipeline:
    def __init__(self):
        self.agents = [
            CloneAgent(),
            ScannerAgent(),
            ValidatorAgent(),
            FixAgent(),
            PRAgent(),
        ]

    def run(self, scan_id, repo_full_name, github_token):
        ctx = Context(scan_id=scan_id, repo_full_name=repo_full_name,
                      github_token=github_token)
        for agent in self.agents:
            try:
                ctx.status = f"running:{agent.name}"
                redis.hset(f"scan:{scan_id}", "status", ctx.status)
                ctx = agent.execute(ctx)
            except Exception as e:
                ctx.status = "failed"
                ctx.error = f"{agent.name}: {e}"
                break
        else:
            ctx.status = "complete"
        storage.save_scan(ctx)
        return ctx
```

---

## Cerebras Client (OpenAI-spec)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.cerebras.ai/v1",
    api_key=os.environ["CEREBRAS_API_KEY"],
)

def chat(messages, model="llama3.3-70b", **kw):
    return client.chat.completions.create(
        model=model, messages=messages, **kw
    )
```

Works identically with OpenAI, Groq, Together — swap `base_url`.

---

## Flask Integration

```python
# app.py
from rq import Queue
from redis import Redis
from pipeline import AgentPipeline

q = Queue(connection=Redis.from_url(os.environ["REDIS_URL"]))

@app.post("/api/scan")
def api_scan():
    data = request.get_json()
    scan_id = str(uuid.uuid4())
    q.enqueue(run_pipeline, scan_id, data["repo_name"],
              session["github_token"], job_timeout=600)
    return jsonify({"scan_id": scan_id, "status": "queued"})

@app.get("/api/scans/<scan_id>/status")
def api_status(scan_id):
    r = Redis.from_url(os.environ["REDIS_URL"])
    return jsonify(r.hgetall(f"scan:{scan_id}"))

def run_pipeline(scan_id, repo, token):
    AgentPipeline().run(scan_id, repo, token)
```

---

## Railway Deploy

**Procfile**
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: python worker.py
```

**worker.py**
```python
import os
from redis import Redis
from rq import Worker, Queue

conn = Redis.from_url(os.environ["REDIS_URL"])
if __name__ == "__main__":
    Worker([Queue(connection=conn)], connection=conn).work()
```

**railway.json**
```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": { "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT" }
}
```

**nixpacks.toml** (installs semgrep + git)
```toml
[phases.setup]
aptPkgs = ["git"]

[phases.install]
cmds = ["pip install -r requirements.txt", "pip install semgrep"]
```

**Railway setup steps**
1. Create project, link GitHub repo.
2. Add Redis plugin → auto-sets `REDIS_URL`.
3. Create two services from same repo: `web` (Procfile web) and `worker` (Procfile worker).
4. Set env vars on both: `CEREBRAS_API_KEY`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `SECRET_KEY`.
5. Deploy. Railway builds once, runs two processes.

---

## requirements.txt additions

```
flask
gunicorn
python-dotenv
redis
rq
openai>=1.0
PyGithub
requests
semgrep
```

---

## Cost / Perf Knobs

- `file_filter` 200-file cap → bounds semgrep time ~30-60s.
- Validator batches findings 5-10 per LLM call.
- Fix agent only runs on validated findings (usually <10).
- Total LLM calls per scan: ~3-5. Cerebras 70B is fast (~1s/call).
- Redis status updates let frontend poll without hammering DB.

---

## Build Order (2-3 days)

1. **Day 1 AM** — `tools/` (git, semgrep, file_filter, cerebras client). Test each in isolation.
2. **Day 1 PM** — `agents/` classes + `pipeline.py`. Run locally end-to-end on test repo.
3. **Day 2 AM** — RQ + Redis wiring. `worker.py`. Status polling endpoint.
4. **Day 2 PM** — Hook Flask routes. Frontend polling.
5. **Day 3** — Railway deploy, env vars, smoke test on real repo, polish PR template.

---

## Future Extensions

- Add `DependencyAgent` (runs `pip-audit`, `npm audit`).
- Add `TestAgent` (runs repo tests on fix branch before PR).
- Swap sequential for LLM-orchestrated when agent count grows > 6.
