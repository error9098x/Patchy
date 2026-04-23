# Patchy - Technical Specification (MVP)

> Multi-Agent GitHub Security Bot - College Project

## 1. Project Overview

**Name**: Patchy  
**Type**: Web app with GitHub integration  
**Purpose**: Scan repos for vulnerabilities, create PRs, and respond to issues  
**Timeline**: 1-2 days

### What It Does
1. User logs in with GitHub
2. User selects a repo to scan
3. Tool scans repo and creates PR with fixes
4. User can @mention bot in any issue
5. Bot analyzes issue and gives suggestions in comments

### Evolution from SentryAgent
- **SentryAgent**: Smart contract security (CLI tool)
- **Patchy**: General application security (Web app + GitHub bot)
- **Core Innovation**: Hybrid tool-LLM multi-agent architecture

---

## 2. Core Features

### Feature 1: GitHub Login
- OAuth login with GitHub
- Show user's repos
- Let user select which repo to scan

### Feature 2: Automated Scanning
- User clicks "Scan" button
- Tool runs Semgrep on selected repo
- Creates PR with fixes automatically

### Feature 3: Issue Interaction
- User @mentions bot in any issue (e.g., "@patchy check this")
- Bot reads issue description
- Bot comments with suggestions/analysis
- No PR creation for issues, just helpful comments

---

## 3. Multi-Agent System

### Agent 1: Scanner Agent
- Runs Semgrep on repo
- Finds vulnerabilities
- Returns list of issues

### Agent 2: Fix Generator Agent
- Takes vulnerabilities from Scanner
- Uses LLM to generate fixes
- Returns fixed code

### Agent 3: PR Creator Agent
- Creates new branch
- Commits fixes
- Opens PR with description

### Agent 4: Issue Responder Agent
- Triggered when @mentioned in issue
- Reads issue context
- Uses LLM to generate helpful response
- Posts comment

---

## 4. System Flow

### Flow 1: Manual Scan
```
User logs in with GitHub
    ↓
User selects repo from list
    ↓
User clicks "Scan" button
    ↓
Agent 1: Scanner (Semgrep)
    ↓
Agent 2: Fix Generator (Cerebras LLM)
    ↓
Agent 3: PR Creator (PyGitHub)
    ↓
PR created on GitHub
```

### Flow 2: Issue Interaction
```
User @mentions bot in issue
    ↓
GitHub webhook triggers
    ↓
Agent 4: Issue Responder
    ↓
Read issue context
    ↓
Generate response (Cerebras LLM)
    ↓
Post comment on issue
```

---

## 5. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | Flask | Simple, fast setup |
| Frontend | HTML + TailwindCSS | No build step needed |
| GitHub Auth | GitHub OAuth | Built-in login |
| GitHub API | PyGitHub | Easy repo access |
| Scanner | Semgrep | Free, accurate |
| LLM | Cerebras (qwen-3-235b) | Fast, cheap, 20k tokens |
| Storage | JSON file | No database needed |
| Hosting | ngrok (dev) / Render (prod) | Free tier |

### Why Cerebras?
- **Fast**: Faster inference than OpenAI
- **Cheap**: Lower cost per token
- **High token limit**: 20k max_tokens
- **Good for code**: Qwen model is strong at code generation

---

## 5. Data Storage (JSON File)

```json
{
  "scans": [
    {
      "id": "scan_123",
      "repo": "user/repo",
      "commit": "abc123",
      "findings": [
        {
          "file": "app.py",
          "line": 42,
          "issue": "SQL injection",
          "fix": "Use parameterized queries"
        }
      ],
      "pr_url": "https://github.com/user/repo/pull/5",
      "timestamp": "2026-04-23T18:00:00"
    }
  ]
}
```

---

## 6. API Endpoints

```python
# Authentication
GET  /                      # Landing page
GET  /login                 # Redirect to GitHub OAuth
GET  /callback              # OAuth callback

# Dashboard
GET  /dashboard             # Show user's repos
POST /scan                  # Trigger scan on selected repo
GET  /scans                 # View scan history

# Webhooks
POST /webhook/issues        # Handle @mentions in issues
```

---

## 7. Implementation Plan (1-2 Days)

### Day 1: Core Functionality (8 hours)

**Hour 1-2: Setup & Auth**
- [ ] Create Flask app
- [ ] Setup GitHub OAuth
- [ ] Login/logout flow
- [ ] Store access token in session

**Hour 3-4: Dashboard & Repo Selection**
- [ ] Fetch user's repos from GitHub API
- [ ] Display repos in simple HTML page
- [ ] Add "Scan" button for each repo

**Hour 5-6: Agent 1 & 2 (Scanner + Fix Generator)**
- [ ] Install Semgrep
- [ ] Run Semgrep on selected repo
- [ ] Send findings to Cerebras LLM
- [ ] Get fixed code back

**Hour 7-8: Agent 3 (PR Creator)**
- [ ] Clone repo locally
- [ ] Create new branch
- [ ] Apply fixes
- [ ] Commit and push
- [ ] Create PR via GitHub API

### Day 2: Issue Interaction & Polish (6 hours)

**Hour 1-2: Webhook Setup**
- [ ] Create GitHub App
- [ ] Setup webhook for issue comments
- [ ] Verify webhook signature

**Hour 3-4: Agent 4 (Issue Responder)**
- [ ] Detect @mentions in issues
- [ ] Read issue context
- [ ] Generate response with Cerebras
- [ ] Post comment via GitHub API

**Hour 5-6: UI Polish & Testing**
- [ ] Add TailwindCSS styling
- [ ] Show scan history
- [ ] Test on real repo
- [ ] Record demo video

---

## 8. File Structure

```
patchy/
├── app.py                    # Flask app + routes
├── agents/
│   ├── scanner.py           # Agent 1: Semgrep scanner
│   ├── fix_generator.py     # Agent 2: LLM fix generator
│   ├── pr_creator.py        # Agent 3: PR creator
│   └── issue_responder.py   # Agent 4: Issue responder
├── utils/
│   ├── github_client.py     # GitHub API wrapper
│   └── cerebras_client.py   # Cerebras API wrapper
├── templates/
│   ├── index.html           # Landing page
│   ├── dashboard.html       # Repo selection
│   └── scans.html           # Scan history
├── static/
│   └── style.css            # TailwindCSS
├── scans.json               # Scan history storage
├── requirements.txt         # Dependencies
└── .env                     # API keys
```

---

## 9. Environment Variables

```bash
# GitHub OAuth
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Cerebras API
CEREBRAS_API_KEY=your_api_key

# Flask
SECRET_KEY=your_secret_key
```

---

## 10. Cerebras Integration

```python
import requests

def call_cerebras(prompt, code):
    response = requests.post(
        'https://api.cerebras.ai/v1/chat/completions',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {CEREBRAS_API_KEY}'
        },
        json={
            'model': 'qwen-3-235b-a22b-instruct-2507',
            'stream': False,
            'max_tokens': 20000,
            'temperature': 0.7,
            'top_p': 0.8,
            'messages': [
                {'role': 'system', 'content': 'You are a security expert.'},
                {'role': 'user', 'content': f'{prompt}\n\nCode:\n{code}'}
            ]
        }
    )
    return response.json()['choices'][0]['message']['content']
```

---

## 11. Demo Flow

### Part 1: Manual Scan
1. Go to patchy.dev
2. Click "Login with GitHub"
3. Select a test repo
4. Click "Scan"
5. Show console logs (Semgrep running)
6. Show PR created on GitHub
7. Show fixes in PR

### Part 2: Issue Interaction
1. Go to GitHub repo
2. Create new issue: "How can I improve security?"
3. Comment: "@patchy analyze this"
4. Show webhook received
5. Show bot comment with suggestions

---

## 12. Dissertation Angle

**Research Question**: 
"How effective is a hybrid tool-LLM multi-agent system for automated vulnerability detection and remediation?"

**Evaluation**:
- Test on 10 repos with known vulnerabilities
- Measure:
  - Detection rate (did it find the vuln?)
  - Fix quality (does the fix work?)
  - Response quality (are issue comments helpful?)

**Comparison**:
- Semgrep alone (baseline)
- Semgrep + Cerebras LLM (our approach)
- Manual review (gold standard)

**Expected Results**:
- Hybrid approach finds 90%+ of known vulnerabilities
- LLM-generated fixes compile and work 70%+ of the time
- Issue responses are helpful 80%+ of the time

---

**Document Version**: 3.0 (Final MVP)  
**Last Updated**: 2026-04-23  
**Timeline**: 1-2 days  
**LLM**: Cerebras (qwen-3-235b)
