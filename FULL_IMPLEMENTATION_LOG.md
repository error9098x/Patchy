# Patchy Full Implementation Log

## Todo Checklist

- [x] Capture what was delivered in the earlier "Opus" implementation pass
- [x] Capture what was changed in the later agentic follow-up pass
- [x] Document backend architecture changes in detail
- [x] Document UI/UX changes in detail
- [x] Document storage/data-model changes in detail
- [x] Document test harnesses and observed test outcomes
- [x] Document remaining work and recommended next steps

---

## Scope Of This Document

This file summarizes all major work completed across the conversation:

1. The earlier large implementation batch (referred to as "Opus" in chat).
2. The follow-up implementation and hardening work completed after that.
3. Verified runtime/test outputs that were observed in terminal.

It includes both delivered behavior and technical details (files, functions, APIs, and runtime flow).

---

## Phase 1: Earlier "Opus" Batch (As Reported In Chat)

The earlier implementation batch reported these file-level changes:

- `storage.py` (`+76 -41`)
- `nvidia_client.py` (`+45 -18`)
- `scan_pipeline.py` (`+134 -84`)
- `app.py` (`+153 -79`)
- `scan.js` (`+109 -58`)
- `dashboard.js` (`+133 -15`)
- `scan_live.html` (`+238 -0`)
- `scan_detail.html` (`+15 -23`)

The intent reported in chat for that pass:

- Backend-first completion.
- Frontend and templates updated after backend.
- Added/expanded scan progress handling.
- Added live scan page and real-time style scan flow.
- Improved data transformation in backend API responses.
- Added enhanced API/live scan route behavior.

This earlier pass established the baseline that the later work built on.

---

## Phase 2: NVIDIA Reliability + Agent Readiness Validation

### 2.1 `test_nvidia.py` was rewritten into a focused harness

File: `test_nvidia.py`

Purpose changed from basic connection demo into agent-readiness validation for MiniMax M2.7:

- Connection reliability check.
- Strict JSON object output reliability.
- Strict JSON array output reliability.
- Single-turn file classifier behavior (`files_to_read` JSON contract).
- Multi-turn agent loop behavior (`read_files -> fix`).
- Fix quality upper-bound check with fuller context.

Environment controls:

- `TRIALS` to repeat each test.
- `VERBOSE=1` to print raw model snippets.

### 2.2 Observed result from terminal run (`VERBOSE=1 TRIALS=3`)

Observed in terminal:

- `connection`: 3/3 pass
- `json object`: 3/3 pass
- `json array`: 3/3 pass
- `file classifier`: 3/3 pass
- `agent loop`: 3/3 pass
- `fix quality`: 3/3 pass
- Final status: `ALL PASS`

Interpretation:

- Model consistently followed JSON contract in tested scenarios.
- Agentic tool-selection style appears feasible with current model/provider integration.

### 2.3 Additional grep capability test

File: `test_nvidia_grep.py`

Purpose:

- Validate that model can choose `{"action":"grep", ...}` under strict JSON instruction.

Observed in terminal:

- 3/3 passes with valid grep patterns returned.
- Final status: `PASS`.

---

## Phase 3: Core Agentic Engine Added

### 3.1 New file `tools/fix_agent.py`

A dedicated agent loop was introduced with strict action protocol and bounded execution.

#### Key constants and guardrails

- `MAX_TURNS = 4`
- `MAX_FILES_PER_READ = 5`
- `MAX_PATCH_CHARS = 20000`
- `MAX_TOKENS_PER_TURN = 3000`
- `MAX_FILE_BYTES = 64000`
- `MAX_INDEX_FILES = 400`
- `GREP_MAX_MATCHES = 40`
- `GREP_TIMEOUT = 10`

#### Supported agent actions

- `read_files`
- `grep`
- `fix`
- `give_up`

#### Outcome taxonomy (explicit failure typing)

- `ok`
- `bad_json`
- `unknown_action`
- `turn_limit`
- `llm_gave_up`
- `api_error`
- `empty_patch`
- `patch_too_large`
- `low_confidence`
- `bad_regex` (defined for regex validation path)

#### Internal design elements

- `build_file_index(repo_path)`:
  - Filters by ignored dirs and file extensions.
  - Skips oversized files.
- `_run_ripgrep(...)`:
  - Uses `rg` first, fallback to `grep -rnE` if needed.
  - Returns compact `path:line:content` snippets.
- `FixResult` object:
  - Standardized return shape (`ok`, `outcome`, `trace`, `turns`, etc).
- `run_fix_agent(...)`:
  - Drives the turn loop.
  - Parses JSON strictly via `_extract_json`.
  - Emits rich turn-level trace events.
  - Enforces guardrails and returns typed outcomes.

#### Live event callback support

`run_fix_agent` now accepts `event_cb` and emits structured events:

- `finding_start`
- `turn` events (including action-level details)
- `finding_end`

These events were used for live UI theater.

---

## Phase 4: Pipeline Migration To Agentic Flow

### 4.1 `scan_pipeline.py` migrated from single-shot fix generation

Before:

- Direct `generate_fix(finding, code_context)` call with limited context window.

After:

- Uses `build_file_index(repo_path)` once per scan.
- Iterates findings and calls:
  - `run_fix_agent(finding, repo_path, file_index, scan_id=..., event_cb=...)`

### 4.2 New per-finding tracking in pipeline

Added maps:

- `agent_outcomes[finding_key]`
- `agent_traces[finding_key]`

`finding_key` format:

- `"{check_id}|{file_path}|{line_num}"`

### 4.3 Live finding pointer and event capture

For each finding:

- `storage.set_current_finding(...)` is updated.
- Callback appends events through:
  - `storage.append_agent_event(scan_id, event)`

After fixing loop:

- `storage.set_current_finding(scan_id, None)`

### 4.4 Final stored findings now include agent metadata

`_format_findings_for_storage(...)` now stores:

- `agent_outcome`
- `agent_trace`

alongside existing fields (`file`, `line`, `severity`, `fix_status`, etc).

### 4.5 Debug logging behavior

`scan_pipeline.py` now gates logs by:

- `PATCHY_DEBUG=1`

When off, pipeline runs quieter. When on, detailed step-by-step logs are printed.

---

## Phase 5: Storage Model Extended For Live Theatre

### 5.1 `storage.py` new fields on scan records

On scan creation:

- `agent_events: []`
- `current_finding: None`

### 5.2 New storage APIs

- `append_agent_event(scan_id, event)`
  - Appends event with timestamp.
  - Caps at `MAX_AGENT_EVENTS` (400).
- `set_current_finding(scan_id, info)`
  - Tracks currently processed finding for UI.

### 5.3 Status API payload enriched

`get_scan_status(scan_id)` now includes:

- `agent_events`
- `current_finding`
- `pr_branch`
- `pr_number`

This powers richer live page rendering.

---

## Phase 6: Live UI "Agent Theatre" Implemented

### 6.1 `templates/scan_live.html` was expanded significantly

Major UI sections:

- Existing scan header/progress.
- Pipeline steps panel.
- New "Agent Theatre" panel:
  - current-finding summary card
  - live event stream timeline
- New PR celebration block:
  - highlighted state when PR is created
  - direct GitHub PR link CTA

### 6.2 Client-side live rendering behavior

The script on page now:

- Polls `/api/scans/<scan_id>/status` every 1.5s.
- Updates:
  - status badge
  - progress bar and percent
  - pipeline steps
  - findings/fixes/valid/pr stats
  - current-finding panel
  - event stream incrementally (no full rerender every poll)
- Auto-reveals PR celebration card when `pr_url` appears.
- Stops polling/timer when scan reaches terminal state (`complete`/`failed`).

### 6.3 Event mapping UI logic

Event stream supports semantic rows for:

- finding start/end
- `read_files`
- `grep`
- `fix`
- `give_up`
- `bad_json`
- `api_error`
- unknown action

Each row includes icon/tone/summary/detail and turn index where available.

---

## Phase 7: LLM Client Logging Controls

### 7.1 `tools/nvidia_client.py` debug gating

Added:

- `DEBUG = os.environ.get("PATCHY_DEBUG", "0") == "1"`
- `_dbg(...)` helper

Internal `[LLM] ...` diagnostics are routed through `_dbg` so verbose logs are available only when debug is enabled.

### 7.2 Existing response cleanup retained

Already-present handling remains part of stack:

- `_strip_think_tags(...)` for model reasoning tags.
- `_extract_json(...)` with support for markdown code fences and raw object/array extraction.

---

## Phase 8: New and Updated Test Assets

### Added / major test scripts

- `test_nvidia.py` (rewritten harness)
- `test_nvidia_grep.py` (grep action validation)
- `test_fix_agent.py` (agent E2E against temp repo)

### `test_fix_agent.py` observed outcome

Terminal run (`TRIALS=2`) showed:

- 2/2 passed
- Each trial:
  - finding start
  - turn 0 read_files
  - turn 1 fix
  - outcome `ok`

This validated end-to-end `run_fix_agent` behavior with live event emission path.

---

## Files With Work In Progress / Current Dirty Tree

Current status includes both previously existing and newly changed files. Snapshot includes:

- Modified:
  - `.env.example`
  - `.gitignore`
  - `app.py`
  - `requirements.txt`
  - `static/js/api.js`
  - `static/js/dashboard.js`
  - `static/js/scan.js`
  - `templates/components/navbar.html`
  - `templates/index.html`
  - `templates/scan_detail.html`
  - `test_nvidia.py`
  - `tools/nvidia_client.py`
- Untracked:
  - `BUILD_AGENTS_PROMPT.md`
  - `DEV_READY.md`
  - `github_client.py`
  - `issue_responder.py`
  - `metrics.json`
  - `scan_pipeline.py`
  - `storage.py`
  - `templates/scan_live.html`
  - `tools/fix_agent.py`

---

## End-To-End Runtime Flow (Current)

1. User starts scan from dashboard.
2. Flask route creates scan record and background thread starts pipeline.
3. Pipeline:
   - clone repo
   - semgrep scan
   - for each finding (up to cap):
     - set current finding
     - run agent loop (`read_files`/`grep`/`fix`/`give_up`)
     - append live events
   - syntax validate accepted fixes
   - create branch/commit/PR if valid fixes exist
   - persist findings with agent trace/outcome
4. Live page polls status endpoint and renders:
   - progress + step timeline
   - current finding
   - event stream
   - PR celebration card + GitHub link when available

---

## What Is Deferred (Not Implemented Yet)

Per user direction, the following were intentionally deferred:

- Feature B: in-product Q/A chat per finding ("why did agent do this?")
- Feature C: interactive post-PR revision commits from UI chat

The architecture now stores enough trace metadata to make Feature B easier later.

---

## Recommended Next Steps

1. Render `agent_trace` directly in `scan_detail.html` (read-only first).
2. Add pagination/windowing for `agent_events` if long scans exceed 400 events.
3. Add explicit backend schema validation for incoming agent event objects.
4. Add integration tests for:
   - PR creation path with agent outcomes mixed (`ok` + failures)
   - no-finding and all-fail edge cases in live UI
5. Stabilize commit history by splitting current dirty tree into logical commits:
   - agent-core
   - storage/status API
   - live-theatre UI
   - test harnesses

---

## Quick Command Log (Referenced During Work)

- `VERBOSE=1 TRIALS=3 python3 test_nvidia.py` -> all sections passed
- `python test_nvidia_grep.py` -> grep action test passed
- `TRIALS=2 python3 test_fix_agent.py` -> 2/2 pass

