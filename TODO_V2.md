# Patchy - TODO V2 (Granular)

> Every task ≤30 min. Exact commands. Verification steps.
> Supersedes: TODO.md

**Last Updated**: 2026-04-23  
**Estimated Total**: 17 hours (~2.5 days)

---

## Phase 0: Prerequisites (30 min)

### 0.1 Register GitHub App (15 min)
- [ ] Go to: https://github.com/settings/apps/new
- [ ] Fill in:
  - App name: `Patchy`
  - Homepage URL: `http://localhost:5000`
  - Callback URL: `http://localhost:5000/callback`
  - Webhook URL: `https://placeholder.ngrok.io/webhook` (update later)
  - Webhook secret: generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set permissions:
  - Repository > Contents: Read & Write
  - Repository > Pull Requests: Read & Write
  - Repository > Issues: Read & Write
  - Repository > Metadata: Read-only
- [ ] Subscribe to events: `Issue comment`
- [ ] Create app → note App ID, Client ID, Client Secret
- [ ] Generate private key → save as `github-app-key.pem` in project root
- **Verify**: App visible at https://github.com/settings/apps

### 0.2 Get Cerebras API Key (5 min)
- [ ] Go to: https://cloud.cerebras.ai
- [ ] Create account / login
- [ ] Generate API key
- **Verify**: `curl -H "Authorization: Bearer YOUR_KEY" https://api.cerebras.ai/v1/models` returns model list

### 0.3 Create .env File (5 min)
```bash
cat > .env << 'EOF'
GITHUB_APP_ID=YOUR_APP_ID
GITHUB_APP_PRIVATE_KEY_PATH=./github-app-key.pem
GITHUB_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET
GITHUB_CLIENT_ID=YOUR_CLIENT_ID
GITHUB_CLIENT_SECRET=YOUR_CLIENT_SECRET
CEREBRAS_API_KEY=YOUR_CEREBRAS_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=development
EOF
```
- **Verify**: `cat .env` shows all values filled

### 0.4 Install Dependencies (5 min)
```bash
pip install -r requirements.txt
pip install semgrep filelock PyJWT cryptography
```
- **Verify**: `semgrep --version` returns version number
- **Verify**: `python3 -c "import flask; print(flask.__version__)"` → 3.1.0

---

## Phase 1: GitHub App Auth (2 hrs)

### 1.1 Create github_client.py (30 min)
- [ ] Create `github_client.py` in project root
- [ ] Implement `get_installation_token(installation_id)`:
  - Read private key from `.pem` file
  - Generate JWT (iat, exp +10min, iss=app_id)
  - POST https://api.github.com/app/installations/{id}/access_tokens
  - Return installation token
- [ ] Implement `get_user_repos(installation_token)`:
  - GET https://api.github.com/installation/repositories
  - Return list of repos
- **Verify**: Write test script that prints JWT, gets token, lists repos

### 1.2 Update Login Flow in app.py (30 min)
- [ ] Update `/login` route:
  - Redirect to `https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&scope=read:user`
- [ ] Update `/callback` route:
  - Exchange code for user token
  - Fetch user info (GET /user)
  - Get app installation for user (GET /user/installations)
  - Store in session: `{username, avatar_url, installation_id, access_token}`
- **Verify**: Login flow works end-to-end, session has user data

### 1.3 Auth Middleware (15 min)
- [ ] Create `login_required` decorator:
```python
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated
```
- [ ] Apply to `/dashboard`, `/scans`, `/scans/<id>`, all `/api/*` routes
- **Verify**: Unauthenticated access redirects to login

### 1.4 Wire Repos to Dashboard API (15 min)
- [ ] Update `/api/repos` to call `get_user_repos(session['installation_token'])`
- [ ] Return repos in format matching MOCK_DATA structure
- **Verify**: `/api/repos` returns real repos from GitHub

---

## Phase 2: Scan Pipeline (4 hrs)

### 2.1 Create storage.py (15 min)
- [ ] Implement `save_scan(scan_data)` with filelock
- [ ] Implement `get_scans()` — return all scans
- [ ] Implement `get_scan(scan_id)` — return single scan
- [ ] Implement `update_scan_status(scan_id, status, data={})` 
- [ ] Initialize empty `scans.json` if not exists
- **Verify**: Write/read round-trip test

### 2.2 Create cerebras_client.py (20 min)
- [ ] Implement `call_cerebras(system_prompt, user_prompt)`:
  - POST to Cerebras API
  - temperature: 0.2
  - max_tokens: 4000
  - 3x retry with exponential backoff
  - 30s timeout
- **Verify**: Test with simple prompt, get response

### 2.3 Create prompts.py (15 min)
- [ ] Define `SECURITY_FIX_SYSTEM` and `SECURITY_FIX_USER` templates
- [ ] Define `ISSUE_RESPONSE_SYSTEM` and `ISSUE_RESPONSE_USER` templates
- [ ] Format functions: `format_fix_prompt(finding, code_context)` 
- **Verify**: Print formatted prompts, check they look correct

### 2.4 Create scan_pipeline.py - Clone Step (30 min)
- [ ] Implement `clone_repo(repo_full_name, github_token)`:
  - Create tmpdir
  - `git clone --depth 1` with token auth
  - Check size (< 100MB)
  - Return clone path + tmpdir handle
- **Verify**: Clone a test repo, check files exist

### 2.5 Create scan_pipeline.py - Semgrep Step (30 min)
- [ ] Implement `run_semgrep(clone_dir)`:
  - `semgrep --config auto --json --timeout 300`
  - Parse JSON output
  - Extract: file, line, rule_id, severity, message
  - Return findings list
- **Verify**: Run on test repo, check findings structure

### 2.6 Create scan_pipeline.py - Fix Step (30 min)
- [ ] Implement `generate_fixes(findings, clone_dir)`:
  - For each finding (max 20):
    - Read code context (±10 lines around finding)
    - Format prompt using prompts.py
    - Call Cerebras
    - Validate fix (ast.parse for Python, etc.)
    - Store valid fixes
  - Return list of {file, original, fixed, finding_id}
- **Verify**: Generate fix for known SQL injection, check output

### 2.7 Create scan_pipeline.py - PR Step (30 min)
- [ ] Implement `create_pr(repo_full_name, fixes, scan_id, github_token)`:
  - Create branch: `patchy/fix-{scan_id}`
  - For each fix: update file content via GitHub API (no need to push, use Contents API)
  - Create PR:
    - Title: `🔒 Patchy: Fixed {n} security vulnerabilities`
    - Body: markdown table of findings + fixes
    - Base: default branch
    - Head: patchy/fix-{scan_id}
  - Return PR URL
- **Verify**: PR created on test repo with correct fixes

### 2.8 Wire Pipeline to API (30 min)
- [ ] Update `/api/scan` to:
  1. Create scan record (status: "cloning")
  2. Run pipeline in background thread (threading.Thread)
  3. Return scan_id immediately
  4. Pipeline updates status as it progresses
- [ ] Update `/api/scans/<id>/status` to read from storage
- **Verify**: POST /api/scan → returns scan_id → poll status → complete

---

## Phase 3: Frontend Integration (1.5 hrs)

### 3.1 Replace Mock Data in api.js (30 min)
- [ ] Change `fetchRepos()` to real `fetch('/api/repos')`
- [ ] Change `scanRepo()` to real `POST /api/scan`
- [ ] Change `fetchScanHistory()` to real `fetch('/api/scans')`
- [ ] Change `fetchScanDetails()` to real `fetch('/api/scans/:id')`
- [ ] Change `fetchScanStatus()` to real `fetch('/api/scans/:id/status')`
- [ ] Keep MOCK_DATA as fallback (commented out)
- **Verify**: Dashboard shows real repos from GitHub

### 3.2 Add Scan Polling to Dashboard (30 min)
- [ ] After scan trigger: start 3s polling interval
- [ ] Update progress UI: cloning → scanning → fixing → creating_pr → complete
- [ ] On complete: show success notification + PR link
- [ ] On error: show error message + retry button
- **Verify**: Scan shows real-time progress in UI

### 3.3 Error Handling UI (30 min)
- [ ] Handle `status: "error"` responses from all API calls
- [ ] Show error toasts/notifications
- [ ] Handle: auth expired, rate limited, repo too large, scan failed
- **Verify**: Simulate errors, check UI shows appropriate messages

---

## Phase 4: Webhooks & Issue Responder (2 hrs)

### 4.1 Setup ngrok (10 min)
```bash
# Install ngrok if needed
brew install ngrok   # or download from ngrok.com
# Start tunnel
ngrok http 5000
```
- [ ] Copy ngrok URL
- [ ] Update GitHub App webhook URL to: `https://xxxx.ngrok.io/webhook`
- **Verify**: ngrok dashboard shows tunnel active

### 4.2 Create issue_responder.py (30 min)
- [ ] Implement `handle_issue_comment(event_data)`:
  - Check action == "created"
  - Check if comment body contains "@patchy" (case-insensitive)
  - Extract: issue title, issue body, comment body, repo name
  - Format prompt using `ISSUE_RESPONSE_SYSTEM/USER`
  - Call Cerebras
  - Return response text
- **Verify**: Test with mock event data

### 4.3 Implement Webhook Handler (30 min)
- [ ] Update `/webhook` route in app.py:
  - Verify `X-Hub-Signature-256` header:
    ```python
    import hmac, hashlib
    signature = request.headers.get('X-Hub-Signature-256')
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(), request.data, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        abort(401)
    ```
  - Parse event type from `X-GitHub-Event` header
  - If `issue_comment`: call `handle_issue_comment()`
  - Post response via GitHub API
- **Verify**: Create issue, @mention bot, see response posted

### 4.4 Post Comment via GitHub API (20 min)
- [ ] Implement `post_issue_comment(repo, issue_number, body, token)`:
  - POST /repos/{repo}/issues/{issue_number}/comments
  - Body: {"body": response_text}
- **Verify**: Bot comment appears on GitHub issue

### 4.5 Test Full Webhook Flow (30 min)
- [ ] Create test issue on test repo
- [ ] Comment "@patchy is this code secure?"
- [ ] Verify: webhook received → processed → comment posted
- [ ] Check ngrok inspect UI for request/response details
- **Verify**: End-to-end webhook flow works

---

## Phase 5: Testing & Demo (2 hrs)

### 5.1 Create Test Repo (30 min)
- [ ] Create repo: `patchy-test-vulnerable`
- [ ] Add Python file with SQL injection:
  ```python
  query = f"SELECT * FROM users WHERE id = '{user_input}'"
  ```
- [ ] Add Python file with hardcoded secret:
  ```python
  API_KEY = "sk-1234567890abcdef"
  ```
- [ ] Add JS file with XSS:
  ```javascript
  document.innerHTML = userInput;
  ```
- [ ] Add Python file with insecure deserialization:
  ```python
  data = pickle.loads(request.data)
  ```
- [ ] Commit and push
- **Verify**: Semgrep finds all 4+ vulnerabilities

### 5.2 End-to-End Scan Test (30 min)
- [ ] Login to Patchy
- [ ] Scan test repo
- [ ] Verify: findings shown, fixes generated, PR created
- [ ] Check PR on GitHub: fixes are valid
- **Verify**: PR diff shows correct security fixes

### 5.3 End-to-End Issue Test (15 min)
- [ ] Create issue on test repo
- [ ] @mention Patchy
- [ ] Verify: bot responds with security analysis
- **Verify**: Comment is helpful and relevant

### 5.4 Edge Case Testing (15 min)
- [ ] Test: scan empty repo (should report 0 findings)
- [ ] Test: scan large repo (should reject > 100MB)
- [ ] Test: @mention without security context (should say "I help with security")
- [ ] Test: double-click scan button (should prevent duplicate scans)
- **Verify**: All edge cases handled gracefully

### 5.5 Record Demo (30 min)
- [ ] Record screen: login → dashboard → scan → PR
- [ ] Record screen: issue → @mention → bot response
- [ ] Take screenshots of key screens
- **Verify**: Demo video shows full flow clearly

---

## Phase 6: Documentation (1 hr)

### 6.1 Update README.md (30 min)
- [ ] Project description
- [ ] Setup instructions (exact commands)
- [ ] How to register GitHub App
- [ ] How to run locally
- [ ] Screenshots
- [ ] Architecture diagram

### 6.2 Code Documentation (30 min)
- [ ] Add docstrings to all functions in:
  - scan_pipeline.py
  - issue_responder.py
  - github_client.py
  - cerebras_client.py
  - storage.py
- [ ] Add inline comments for complex logic

---

## Quick Reference: File Creation Order

```
1. .env                    ← credentials
2. github_client.py        ← GitHub App auth
3. storage.py              ← JSON read/write
4. cerebras_client.py      ← LLM client
5. prompts.py              ← prompt templates
6. scan_pipeline.py        ← core pipeline
7. issue_responder.py      ← webhook handler
8. Update app.py           ← wire everything together
9. Update api.js           ← replace mock data
```

---

## Completed Tasks

_Move tasks here as completed_

- [x] Frontend: Landing page (index.html)
- [x] Frontend: Dashboard page (dashboard.html)
- [x] Frontend: Scan results page (scan_results.html)
- [x] Frontend: Scan detail page (scan_detail.html)
- [x] Frontend: All components (navbar, sidebar, repo_card, finding_card, loading)
- [x] Frontend: CSS (main.css)
- [x] Frontend: JS (api.js with mock data, main.js, dashboard.js)
- [x] Backend: Flask app skeleton (app.py with routes)
- [x] Backend: requirements.txt

---

## Blockers / Issues

| Blocker | Severity | Resolution |
|---------|----------|------------|
| GitHub App not yet registered | Critical | Phase 0.1 |
| Cerebras API key not obtained | Critical | Phase 0.2 |
| Semgrep not installed locally | Medium | `pip install semgrep` |
| No test repo with vulnerabilities | Medium | Phase 5.1 |

---

**Total Estimated Time**: 17 hours (~2.5 days)  
**Critical Path**: Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 5  
**Can Skip for MVP**: Phase 4 (webhooks), Phase 6 (docs)
