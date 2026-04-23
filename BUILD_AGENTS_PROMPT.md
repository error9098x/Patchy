# Build Patchy Agents - Natural Prompt for Opus

Hey Opus,

We need you to build the agent system for Patchy. You've already seen the specs and architecture docs. Now it's time to code.

---

## Our Philosophy

**Keep it simple**. This is a college project that needs to work in 1-2 days, not a production system.

**Write code like a good developer**:
- Clear and readable
- Minimal but complete
- Comments where needed
- No over-engineering
- If something can be done in 10 lines, don't use 50

**Think practically**:
- Does it work? Good.
- Is it clean? Good.
- Can someone understand it in 6 months? Good.
- That's all we need.

---

## What We Have

✅ NVIDIA API working (minimaxai/minimax-m2.7)  
✅ GitHub App configured  
✅ Flask running  
✅ Frontend done  
✅ All credentials in .env  

---

## What We Need You to Build

### 1. GitHub Client (`github_client.py`)
A simple wrapper around PyGithub that:
- Gets installation token using JWT
- Lists user's repos
- Creates PRs
- Posts comments

Just the functions we need. Nothing fancy.

### 2. Scanner Agent (`agents/scanner_agent.py`)
- Clone repo to temp directory
- Run Semgrep on it
- Parse the JSON output
- Return findings

That's it. Don't overthink it.

### 3. Fix Generator Agent (`agents/fix_agent.py`)
- Take a finding from Semgrep
- Send it to NVIDIA API with good prompt
- Get fixed code back
- Return it

Use the `tools/nvidia_client.py` we already have.

### 4. PR Creator Agent (`agents/pr_agent.py`)
- Take the fixes
- Create a branch
- Commit the changes
- Open a PR

Use the github_client we built.

### 5. Pipeline (`pipeline.py`)
- Run agents in sequence
- Handle errors gracefully
- Log progress
- Return results

Simple orchestration. No complex state machines.

### 6. Flask Routes (`app.py`)
Update the existing routes:
- `/login` - GitHub OAuth
- `/callback` - Handle OAuth callback
- `/dashboard` - Show repos
- `/api/scan` - Trigger scan
- `/webhook` - Handle GitHub webhooks

---

## How to Approach This

**Start simple**:
1. Build github_client first
2. Test it works
3. Build scanner agent
4. Test it works
5. Build fix agent
6. Test it works
7. Wire them together in pipeline
8. Add Flask routes
9. Test end-to-end

**Don't build everything at once**. Build one piece, make sure it works, move to next.

**Use what we have**:
- `tools/nvidia_client.py` for LLM calls
- PyGithub for GitHub API
- Semgrep for scanning
- Standard library for everything else

**No external dependencies** unless absolutely necessary.

---

## Code Style

```python
# Good - clear and simple
def scan_repo(repo_path):
    """Run Semgrep and return findings."""
    result = subprocess.run(['semgrep', '--json', repo_path], capture_output=True)
    findings = json.loads(result.stdout)
    return findings['results']

# Bad - over-engineered
class SemgrepScannerFactory:
    def __init__(self, config_manager, logger_factory):
        self.scanner = ScannerBuilder().with_config(config_manager).build()
    # ... 50 more lines
```

See the difference? Keep it like the first one.

---

## Error Handling

```python
# Good enough
try:
    result = do_something()
except Exception as e:
    print(f"Error: {e}")
    return None

# Don't need
try:
    result = do_something()
except SpecificError1 as e:
    handle_specific_case_1()
except SpecificError2 as e:
    handle_specific_case_2()
except SpecificError3 as e:
    handle_specific_case_3()
# ... etc
```

Catch the error, log it, move on. We're not building a bank.

---

## Testing

**Manual testing is fine**:
- Run the function
- Print the output
- Does it look right? Good.
- Does it work on a test repo? Good.

**No need for**:
- Unit tests (unless you want to)
- Integration tests
- Mocks and fixtures
- Test coverage reports

This is a demo. If it works when we run it, it works.

---

## What Success Looks Like

At the end, we should be able to:
1. Open http://localhost:5001
2. Click "Login with GitHub"
3. See our repos
4. Click "Scan" on a repo
5. Wait a minute
6. See a PR created with fixes

That's it. If that works, you've succeeded.

---

## Important Notes

**Use the existing code**:
- Don't rewrite `tools/nvidia_client.py`
- Don't rewrite the frontend
- Don't change the .env structure
- Build on what's there

**Follow the specs**:
- TECHNICAL_SPEC_V2.md has the architecture
- AGENT_WORKFLOW_PLAN.md has the agent details
- But if something in the spec seems overcomplicated, simplify it

**Ask if stuck**:
- If something's unclear, ask
- If you need a decision, ask
- If you're about to write 200 lines for something simple, ask

---

## Timeline

**Realistic estimate**: 3-4 hours of focused work

- GitHub client: 30 min
- Scanner agent: 30 min
- Fix agent: 30 min
- PR agent: 30 min
- Pipeline: 30 min
- Flask routes: 1 hour
- Testing & debugging: 1 hour

Take breaks. Don't rush. Quality over speed.

---

## Final Thoughts

You're a good developer. You know how to write clean code. You know when something is getting too complex.

Trust your instincts. If it feels like you're over-engineering, you probably are.

Build something that works, that's readable, and that we can demo tomorrow.

That's all we need.

---

**Ready? Let's build this thing.** 🚀

Start with `github_client.py` and let me know when it's done.
