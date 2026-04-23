# Patchy - Technical Specification V2 (Improved)

> Multi-Agent GitHub Security Bot - College Project
> Supersedes: TECHNICAL_SPEC.md

## 1. Project Overview

**Name**: Patchy  
**Type**: Web app with GitHub integration  
**Purpose**: Scan repos for vulnerabilities, create PRs with fixes, respond to issues  
**Timeline**: 2-3 days (realistic)  
**Demo**: Local + ngrok

### What It Does
1. User installs GitHub App on selected repos
2. User selects repo to scan from dashboard
3. ScanPipeline: Semgrep → LLM fix → validate → PR
4. User can @mention bot in issues → bot comments with analysis

### Evolution from SentryAgent
- **SentryAgent**: Smart contract security (CLI)
- **Patchy**: General application security (Web + GitHub bot)
- **Core Innovation**: Hybrid tool-LLM pipeline with validation

---

## 2. Core Features

### Feature 1: GitHub App Authentication
- GitHub App installation flow (NOT OAuth App)
- User installs app → picks repos → redirect to callback
- App gets installation access token (expires in 1hr, auto-refreshed)
- Show user's installed repos on dashboard

### Feature 2: Scan Pipeline
- User clicks "Scan" on repo card
- Pipeline runs sequentially:
  1. **Clone**: Shallow clone to tmpdir (`--depth 1`)
  2. **Scan**: Semgrep `--config auto --json`
  3. **Fix**: Cerebras LLM generates fixes with structured prompt
  4. **Validate**: Syntax check fixes (ast.parse / node --check)
  5. **PR**: Create branch, commit valid fixes, open PR
- Frontend polls `/api/scans/:id/status` every 3s for progress
- Results saved to `scans.json` with filelock

### Feature 3: Issue Responder
- Webhook fires on `issue_comment` event
- Check if bot is @mentioned
- Read issue context (title, body, comments)
- Generate response with Cerebras (security-focused prompt)
- Post comment via GitHub API as app bot

---

## 3. Architecture

### Two Modules (Not Four Agents)

```
Module 1: ScanPipeline
┌─────────────────────────────────────────────────┐
│  clone_repo() → run_semgrep() → generate_fixes() │
│  → validate_fixes() → create_pr()               │
└─────────────────────────────────────────────────┘
Single function, sequential steps, tmpdir scoped.

Module 2: IssueResponder  
┌─────────────────────────────────────────────────┐
│  parse_webhook() → read_context() → llm_respond()│
│  → post_comment()                                │
└─────────────────────────────────────────────────┘
Webhook-triggered, independent, stateless.
```

### Why Not Four Agents?
Scanner, FixGenerator, and PRCreator are always sequential with shared state (cloned repo, findings list). Splitting them into separate "agents" creates unnecessary data passing overhead. One pipeline function is cleaner.

---

## 4. System Flow

### Flow 1: Scan Pipeline
```
User clicks "Scan Now" on repo card
    ↓
POST /api/scan { repo_name }
    ↓
Create scan record (status: "cloning")
    ↓
git clone --depth 1 to tmpdir
    ↓
Update status: "scanning"
    ↓
semgrep --config auto --json --timeout 300
    ↓
Update status: "fixing"
    ↓
For each finding:
    → Build structured prompt with code context
    → Call Cerebras (qwen-3-235b)
    → Validate fix (syntax check)
    → Keep only valid fixes
    ↓
Update status: "creating_pr"
    ↓
Create branch: patchy/fix-{scan_id}
Commit valid fixes
Open PR with summary description
    ↓
Update status: "complete"
Save to scans.json (with filelock)
Cleanup tmpdir
```

### Flow 2: Issue Response
```
@mention in issue comment
    ↓
GitHub sends POST /webhook
    ↓
Verify HMAC signature
    ↓
Parse event: extract issue title, body, comment
    ↓
Call Cerebras with issue-response prompt
    ↓
Post comment via GitHub API
```

### Frontend Polling (Flow 1)
```javascript
// Dashboard calls this after triggering scan
pollScanStatus(scanId) {
    setInterval(async () => {
        const { status, progress } = await API.fetchScanStatus(scanId);
        updateProgressUI(status); // cloning → scanning → fixing → creating_pr → complete
        if (status !== 'scanning' && status !== 'cloning' && ...) clearInterval();
    }, 3000);
}
```

---

## 5. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | Flask 3.1 | Simple, fast setup |
| Frontend | HTML + TailwindCSS + Vanilla JS | No build step |
| Auth | GitHub App | Handles auth + webhooks + API |
| GitHub API | PyGitHub 2.6 | Easy repo/PR access |
| Scanner | Semgrep | Free, accurate, JSON output |
| LLM | Cerebras (qwen-3-235b) | Fast, cheap, 20k tokens |
| Storage | JSON file + filelock | No database needed |
| Webhooks | ngrok (dev) | Free, easy tunnel |
| Demo | Local Flask server | No hosting constraints |

### Why Cerebras?
- **Fast**: ~1s inference for code fixes
- **Cheap**: Lower cost per token than OpenAI
- **High token limit**: 20k max_tokens
- **Good at code**: Qwen model handles code generation well

---

## 6. Data Storage

### scans.json (with filelock)
```json
{
  "scans": [
    {
      "id": "scan_1682345678",
      "repo": "user/repo",
      "commit": "abc123",
      "status": "complete",
      "started_at": "2026-04-23T18:00:00Z",
      "completed_at": "2026-04-23T18:01:30Z",
      "findings_count": 8,
      "fixes_generated": 6,
      "fixes_valid": 5,
      "findings": [
        {
          "id": "f_001",
          "file": "app.py",
          "line": 42,
          "type": "SQL Injection",
          "severity": "critical",
          "semgrep_rule": "python.lang.security.audit.raw-sql",
          "message": "User input in SQL query",
          "fix_status": "applied",
          "fix_code": "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
        }
      ],
      "pr_url": "https://github.com/user/repo/pull/5",
      "pr_branch": "patchy/fix-scan_1682345678"
    }
  ]
}
```

### metrics.json (for dissertation)
```json
{
  "scans": [
    {
      "repo": "user/repo",
      "timestamp": "2026-04-23T18:00:00Z",
      "findings_count": 8,
      "fixes_generated": 6,
      "fixes_valid": 5,
      "pr_created": true,
      "scan_duration_seconds": 45,
      "llm_calls": 8,
      "llm_duration_seconds": 12
    }
  ]
}
```

---

## 7. API Endpoints

### Page Routes
```python
GET  /                      # Landing page (public)
GET  /login                 # Start GitHub App install flow
GET  /callback              # GitHub App callback → store token
GET  /logout                # Clear session
GET  /dashboard             # Repo dashboard (auth required)
GET  /scans                 # Scan history (auth required)
GET  /scans/<scan_id>       # Scan detail (auth required)
```

### API Routes (JSON responses)
```python
GET  /api/repos             # List installed repos
POST /api/scan              # Trigger scan { repo_name }
GET  /api/scans             # Scan history list
GET  /api/scans/<id>        # Scan detail with findings
GET  /api/scans/<id>/status # Poll scan progress

# Response format (ALL endpoints):
# Success: { "status": "ok", "data": <payload> }
# Error:   { "status": "error", "code": "<ERROR_CODE>", "message": "<details>" }
```

### Webhook Route
```python
POST /webhook               # All GitHub App webhook events
# Verify X-Hub-Signature-256 header
# Handle: issue_comment (check for @mention)
```

### Error Codes
```
AUTH_REQUIRED     - No session / not logged in
AUTH_EXPIRED      - Token expired, re-login needed
REPO_NOT_FOUND    - Repo doesn't exist or no access
REPO_TOO_LARGE    - Exceeds 100MB limit
SCAN_TIMEOUT      - Semgrep exceeded 5min timeout
SCAN_FAILED       - Semgrep crashed or returned error
LLM_ERROR         - Cerebras API failed after 3 retries
GITHUB_API_ERROR  - GitHub API returned error
RATE_LIMITED      - Too many requests
SCAN_IN_PROGRESS  - Repo already being scanned
```

---

## 8. File Structure

```
patchy/
├── app.py                          # Flask routes + config
├── scan_pipeline.py                # Module 1: clone → scan → fix → validate → PR
├── issue_responder.py              # Module 2: webhook → analyze → comment
├── prompts.py                      # LLM prompt templates
├── github_client.py                # GitHub App auth + API wrapper
├── cerebras_client.py              # Cerebras API wrapper with retry
├── storage.py                      # JSON file R/W with filelock
├── templates/
│   ├── base.html                   # Base template with sidebar nav
│   ├── index.html                  # Landing page
│   ├── dashboard.html              # Repo dashboard
│   ├── scan_results.html           # Scan history
│   ├── scan_detail.html            # Individual scan detail
│   └── components/
│       ├── navbar.html             # Public navbar
│       ├── navbar_app.html         # Authenticated navbar
│       ├── sidebar.html            # Dashboard sidebar
│       ├── repo_card.html          # Repository card
│       ├── finding_card.html       # Security finding card
│       └── loading.html            # Loading/progress states
├── static/
│   ├── css/
│   │   └── main.css                # All styles (Stitch + custom)
│   └── js/
│       ├── api.js                  # API client + mock data
│       ├── main.js                 # Global JS (theme, nav)
│       └── dashboard.js            # Dashboard logic + polling
├── scans.json                      # Scan history storage
├── metrics.json                    # Dissertation metrics
├── requirements.txt                # Python dependencies
├── .env                            # API keys (not committed)
└── .gitignore                      # Ignore .env, scans.json, __pycache__
```

---

## 9. Environment Variables

```bash
# GitHub App (register at Settings > Developer Settings > GitHub Apps)
GITHUB_APP_ID=12345
GITHUB_APP_PRIVATE_KEY_PATH=./github-app-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GITHUB_CLIENT_ID=Iv1.abc123          # For OAuth-like user auth
GITHUB_CLIENT_SECRET=secret_xyz

# Cerebras API
CEREBRAS_API_KEY=your_api_key

# Flask
SECRET_KEY=generate-with-python-c-import-secrets-secrets.token_hex(32)
FLASK_ENV=development
```

---

## 10. LLM Prompt Templates

### Fix Generation Prompt
```python
SECURITY_FIX_SYSTEM = "You are a code security fixer. Return ONLY fixed code. No explanations."

SECURITY_FIX_USER = """Fix this vulnerability found by Semgrep.

RULES:
1. Return ONLY the fixed code, no markdown, no explanations
2. Preserve ALL original functionality
3. Fix ONLY the security issue
4. Maintain original style and indentation
5. Include any needed imports at the top

VULNERABILITY:
- Type: {vuln_type}
- Rule: {rule_id}
- Severity: {severity}
- Message: {message}

FILE: {file_path} (line {line_number})

ORIGINAL CODE:
{code_context}

FIXED CODE:"""
```

### Issue Response Prompt
```python
ISSUE_RESPONSE_SYSTEM = "You are Patchy, a GitHub security bot. Be concise, technical, helpful."

ISSUE_RESPONSE_USER = """Respond to this GitHub issue with security analysis.

RULES:
1. Be concise (max 300 words)
2. If security-related, give specific remediation
3. Use markdown formatting
4. If not security-related, say "I'm a security bot — I can help with security questions."

ISSUE: {title}
BODY:
{body}

COMMENT THAT MENTIONED YOU:
{comment}

Your response:"""
```

---

## 11. Cerebras Integration (with retry)

```python
import requests
import time

CEREBRAS_API_URL = 'https://api.cerebras.ai/v1/chat/completions'

def call_cerebras(system_prompt, user_prompt, max_retries=3):
    """Call Cerebras API with retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                CEREBRAS_API_URL,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {CEREBRAS_API_KEY}'
                },
                json={
                    'model': 'qwen-3-235b-a22b-instruct-2507',
                    'stream': False,
                    'max_tokens': 4000,  # Not 20k — fixes are small
                    'temperature': 0.2,  # Low temp for code — deterministic
                    'top_p': 0.9,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt}
                    ]
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']

        except (requests.RequestException, KeyError) as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise RuntimeError(f"Cerebras API failed after {max_retries} attempts: {e}")
```

**Key changes from original:**
- `temperature: 0.2` (not 0.7 — we want deterministic code fixes)
- `max_tokens: 4000` (not 20k — fixes are small, save cost)
- 30s timeout
- 3x retry with exponential backoff
- Explicit error handling

---

## 12. Fix Validation

```python
import ast
import subprocess

def validate_python_fix(code):
    """Check Python code is syntactically valid."""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def validate_javascript_fix(code):
    """Check JS code with Node."""
    try:
        result = subprocess.run(
            ['node', '-e', f'try {{ new Function({repr(code)}) }} catch(e) {{ process.exit(1) }}'],
            capture_output=True, timeout=5
        )
        return result.returncode == 0, result.stderr.decode() if result.returncode != 0 else None
    except Exception as e:
        return False, str(e)

VALIDATORS = {
    'python': validate_python_fix,
    'javascript': validate_javascript_fix,
    'typescript': validate_javascript_fix,
}

def validate_fix(code, language):
    """Validate fix for given language. Returns (is_valid, error_msg)."""
    validator = VALIDATORS.get(language.lower())
    if validator:
        return validator(code)
    return True, None  # Skip validation for unsupported languages
```

---

## 13. Scan Limits & Safety

```python
# Limits
MAX_REPO_SIZE_MB = 100          # Reject repos > 100MB
SEMGREP_TIMEOUT_SECONDS = 300   # 5 minute scan timeout
CLONE_TIMEOUT_SECONDS = 60      # 1 minute clone timeout
MAX_FINDINGS_TO_FIX = 20        # Don't fix more than 20 per scan
MAX_CONCURRENT_SCANS = 2        # Prevent resource exhaustion
LLM_TIMEOUT_SECONDS = 30        # Per-fix LLM timeout
```

---

## 14. Demo Flow

### Setup (once)
1. Register GitHub App at github.com/settings/apps
2. Install app on test repo `patchy-test-vulnerable`
3. Start Flask: `python app.py`
4. Start ngrok: `ngrok http 5000`
5. Update GitHub App webhook URL to ngrok URL

### Demo Part 1: Scan
1. Open localhost:5000
2. Click "Login with GitHub" → install app
3. See repos on dashboard
4. Click "Scan Now" on test repo
5. Watch progress: cloning → scanning → fixing → creating PR
6. Show PR on GitHub with fixes

### Demo Part 2: Issue Response
1. Go to test repo on GitHub
2. Create issue: "Is my authentication secure?"
3. Comment: "@patchy analyze this"
4. Show webhook received in Flask logs
5. Show bot comment with security analysis

---

## 15. Deployment Strategy

### Development vs Production

**Phase 1: Development (Current)**
- **GitHub App**: "Only on this account"
- **Hosting**: Local (localhost:5001)
- **Webhook**: ngrok tunnel
- **Purpose**: Testing and development
- **Users**: Just you

**Phase 2: Production (Future)**
- **GitHub App**: Create NEW app with "Any account" ✅
- **Hosting**: Railway with custom domain
- **Webhook**: Stable URL (https://patchy.app/webhook)
- **Purpose**: Public use
- **Users**: Anyone can install

### Why Two Apps?

**Development App**:
- Safe testing environment
- Break things without affecting users
- Debug on your repos only
- Use ngrok for local webhooks

**Production App**:
- Stable and monitored
- Professional domain
- Public marketplace
- Real users

### Production Checklist

Before creating production app:
- [ ] Code tested thoroughly on dev app
- [ ] Deployed to Railway with custom domain
- [ ] Webhook endpoint is reliable (not ngrok)
- [ ] Error handling and logging in place
- [ ] Rate limiting implemented
- [ ] Privacy policy and ToS ready
- [ ] Security review complete

### Production GitHub App Setup

1. **Create new app** (don't modify dev app)
2. **Name**: `Patchy` (official)
3. **Installation**: **"Any account"** ✅
4. **Webhook**: `https://patchy.app/webhook`
5. **Homepage**: `https://patchy.app`
6. **Same permissions** as dev app
7. **New credentials** → production .env

### Deployment Environments

```
Development:
- GitHub App: Patchy-Dev (only your account)
- URL: http://localhost:5001
- Webhook: https://abc123.ngrok.io/webhook
- .env: .env.development

Production:
- GitHub App: Patchy (any account)
- URL: https://patchy.app
- Webhook: https://patchy.app/webhook
- .env: .env.production
```

### Migration Path

1. **Week 1-2**: Build on dev app (localhost + ngrok)
2. **Week 3**: Deploy to Railway (still dev app)
3. **Week 4**: Test thoroughly
4. **Week 5**: Create production app
5. **Week 6**: Switch to production app
6. **Week 7+**: Keep dev app for testing new features

---

## 16. Dissertation Angle

**Research Question:**  
"How effective is a hybrid tool-LLM pipeline for automated vulnerability detection and remediation?"

**Evaluation (built into app via metrics.json):**

| Metric | How to Measure |
|--------|---------------|
| Detection rate | Semgrep findings vs known vulns in test repos |
| Fix validity | % of LLM fixes that pass syntax validation |
| Fix correctness | Manual review: does fix actually resolve vuln? |
| Response quality | Manual rating of issue comments (1-5 scale) |
| Pipeline speed | Total scan duration (logged automatically) |

**Test repos needed:** 5-10 repos with planted vulnerabilities across Python, JavaScript, and TypeScript.

**Comparison:**
1. Semgrep alone (baseline — finds but doesn't fix)
2. Semgrep + Cerebras (our approach — finds AND fixes)
3. Manual review (gold standard — human expert)

---

**Document Version**: 4.0 (V2 - Improved)  
**Last Updated**: 2026-04-23  
**Supersedes**: TECHNICAL_SPEC.md  
**Timeline**: 2-3 days  
**LLM**: Cerebras (qwen-3-235b)
