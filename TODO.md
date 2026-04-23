# Patchy - TODO List

> Track progress for 1-2 day build

**Last Updated**: 2026-04-23 18:33

---

## Day 1: Core Functionality

### Setup (2 hours)
- [ ] Initialize Flask project
- [ ] Install dependencies (Flask, PyGitHub, Semgrep, requests)
- [ ] Create `.env` file with API keys
- [ ] Setup project structure (agents/, templates/, static/)
- [ ] Test Flask server runs

### GitHub OAuth (2 hours)
- [ ] Register GitHub OAuth App
- [ ] Implement `/login` route
- [ ] Implement `/callback` route
- [ ] Store access token in session
- [ ] Test login flow works

### Dashboard & Repo Selection (2 hours)
- [ ] Create dashboard route
- [ ] Fetch user's repos from GitHub API
- [ ] Design dashboard page in Stitch
- [ ] Export and integrate HTML/CSS
- [ ] Display repos with "Scan" button
- [ ] Test repo list displays

### Agent 1: Scanner (1 hour)
- [ ] Install Semgrep
- [ ] Create `agents/scanner.py`
- [ ] Function to clone repo
- [ ] Function to run Semgrep
- [ ] Parse Semgrep JSON output
- [ ] Test on sample repo

### Agent 2: Fix Generator (1 hour)
- [ ] Create `agents/fix_generator.py`
- [ ] Create `utils/cerebras_client.py`
- [ ] Write prompt for fix generation
- [ ] Call Cerebras API
- [ ] Parse LLM response
- [ ] Test fix generation

---

## Day 2: PR Creation & Issue Interaction

### Agent 3: PR Creator (2 hours)
- [ ] Create `agents/pr_creator.py`
- [ ] Function to create branch
- [ ] Function to commit fixes
- [ ] Function to push branch
- [ ] Function to create PR via GitHub API
- [ ] Test PR creation

### Scan Flow Integration (1 hour)
- [ ] Create `/scan` POST endpoint
- [ ] Chain agents: Scanner → Fix Generator → PR Creator
- [ ] Add loading state UI
- [ ] Store scan results in `scans.json`
- [ ] Test end-to-end scan flow

### GitHub Webhook Setup (1 hour)
- [ ] Create GitHub App
- [ ] Configure webhook URL
- [ ] Add webhook secret to `.env`
- [ ] Create `/webhook/issues` endpoint
- [ ] Verify webhook signature
- [ ] Test webhook receives events

### Agent 4: Issue Responder (1 hour)
- [ ] Create `agents/issue_responder.py`
- [ ] Detect @mentions in issue comments
- [ ] Read issue context
- [ ] Generate response with Cerebras
- [ ] Post comment via GitHub API
- [ ] Test issue interaction

### UI Polish (2 hours)
- [ ] Design scan results page in Stitch
- [ ] Export and integrate
- [ ] Add TailwindCSS styling
- [ ] Add loading spinners
- [ ] Add error messages
- [ ] Add success notifications
- [ ] Test responsive design

---

## Testing & Demo

### Testing (1 hour)
- [ ] Create test repo with vulnerabilities
- [ ] Test full scan flow
- [ ] Test issue interaction
- [ ] Test error handling
- [ ] Fix any bugs

### Demo Preparation (1 hour)
- [ ] Record demo video
- [ ] Take screenshots
- [ ] Write README.md
- [ ] Deploy to Render/Railway (optional)
- [ ] Prepare presentation

---

## Documentation

### Code Documentation
- [ ] Add docstrings to all functions
- [ ] Add comments for complex logic
- [ ] Update TECHNICAL_SPEC.md with any changes

### User Documentation
- [ ] Write setup instructions in README
- [ ] Document environment variables
- [ ] Add usage examples
- [ ] Add troubleshooting section

---

## Optional Enhancements (If Time Permits)

- [ ] Add scan history page
- [ ] Add filtering/search for repos
- [ ] Add dark/light mode toggle
- [ ] Add email notifications
- [ ] Add rate limiting
- [ ] Add error logging
- [ ] Add analytics/metrics

---

## Completed Tasks

_Tasks will be moved here as they are completed_

---

## Blockers / Issues

_Track any blockers or issues here_

---

## Notes

- Keep console logs for debugging
- Test each agent independently before integration
- Use ngrok for local webhook testing
- Commit frequently to Git

---

**Total Estimated Time**: 16 hours (2 days)
**Priority**: Complete Day 1 tasks first, Day 2 is bonus
