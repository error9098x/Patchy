# Integration Checklist

> Step-by-step guide connecting frontend ↔ backend ↔ GitHub ↔ Cerebras

---

## 1. Frontend → Backend API

| Frontend Call (api.js) | Backend Route (app.py) | Status |
|----------------------|----------------------|--------|
| `API.fetchRepos()` | `GET /api/repos` | Mock → Wire to `github_client.get_user_repos()` |
| `API.scanRepo(id, name)` | `POST /api/scan` | Mock → Wire to `scan_pipeline.run()` |
| `API.fetchScanHistory()` | `GET /api/scans` | Mock → Wire to `storage.get_scans()` |
| `API.fetchScanDetails(id)` | `GET /api/scans/:id` | Mock → Wire to `storage.get_scan()` |
| `API.fetchScanStatus(id)` | `GET /api/scans/:id/status` | Mock → Wire to `storage.get_scan().status` |

### Integration Steps:
1. Build each backend function independently
2. Test with `curl` or Postman
3. Uncomment real `fetch()` in api.js, comment out mock
4. Test in browser
5. Verify data format matches MOCK_DATA structure

### Common Issues:
- **CORS**: Not needed — same-origin (Flask serves frontend)
- **JSON format mismatch**: Backend returns `{status, data}`, frontend expects raw array
  - Fix: unwrap in api.js `_fetch()` → `return response.data`
- **Auth token missing**: Session cookie handles auth (automatic)

---

## 2. Backend → GitHub API

| Operation | Endpoint | Library |
|-----------|----------|---------|
| Get user info | `GET /user` | requests |
| List repos | `GET /installation/repositories` | PyGithub |
| Get file content | `GET /repos/:owner/:repo/contents/:path` | PyGithub |
| Create branch | `POST /repos/:owner/:repo/git/refs` | PyGithub |
| Update file | `PUT /repos/:owner/:repo/contents/:path` | PyGithub |
| Create PR | `POST /repos/:owner/:repo/pulls` | PyGithub |
| Post comment | `POST /repos/:owner/:repo/issues/:number/comments` | PyGithub |
| Clone repo | `git clone --depth 1` | subprocess |

### Auth Flow:
```
1. User clicks Login
2. → Redirect to github.com/login/oauth/authorize
3. ← GitHub redirects to /callback?code=xxx
4. → Exchange code for user token (POST github.com/login/oauth/access_token)
5. → Get app installation ID (GET /user/installations)
6. → Get installation token (POST /app/installations/:id/access_tokens)
7. → Store in session: {user_token, installation_token, installation_id}
```

### Token Refresh:
Installation tokens expire after 1 hour. Before each API call:
```python
def get_valid_token(session):
    if token_expired(session['token_expires_at']):
        session['installation_token'] = refresh_installation_token(session['installation_id'])
        session['token_expires_at'] = datetime.now() + timedelta(hours=1)
    return session['installation_token']
```

---

## 3. Backend → Cerebras API

| Call | Endpoint | Prompt Template |
|------|----------|----------------|
| Generate fix | `POST /v1/chat/completions` | `SECURITY_FIX_SYSTEM` + `SECURITY_FIX_USER` |
| Issue response | `POST /v1/chat/completions` | `ISSUE_RESPONSE_SYSTEM` + `ISSUE_RESPONSE_USER` |

### Integration Test:
```python
# Test Cerebras connection
from cerebras_client import call_cerebras
response = call_cerebras(
    "You are helpful.",
    "Say hello in exactly 3 words."
)
print(response)  # Should get 3-word response
```

### Common Issues:
- **Rate limit**: Cerebras has per-minute limits. Add 1s delay between calls.
- **Response parsing**: LLM sometimes wraps code in \`\`\`. Strip markdown fences.
- **Timeout**: Large prompts take longer. 30s timeout should suffice.

---

## 4. GitHub → Backend (Webhooks)

| Event | Trigger | Handler |
|-------|---------|---------|
| `issue_comment` | @mention in issue | `issue_responder.handle_issue_comment()` |

### Setup:
1. Start Flask: `python app.py`
2. Start ngrok: `ngrok http 5000`
3. Copy ngrok URL (e.g., `https://abc123.ngrok.io`)
4. Update GitHub App settings → Webhook URL → `https://abc123.ngrok.io/webhook`
5. Set webhook secret in GitHub App settings (same as `.env`)

### Verification:
```bash
# Check ngrok is receiving webhooks
# Open: http://127.0.0.1:4040 (ngrok inspect UI)
# Create issue comment with @patchy
# Should see POST /webhook in ngrok UI
```

### Signature Verification:
```python
import hmac, hashlib

def verify_webhook(request):
    signature = request.headers.get('X-Hub-Signature-256', '')
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        request.data,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

---

## 5. Backend → Local Tools

| Tool | Command | Notes |
|------|---------|-------|
| Git clone | `git clone --depth 1 <url> <dir>` | Use tmpdir, token in URL |
| Semgrep | `semgrep --config auto --json <dir>` | 5min timeout |

### Semgrep Output Format:
```json
{
  "results": [
    {
      "check_id": "python.lang.security.audit.raw-query",
      "path": "app.py",
      "start": {"line": 42, "col": 5},
      "end": {"line": 42, "col": 65},
      "extra": {
        "severity": "ERROR",
        "message": "User input in SQL query",
        "metadata": {"category": "security"}
      }
    }
  ]
}
```

Map Semgrep severity to Patchy severity:
- `ERROR` → `critical`
- `WARNING` → `medium`  
- `INFO` → `low`

---

## 6. Data Flow Diagram

```
User Browser          Flask Server           GitHub API          Cerebras API
    │                      │                     │                    │
    │──GET /dashboard─────→│                     │                    │
    │                      │──GET /repos────────→│                    │
    │                      │←─repo list──────────│                    │
    │←─render dashboard────│                     │                    │
    │                      │                     │                    │
    │──POST /api/scan─────→│                     │                    │
    │←─{scan_id}───────────│                     │                    │
    │                      │──git clone─────────→│                    │
    │                      │──semgrep────────────│                    │
    │──GET /status────────→│                     │                    │
    │←─{scanning}──────────│                     │                    │
    │                      │──fix prompt────────→│───────────────────→│
    │                      │←─fixed code─────────│←───────────────────│
    │                      │──create PR─────────→│                    │
    │──GET /status────────→│                     │                    │
    │←─{complete, pr_url}──│                     │                    │
```
