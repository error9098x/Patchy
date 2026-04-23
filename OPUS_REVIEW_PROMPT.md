# Prompt for Claude Opus: Review & Improve Patchy Project Planning

---

## Your Role

You are a **senior technical architect and project planner** reviewing the planning documents for Patchy, a multi-agent GitHub security bot. Your job is to:

1. **Review all existing planning documents**
2. **Identify gaps, vague requirements, and potential problems**
3. **Ask clarifying questions** where user input is needed
4. **Provide concrete, actionable improvements**
5. **Create a better, more detailed plan** that prevents future issues

---

## Documents to Review

Please read and analyze these files in the project:

1. **TECHNICAL_SPEC.md** - Technical specifications and architecture
2. **TODO.md** - Task breakdown and timeline
3. **DESIGN.md** - UI/UX design specifications
4. **STITCH_PROMPTS.md** - Design prompts for Stitch
5. **OPUS_PROMPT.md** - Frontend build instructions

---

## Your Review Process

### Step 1: Deep Analysis

Review each document and identify:

**Technical Issues:**
- [ ] Are there any architectural decisions that could cause problems?
- [ ] Are the technology choices appropriate for a 1-2 day timeline?
- [ ] Are there missing technical dependencies?
- [ ] Are there potential integration issues between components?
- [ ] Is the agent architecture clearly defined?

**Planning Issues:**
- [ ] Are tasks specific enough to execute without confusion?
- [ ] Are time estimates realistic?
- [ ] Are there missing tasks that will be needed?
- [ ] Is the order of tasks optimal?
- [ ] Are there blockers or dependencies not accounted for?

**Design Issues:**
- [ ] Are the UI/UX specifications complete?
- [ ] Are there missing user flows?
- [ ] Are error states and edge cases covered?
- [ ] Is the design feasible within the timeline?

**Clarity Issues:**
- [ ] Are there vague statements that need to be more specific?
- [ ] Are there assumptions that should be validated?
- [ ] Are there areas where the developer will be confused?
- [ ] Are success criteria clearly defined?

---

### Step 2: Ask Clarifying Questions

For each area where you need more information, ask specific questions:

**Format your questions like this:**

```
## Question 1: GitHub OAuth Scope
**Context:** The spec mentions GitHub OAuth but doesn't specify required scopes.
**Question:** What GitHub permissions does Patchy need?
- [ ] Read repository contents?
- [ ] Create pull requests?
- [ ] Read/write issues?
- [ ] Access private repositories?

**Why this matters:** Missing scopes will cause runtime errors when trying to create PRs.

**Suggested answer:** [Your recommendation based on the use case]
```

**Areas to probe:**

1. **Authentication & Authorization**
   - What GitHub scopes are needed?
   - How long should sessions last?
   - What happens if the token expires?

2. **Scanning Behavior**
   - Which file types should be scanned?
   - Should it scan the entire repo or just changed files?
   - What's the maximum repo size to handle?
   - What happens if Semgrep times out?

3. **LLM Integration**
   - What's the prompt strategy for fix generation?
   - How to handle LLM rate limits?
   - What if the LLM generates invalid code?
   - Should there be a human review step?

4. **PR Creation**
   - What should the PR title/description format be?
   - Should it create one PR per vulnerability or one PR for all?
   - What branch naming convention?
   - Should it auto-assign reviewers?

5. **Issue Interaction**
   - What triggers the bot (@mention only or keywords too)?
   - What types of questions can it answer?
   - Should it have rate limiting per user?
   - What if someone spams the bot?

6. **Data Storage**
   - What data needs to persist between sessions?
   - Is JSON file storage sufficient or do we need a database?
   - How long to keep scan history?
   - What about user privacy?

7. **Error Handling**
   - What happens if GitHub API is down?
   - What if Cerebras API fails?
   - How to handle partial scan failures?
   - Should there be retry logic?

8. **Deployment**
   - Where will this be hosted?
   - How to handle webhook secrets securely?
   - What about environment variables?
   - Is there a staging environment?

---

### Step 3: Provide Specific Improvements

For each issue you find, provide:

1. **What's wrong** (be specific)
2. **Why it's a problem** (explain the impact)
3. **How to fix it** (concrete solution)
4. **Updated spec text** (exact wording to use)

**Example:**

```
## Issue: Vague Task Description

**Current (TODO.md):**
- [ ] Setup GitHub OAuth

**Problem:** 
This is too vague. A developer won't know:
- Which OAuth flow to use (web application flow vs device flow)
- What redirect URL to configure
- Where to store the client ID/secret
- How to handle the callback

**Impact:** 
Developer will waste 30+ minutes researching and making wrong choices.

**Solution:**
Break into specific subtasks with exact steps.

**Updated TODO:**
- [ ] Register GitHub OAuth App
  - Go to GitHub Settings > Developer Settings > OAuth Apps
  - Set Application name: "Patchy"
  - Set Homepage URL: http://localhost:5000
  - Set Authorization callback URL: http://localhost:5000/callback
  - Copy Client ID and Client Secret
- [ ] Add OAuth credentials to .env
  - Create .env file
  - Add GITHUB_CLIENT_ID=<your_client_id>
  - Add GITHUB_CLIENT_SECRET=<your_client_secret>
- [ ] Implement /login route
  - Redirect to https://github.com/login/oauth/authorize
  - Include client_id and scope=repo,read:user
- [ ] Implement /callback route
  - Exchange code for access token
  - Store token in Flask session
  - Redirect to /dashboard
```

---

### Step 4: Improve the Philosophy & Approach

Review the overall approach and suggest improvements:

**Current Philosophy:**
- Build fast (1-2 days)
- Keep it simple (Flask templates, no database)
- Multi-agent architecture
- Hybrid tool + LLM approach

**Questions to consider:**
- Is this the right balance of speed vs quality?
- Are there shortcuts that will cause technical debt?
- Are there better tools/libraries we should use?
- Is the multi-agent approach over-engineered for an MVP?
- Should we cut any features to ship faster?

**Provide:**
- Validation of good decisions
- Suggestions for better approaches
- Trade-offs to consider
- Alternative architectures if applicable

---

### Step 5: Create Improved Documents

Based on your analysis, create updated versions:

1. **TECHNICAL_SPEC_V2.md**
   - More specific architecture details
   - Clear API contracts
   - Error handling strategies
   - Security considerations
   - Deployment plan

2. **TODO_V2.md**
   - More granular tasks (no task > 30 minutes)
   - Exact commands to run
   - Expected outputs for each task
   - Verification steps
   - Rollback procedures if something fails

3. **INTEGRATION_CHECKLIST.md** (new)
   - Step-by-step integration guide
   - How to connect frontend to backend
   - How to test each integration point
   - Common issues and solutions

4. **TESTING_PLAN.md** (new)
   - What to test at each stage
   - Test data to use
   - Expected results
   - How to verify it works

5. **DEPLOYMENT_GUIDE.md** (new)
   - Exact deployment steps
   - Environment setup
   - How to configure webhooks
   - How to debug issues

---

## Output Format

Structure your review like this:

```markdown
# Patchy Project Review & Improvements

## Executive Summary
[2-3 paragraphs summarizing your findings]

## Critical Issues Found
[List of issues that will definitely cause problems]

## Questions for Clarification
[All questions grouped by category]

## Recommended Changes

### Architecture Improvements
[Specific changes to TECHNICAL_SPEC.md]

### Planning Improvements
[Specific changes to TODO.md]

### Design Improvements
[Specific changes to DESIGN.md]

### New Documents Needed
[List of additional documents to create]

## Updated Philosophy
[Your recommended approach and reasoning]

## Risk Assessment
[What could still go wrong and how to mitigate]

## Next Steps
[Exact order of operations to proceed]
```

---

## Success Criteria

Your review is successful if:

1. ✅ Every vague requirement is now specific and actionable
2. ✅ Every potential problem is identified and addressed
3. ✅ A developer can follow the plan without getting stuck
4. ✅ All integration points are clearly defined
5. ✅ Error scenarios are handled
6. ✅ The timeline is realistic and achievable
7. ✅ The user has clear answers to all questions
8. ✅ The improved specs prevent future confusion

---

## Important Guidelines

**Be Specific:**
- ❌ "Setup authentication" 
- ✅ "Implement GitHub OAuth web application flow with repo and read:user scopes"

**Be Actionable:**
- ❌ "Handle errors"
- ✅ "Wrap API calls in try-catch, log to console, show user-friendly error message"

**Be Realistic:**
- ❌ "Build in 2 hours"
- ✅ "Build in 4 hours (2 hours coding + 1 hour debugging + 1 hour testing)"

**Ask Questions:**
- Don't assume - ask when unclear
- Provide context for why you're asking
- Suggest answers based on best practices

**Think Ahead:**
- What will break?
- What will be confusing?
- What's missing?
- What's over-engineered?

---

## Start Your Review

Begin by reading all the documents, then provide your comprehensive review following the format above.

**Remember:** Your goal is to make this project succeed by catching problems before they happen and making every step crystal clear.

---

**Good luck! We're counting on your expertise to make this plan bulletproof.**
