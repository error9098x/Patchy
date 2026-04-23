# Testing Plan

> What to test, how, expected results, verification commands.

---

## 1. Unit Tests (per module)

### 1.1 storage.py
| Test | Input | Expected | Command |
|------|-------|----------|---------|
| Save scan | scan dict | Written to scans.json | `python3 -c "from storage import save_scan; save_scan({...})"` |
| Get scans | — | Returns list | `python3 -c "from storage import get_scans; print(get_scans())"` |
| Get scan by ID | scan_id | Returns scan or None | Same |
| Concurrent writes | 2 threads writing | No corruption | Threading test script |
| Empty file | — | Returns empty list | Delete scans.json, call get_scans |

### 1.2 cerebras_client.py
| Test | Input | Expected | Command |
|------|-------|----------|---------|
| Basic call | "Say hello" | Non-empty response | `python3 -c "from cerebras_client import call_cerebras; print(call_cerebras('system', 'hello'))"` |
| Retry on failure | Invalid API key | Raises after 3 attempts | Mock or use bad key |
| Timeout | Very long prompt | Raises within 30s | Stress test |

### 1.3 scan_pipeline.py
| Test | Input | Expected | Command |
|------|-------|----------|---------|
| Clone repo | public repo URL | Files in tmpdir | `python3 -c "..."` |
| Clone too-large repo | 200MB repo | Raises ValueError | — |
| Run semgrep | cloned dir | JSON with findings | Check results structure |
| Generate fix | SQL injection finding | Valid Python code | ast.parse succeeds |
| Create PR | fixes list | PR URL returned | Check GitHub |

### 1.4 github_client.py
| Test | Input | Expected | Command |
|------|-------|----------|---------|
| Generate JWT | App ID + key | Valid JWT string | Decode and check claims |
| Get installation token | Installation ID | Token string | Print token[:10] |
| List repos | Token | Array of repos | Print repo names |

---

## 2. Integration Tests

### 2.1 Full Scan Pipeline
```bash
# Start Flask
python app.py &

# Login (browser)
open http://localhost:5000/login

# Trigger scan via curl
curl -X POST http://localhost:5000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_name": "YOUR_USER/patchy-test-vulnerable"}' \
  -b cookies.txt

# Poll status
watch -n 3 'curl -s http://localhost:5000/api/scans/SCAN_ID/status -b cookies.txt'
```

**Expected**: Status progresses: cloning → scanning → fixing → creating_pr → complete

### 2.2 Webhook Flow
```bash
# Start ngrok
ngrok http 5000

# Go to GitHub test repo → Issues → New Issue
# Title: "Security concern"
# Comment: "@patchy check this"

# Check Flask logs for webhook receipt
# Check issue for bot comment
```

### 2.3 Frontend Integration
| Page | Test | Expected |
|------|------|----------|
| Landing | Click Login | Redirects to GitHub |
| Dashboard | After login | Shows real repos |
| Dashboard | Click Scan | Progress indicator appears |
| Dashboard | Scan complete | Success notification + PR link |
| Scan History | After scan | New scan entry appears |
| Scan Detail | Click entry | Shows findings with diffs |

---

## 3. Test Data

### 3.1 Test Repository: `patchy-test-vulnerable`

Create with these files:

**`vulnerable_app.py`**:
```python
import pickle
import sqlite3

def get_user(username):
    conn = sqlite3.connect('db.sqlite')
    # SQL Injection - Semgrep should catch this
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return conn.execute(query).fetchone()

# Hardcoded secret - Semgrep should catch this  
API_KEY = "sk-proj-1234567890abcdefghijklmnop"
DATABASE_PASSWORD = "super_secret_password_123"

def load_data(raw_bytes):
    # Insecure deserialization - Semgrep should catch this
    return pickle.loads(raw_bytes)
```

**`templates/profile.html`**:
```html
<h1>Profile</h1>
<!-- XSS - Semgrep should catch this -->
<p>Welcome, {{ user_input | safe }}</p>
<div>{{ comment | safe }}</div>
```

**`config.py`**:
```python
import os
import hashlib

# Weak hashing - Semgrep should catch this
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# Debug mode in production
DEBUG = True
SECRET_KEY = "not-a-secret"
```

**Expected Semgrep findings**: 6-8 vulnerabilities

---

## 4. Edge Cases

| Scenario | Expected Behavior |
|----------|------------------|
| Empty repo (no code files) | "No vulnerabilities found" |
| Repo > 100MB | Error: "Repository too large" |
| Repo with no supported languages | Scan completes, 0 findings |
| Semgrep timeout (>5 min) | Error: "Scan timed out" |
| Cerebras API down | Error after 3 retries |
| Invalid GitHub token | Redirect to login |
| Double-click Scan button | Prevent duplicate, show "already scanning" |
| Bot @mentioned with no context | "I'm a security bot — ask about security" |

---

## 5. Verification Checklist

### Before Demo
- [ ] Login flow works end-to-end
- [ ] Dashboard shows real repos
- [ ] Scan completes on test repo
- [ ] PR created with valid fixes
- [ ] Scan history shows completed scans
- [ ] Scan detail shows findings with diffs
- [ ] Webhook receives events
- [ ] Bot responds to @mentions
- [ ] Error states display correctly
- [ ] No console errors in browser
- [ ] No Python tracebacks in Flask logs

### Performance
- [ ] Scan completes in < 3 minutes for test repo
- [ ] Dashboard loads in < 2 seconds
- [ ] API responses < 500ms (except scan trigger)
