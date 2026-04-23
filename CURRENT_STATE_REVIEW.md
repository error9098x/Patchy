# Patchy - Current State Review

**Date**: 2026-04-23 21:36  
**Reviewed by**: Kiro AI

---

## What's Been Done ✅

### 1. Planning & Documentation (Complete)
- ✅ **TECHNICAL_SPEC_V2.md** - Improved architecture (2 modules instead of 4 agents)
- ✅ **TODO_V2.md** - Granular tasks with exact commands (≤30 min each)
- ✅ **INTEGRATION_CHECKLIST.md** - Step-by-step integration guide
- ✅ **TESTING_PLAN.md** - Test strategy and evaluation
- ✅ **DEPLOYMENT_GUIDE.md** - Deployment instructions
- ✅ **BINARY_ANIMATION_PROMPT.md** - Binary grid animation spec

### 2. Frontend (Complete)
- ✅ **Landing page** with interactive binary grid background
- ✅ **Binary grid animation** - Mouse-reactive, twinkling bits, proper scrolling
- ✅ **Dashboard UI** - Repo cards, scan buttons (using mock data)
- ✅ **Scan results UI** - History and details pages
- ✅ **API client** (api.js) - All endpoints defined with mock data
- ✅ **Responsive design** - Works on mobile and desktop
- ✅ **TailwindCSS** - Styled with design system colors

### 3. Backend (Skeleton Only)
- ✅ **Flask app structure** - Routes defined but not implemented
- ✅ **Mock endpoints** - Return placeholder data
- ⚠️ **No real functionality** - Everything is stubbed

---

## What Needs to Be Built 🚧

### Phase 1: GitHub App Authentication (2 hours)
**Priority**: HIGH - Nothing works without this

**Tasks**:
1. Create `github_client.py`:
   - `get_installation_token(installation_id)` - Generate JWT, get token
   - `get_user_repos(installation_token)` - List repos
   - `create_pr(repo, branch, title, body)` - Create PR
   - `post_comment(repo, issue_number, body)` - Post comment

2. Update `app.py` routes:
   - `/login` - Redirect to GitHub OAuth
   - `/callback` - Exchange code, get installation, store in session
   - `/logout` - Clear session
   - Add `@login_required` decorator

3. Test:
   - Login flow works
   - Session persists
   - Can list repos

**Files to create**:
- `github_client.py`

**Files to modify**:
- `app.py` (login/callback/logout routes)

---

### Phase 2: Scan Pipeline (4 hours)
**Priority**: HIGH - Core functionality

**Tasks**:
1. Create `scan_pipeline.py`:
   - `run_scan(repo_name, installation_token)`:
     - Clone repo to tmpdir
     - Run Semgrep
     - Parse findings
     - Generate fixes with Cerebras
     - Validate fixes (syntax check)
     - Create PR with valid fixes
     - Return scan result

2. Create `cerebras_client.py`:
   - `generate_fix(finding, code_context)` - Call Cerebras API
   - `respond_to_issue(issue_context)` - Generate issue response

3. Create `storage.py`:
   - `save_scan(scan_data)` - Write to scans.json with filelock
   - `get_scan(scan_id)` - Read scan by ID
   - `get_all_scans()` - List all scans

4. Update `app.py`:
   - `POST /api/scan` - Trigger scan pipeline
   - `GET /api/scans/:id/status` - Poll scan status
   - `GET /api/repos` - List user's repos

5. Test:
   - Scan completes end-to-end
   - PR is created on GitHub
   - Scan saved to scans.json

**Files to create**:
- `scan_pipeline.py`
- `cerebras_client.py`
- `storage.py`

**Files to modify**:
- `app.py` (scan endpoints)

---

### Phase 3: Issue Responder (1 hour)
**Priority**: MEDIUM - Nice to have

**Tasks**:
1. Create `issue_responder.py`:
   - `handle_issue_comment(webhook_data)`:
     - Parse webhook
     - Check for @mention
     - Read issue context
     - Generate response with Cerebras
     - Post comment

2. Update `app.py`:
   - `POST /webhook/issues` - Verify signature, call handler

3. Setup ngrok:
   - `ngrok http 5001`
   - Update GitHub App webhook URL

4. Test:
   - @mention bot in issue
   - Bot responds with helpful comment

**Files to create**:
- `issue_responder.py`

**Files to modify**:
- `app.py` (webhook endpoint)

---

### Phase 4: Frontend Integration (1 hour)
**Priority**: HIGH - Connect UI to backend

**Tasks**:
1. Update `static/js/api.js`:
   - Replace MOCK_DATA with real fetch() calls
   - Test each endpoint

2. Test:
   - Dashboard loads real repos
   - Scan button triggers real scan
   - Progress updates in real-time
   - Scan history shows real data

**Files to modify**:
- `static/js/api.js`

---

## Current Issues 🐛

### 1. Binary Grid Animation
- ✅ **FIXED**: Grid now scrolls with page (position: absolute)
- ✅ **FIXED**: Mouse tracking accounts for scroll (+ window.scrollY)
- ✅ **FIXED**: Canvas stops at footer (uses footer.offsetTop)
- ✅ **FIXED**: Twinkling effect added (10/25 probability)
- ✅ **FIXED**: Brightness increased (0.5 default, 2.5 hover)

### 2. Backend
- ⚠️ **NOT STARTED**: No GitHub authentication
- ⚠️ **NOT STARTED**: No scan pipeline
- ⚠️ **NOT STARTED**: No Cerebras integration
- ⚠️ **NOT STARTED**: No data persistence

---

## Architecture Changes from V1 → V2

### Key Improvements by Opus:

1. **Simplified Agent Architecture**:
   - ❌ Old: 4 separate agents (Scanner, Validator, FixGen, PRCreator)
   - ✅ New: 2 modules (ScanPipeline, IssueResponder)
   - **Why**: Sequential steps with shared state don't need separate agents

2. **GitHub App instead of OAuth App**:
   - ❌ Old: OAuth App (user tokens only)
   - ✅ New: GitHub App (installation tokens, webhooks)
   - **Why**: Better permissions, webhook support, bot identity

3. **Validation Step Added**:
   - ✅ New: Syntax check fixes before committing
   - **Why**: Prevent broken code in PRs

4. **Granular TODO**:
   - ❌ Old: Vague tasks ("Setup OAuth")
   - ✅ New: Exact commands, ≤30 min tasks
   - **Why**: No confusion, clear progress

5. **Realistic Timeline**:
   - ❌ Old: 1-2 days (unrealistic)
   - ✅ New: 2-3 days (17 hours total)
   - **Why**: Accounts for debugging, testing

---

## Next Steps (Priority Order)

### Immediate (Today):
1. ✅ Review all updated specs (this document)
2. 🔲 Register GitHub App (15 min)
3. 🔲 Get Cerebras API key (5 min)
4. 🔲 Create .env file (5 min)
5. 🔲 Install dependencies (5 min)

### Tomorrow (Day 1):
1. 🔲 Build GitHub authentication (2 hours)
2. 🔲 Build scan pipeline (4 hours)
3. 🔲 Test end-to-end scan (1 hour)

### Day After (Day 2):
1. 🔲 Build issue responder (1 hour)
2. 🔲 Connect frontend to backend (1 hour)
3. 🔲 Test everything (2 hours)
4. 🔲 Record demo video (1 hour)

---

## Files Structure

```
patchy/
├── app.py                      # Flask app (routes only, no logic)
├── github_client.py            # GitHub API wrapper (TO BUILD)
├── scan_pipeline.py            # Scan logic (TO BUILD)
├── cerebras_client.py          # LLM calls (TO BUILD)
├── issue_responder.py          # Webhook handler (TO BUILD)
├── storage.py                  # JSON file operations (TO BUILD)
├── requirements.txt            # Dependencies
├── .env                        # Secrets (TO CREATE)
├── github-app-key.pem          # GitHub App private key (TO DOWNLOAD)
├── scans.json                  # Scan history (auto-created)
├── static/
│   ├── css/main.css           # ✅ Done
│   └── js/
│       ├── matrix.js          # ✅ Done (binary grid)
│       ├── api.js             # ⚠️ Has mock data, needs real fetch
│       ├── main.js            # ✅ Done
│       └── dashboard.js       # ✅ Done
└── templates/
    ├── index.html             # ✅ Done (landing page)
    ├── dashboard.html         # ✅ Done
    ├── scan_results.html      # ✅ Done
    └── scan_detail.html       # ✅ Done
```

---

## Questions to Answer Before Building

1. **GitHub App Setup**:
   - ✅ Do you have a GitHub account? (Yes, error9098x)
   - 🔲 Ready to register GitHub App now?

2. **Cerebras API**:
   - 🔲 Do you have Cerebras account?
   - 🔲 Have API key?

3. **Testing**:
   - 🔲 Do you have a test repo with known vulnerabilities?
   - 🔲 Or should we create one?

4. **Scope**:
   - 🔲 Do you want issue responder (@patchy) or just scanning?
   - 🔲 Is 2-3 days timeline acceptable?

---

## Summary

**Frontend**: ✅ 100% Complete  
**Backend**: ⚠️ 0% Complete (skeleton only)  
**Specs**: ✅ 100% Complete (improved by Opus)  

**Next Action**: Start Phase 1 (GitHub App Auth) - 2 hours of work

**Estimated Time to Working Demo**: 8-10 hours of focused coding

---

**Ready to start building?** Let me know and I'll begin with Phase 1!
