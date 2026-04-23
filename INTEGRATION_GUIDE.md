# Patchy - Backend Integration Guide

> API contract between frontend and backend for the multi-agent GitHub security bot.

---

## Authentication Flow

### GitHub OAuth

```
1. User clicks "Login with GitHub" → GET /login
2. Flask redirects to GitHub OAuth → https://github.com/login/oauth/authorize
3. GitHub redirects back → GET /callback?code=xxx
4. Flask exchanges code for token → POST https://github.com/login/oauth/access_token
5. Flask stores token in session and redirects to /dashboard
```

**Required OAuth Scopes**: `repo`, `user`

**Session Data Structure**:
```python
session['user'] = {
    'username': 'string',
    'avatar_url': 'string',
    'access_token': 'string',  # GitHub token
    'repos_count': int
}
```

---

## API Endpoints

### `GET /api/repos`

Fetch the authenticated user's GitHub repositories.

**Response**:
```json
[
    {
        "id": "repo_1",
        "name": "Core Authentication API",
        "full_name": "patchy-hq / core-api",
        "language": "Python",
        "last_scan": "2 hours ago",
        "status": "active",      // "active" | "inactive" | "error"
        "is_scanning": false,
        "contributors": [
            "https://avatars.githubusercontent.com/u/123"
        ]
    }
]
```

### `POST /api/scan`

Trigger a security scan on a repository.

**Request Body**:
```json
{
    "repo_id": "repo_1",
    "repo_name": "patchy-hq/core-api"
}
```

**Response**:
```json
{
    "scan_id": "scan_1234567890",
    "status": "scanning"
}
```

**Backend Flow**:
1. Clone repository to temp directory
2. **Agent 1 (Scanner)**: Run `semgrep --json` on codebase
3. **Agent 2 (Fix Generator)**: Send findings to Cerebras LLM for fixes
4. **Agent 3 (PR Creator)**: Create branch, apply fixes, open PR
5. Store results in `scans.json`

### `GET /api/scans`

Fetch scan history.

**Response**:
```json
[
    {
        "id": "scan_001",
        "repo": "api-gateway-service",
        "commit": "#a8c93bf",
        "timestamp": "12 mins ago",
        "run_time": "45s run time",
        "status": "critical",    // "critical" | "warning" | "clean"
        "findings": {
            "critical": 3,
            "medium": 5,
            "low": 12
        },
        "pr_url": "https://github.com/org/repo/pull/42"
    }
]
```

### `GET /api/scans/:id`

Fetch detailed scan results with findings.

**Response**:
```json
{
    "id": "scan_001",
    "repo": "backend-api-core",
    "commit": "a8f92b1",
    "timestamp": "2 mins ago",
    "author": "dev-team-alpha",
    "pr_url": "https://github.com/org/repo/pull/42",
    "summary": {
        "critical": 3,
        "high": 5,
        "moderate": 12
    },
    "findings": [
        {
            "id": "f_001",
            "severity": "critical",   // "critical" | "high" | "moderate"
            "type": "SQL Injection (SQLi)",
            "description": "User input directly concatenated into SQL query.",
            "file": "app/database/queries.py",
            "line": 42,
            "is_expanded": true,
            "fix_diff": [
                {
                    "type": "removed",
                    "line_num": 42,
                    "content": "query = f\"SELECT * FROM users WHERE ...\""
                },
                {
                    "type": "added",
                    "line_num": 42,
                    "content": "query = \"SELECT * FROM users WHERE username = %s\""
                }
            ]
        }
    ]
}
```

### `GET /api/scans/:id/status`

Poll for scan progress (for in-progress scans).

**Response**:
```json
{
    "status": "scanning",    // "scanning" | "complete" | "failed"
    "progress": 50,          // Percentage 0-100
    "current_step": "Running security scan"
}
```

---

## Webhook

### `POST /webhook/issues`

GitHub sends this when a user comments on an issue.

**Verification**: Validate `X-Hub-Signature-256` header using `GITHUB_WEBHOOK_SECRET`.

**Expected Payload** (from GitHub):
```json
{
    "action": "created",
    "comment": {
        "body": "@patchy analyze this vulnerability"
    },
    "issue": {
        "number": 5,
        "title": "Security concern in login flow",
        "body": "I think there might be an issue..."
    },
    "repository": {
        "full_name": "org/repo"
    }
}
```

**Backend Flow**:
1. Verify webhook signature
2. Check if `@patchy` is mentioned in comment body
3. **Agent 4 (Issue Responder)**: Send issue context to Cerebras LLM
4. Post LLM response as comment via GitHub API

---

## Data Storage

All scan data is stored in `scans.json` in the project root:

```json
{
    "scans": [
        {
            "id": "scan_123",
            "repo": "user/repo",
            "commit": "abc123",
            "findings": [...],
            "pr_url": "https://...",
            "timestamp": "2026-04-23T18:00:00"
        }
    ]
}
```

---

## Frontend Integration Points

All backend integration points in the frontend code are marked with:
- `// BACKEND:` comments in JavaScript
- `<!-- BACKEND: -->` comments in HTML templates
- `# BACKEND:` comments in Python

Search for these markers to find all integration points.

---

## Development Workflow

1. Frontend runs independently with mock data (no backend needed)
2. Backend developer implements API endpoints matching this contract
3. Replace mock data in `static/js/api.js` with real `fetch()` calls
4. Remove `MOCK_DATA` object from `api.js`
5. Test integration end-to-end
