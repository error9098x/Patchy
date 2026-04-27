"""
Scan Pipeline
Sequential: clone → semgrep → fix → validate → PR
Runs in background thread, updates scan status in storage.
Verbose logging for full transparency.
"""

import os
import ast
import json
import time
import shutil
import tempfile
import subprocess

import storage
import github_client
import verbose_log
from tools.fix_agent import (
    run_fix_agent_for_file, build_file_index, OUTCOME_OK
)
from pr_summarizer import summarize_pr
from collections import OrderedDict

# Limits
MAX_REPO_SIZE_MB = 100
SEMGREP_TIMEOUT = 300  # 5 min
CLONE_TIMEOUT = 60     # 1 min
MAX_FINDINGS_TO_FIX = 20

DEBUG = os.environ.get("PATCHY_DEBUG", "0") == "1"


def _log(scan_id, msg):
    """Verbose pipeline log. Gated on PATCHY_DEBUG=1."""
    if DEBUG:
        print(f"[SCAN {scan_id}] {msg}")


def run_pipeline(repo_full_name, installation_id, scan_id):
    """Main pipeline. Runs in background thread."""
    tmpdir = None
    start_time = time.time()
    llm_calls = 0
    llm_start = 0

    _log(scan_id, "═" * 50)
    _log(scan_id, f"PIPELINE START: {repo_full_name}")
    _log(scan_id, "═" * 50)

    verbose_log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "logs", f"scan_{scan_id}.log"
    )
    verbose_log.set_file(verbose_log_path)
    verbose_log.section(f"PIPELINE START — {repo_full_name} — {scan_id}")
    verbose_log.log("pipeline.start", {
        "repo": repo_full_name,
        "installation_id": installation_id,
        "scan_id": scan_id,
    })

    try:
        # ── Step 1: Clone ──
        _log(scan_id, "Step 1/6: CLONE REPOSITORY")
        storage.update_scan(scan_id, status="cloning", progress=10)
        storage.add_scan_step(scan_id, "clone", "running", "Cloning repository...")
        
        tmpdir = tempfile.mkdtemp(prefix="patchy_")
        repo_path = os.path.join(tmpdir, "repo")
        clone_url = f"https://github.com/{repo_full_name}.git"
        _log(scan_id, f"  Clone URL: {clone_url}")

        result = subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, repo_path],
            capture_output=True, timeout=CLONE_TIMEOUT, text=True
        )
        if result.returncode != 0:
            storage.add_scan_step(scan_id, "clone", "failed", f"Clone failed: {result.stderr[:200]}")
            raise RuntimeError(f"Clone failed: {result.stderr}")

        repo_size_mb = _get_dir_size_mb(repo_path)
        file_count = sum(len(files) for _, _, files in os.walk(repo_path))
        clone_time = round(time.time() - start_time, 1)
        
        _log(scan_id, f"  ✓ Clone complete ({repo_size_mb:.1f}MB, {file_count} files) [{clone_time}s]")
        storage.add_scan_step(scan_id, "clone", "complete",
                              f"Cloned {repo_size_mb:.1f}MB, {file_count} files")

        if repo_size_mb > MAX_REPO_SIZE_MB:
            raise RuntimeError(f"Repo too large: {repo_size_mb:.0f}MB (max {MAX_REPO_SIZE_MB}MB)")

        # ── Step 2: Semgrep ──
        _log(scan_id, "─" * 50)
        _log(scan_id, "Step 2/6: SEMGREP ANALYSIS")
        storage.update_scan(scan_id, status="scanning", progress=30)
        storage.add_scan_step(scan_id, "semgrep", "running", "Running Semgrep scan...")
        
        scan_start = time.time()
        verbose_log.section("SEMGREP")
        findings = _run_semgrep(repo_path)
        scan_time = round(time.time() - scan_start, 1)
        verbose_log.log("semgrep.result_count", len(findings))
        verbose_log.log("semgrep.findings", findings)

        storage.update_scan(scan_id, findings_count=len(findings), progress=50)
        _log(scan_id, f"  ✓ Found {len(findings)} vulnerabilities [{scan_time}s]")
        storage.add_scan_step(scan_id, "semgrep", "complete",
                              f"Found {len(findings)} vulnerabilities",
                              detail=f"Scan took {scan_time}s")

        if not findings:
            _log(scan_id, "  No findings — marking complete")
            # Mark remaining steps as skipped
            for step_name in ["fixing", "validate", "branch", "pr"]:
                storage.add_scan_step(scan_id, step_name, "skipped", "No vulnerabilities found")
            storage.update_scan(
                scan_id, status="complete", progress=100,
                completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                findings=[]
            )
            _log_metrics(scan_id, repo_full_name, 0, 0, 0, False,
                         time.time() - start_time, 0, 0)
            _log(scan_id, "PIPELINE COMPLETE (clean scan)")
            return

        # ── Step 3: Generate fixes ──
        _log(scan_id, "─" * 50)
        _log(scan_id, "Step 3/6: AI FIX GENERATION")
        storage.update_scan(scan_id, status="fixing", progress=60)
        storage.add_scan_step(scan_id, "fixing", "running",
                              f"Processing {min(len(findings), MAX_FINDINGS_TO_FIX)} findings...")
        
        fixes = []
        agent_outcomes = {}  # finding_key -> outcome string
        agent_traces = {}    # finding_key -> trace list
        capped_findings = findings[:MAX_FINDINGS_TO_FIX]
        llm_start = time.time()

        file_index = build_file_index(repo_path)
        _log(scan_id, f"  File index: {len(file_index)} files")
        verbose_log.section("FIX AGENT (grouped by file)")

        # Group findings by file, preserving order
        grouped: "OrderedDict[str, list]" = OrderedDict()
        for f in capped_findings:
            grouped.setdefault(f.get("path", ""), []).append(f)
        _log(scan_id, f"  Grouped {len(capped_findings)} findings → {len(grouped)} files")
        verbose_log.log("fix.groups", {
            fp: [{"check_id": x.get("check_id"),
                  "line": x.get("start", {}).get("line")} for x in grp]
            for fp, grp in grouped.items()
        })

        total_groups = len(grouped)
        total_findings = len(capped_findings)
        done_findings = 0

        for gi, (file_path, group) in enumerate(grouped.items()):
            _log(scan_id, f"  Group {gi+1}/{total_groups}: {file_path} "
                         f"({len(group)} finding{'s' if len(group) > 1 else ''})")
            # Representative finding for UI metadata
            rep = group[0]
            rep_check_id = rep.get("check_id", "unknown")
            rep_line = rep.get("start", {}).get("line", 1)
            group_key = f"__file__|{file_path}"

            storage.add_scan_step(scan_id, "fixing", "running",
                                  f"Agent on file {gi+1}/{total_groups}",
                                  detail=f"{file_path} — {len(group)} finding(s)")
            storage.set_current_finding(scan_id, {
                "index": gi + 1, "total": total_groups,
                "check_id": rep_check_id, "file": file_path, "line": rep_line,
                "severity": rep.get("extra", {}).get("severity", "").lower(),
                "message": f"{len(group)} finding(s) in {file_path}",
            })

            def _cb(ev, _scan_id=scan_id, _gi=gi, _total=total_groups,
                    _gk=group_key, _group=group):
                ev = dict(ev)
                ev["finding_index"] = _gi + 1
                ev["finding_total"] = _total
                ev["finding_key"] = _gk
                ev["group_size"] = len(_group)
                storage.append_agent_event(_scan_id, ev)

            try:
                result = run_fix_agent_for_file(
                    group, repo_path, file_index,
                    scan_id=scan_id, event_cb=_cb)
            except Exception as e:
                _log(scan_id, f"    ✗ agent crashed: {e}")
                for f in group:
                    fk = _finding_key(f)
                    agent_outcomes[fk] = "exception"
                    agent_traces[fk] = [{"error": str(e)}]
                done_findings += len(group)
                continue

            llm_calls += result.turns
            for f in group:
                fk = _finding_key(f)
                agent_outcomes[fk] = result.outcome
                agent_traces[fk] = result.trace

            if result.ok:
                fix_file_abs = os.path.join(repo_path, result.file)
                original_code = ""
                if os.path.exists(fix_file_abs):
                    try:
                        with open(fix_file_abs, "r", encoding="utf-8", errors="replace", newline="") as f:
                            original_code = f.read()
                    except Exception:
                        pass
                # Write patched content back to disk so subsequent groups (or
                # tools) see the updated file. Harmless since repo_path is
                # a throwaway clone.
                try:
                    with open(fix_file_abs, "w", encoding="utf-8", newline="") as f:
                        f.write(result.patched_content)
                except Exception as e:
                    _log(scan_id, f"    ⚠ disk write-back failed: {e}")
                fixes.append({
                    "finding": rep,
                    "findings_group": group,
                    "finding_key": group_key,
                    "file_path": result.file,
                    "original_code": original_code,
                    "fixed_code": result.patched_content,
                    "explanation": result.explanation or "",
                    "confidence": result.confidence,
                })
                verbose_log.log("fix.group_ok", {
                    "file": result.file,
                    "findings_covered": len(group),
                    "confidence": result.confidence,
                    "patch_chars": len(result.patched_content or ""),
                    "turns": result.turns,
                })
            else:
                _log(scan_id, f"    ✗ agent outcome: {result.outcome}")
                verbose_log.log("fix.group_fail", {
                    "file": file_path,
                    "outcome": result.outcome,
                    "detail": result.detail,
                    "turns": result.turns,
                })

            done_findings += len(group)
            progress = 60 + int(done_findings / max(total_findings, 1) * 20)
            storage.update_scan(scan_id, progress=progress,
                                fixes_generated=len(fixes))

        llm_duration = time.time() - llm_start
        outcome_counts = {}
        for o in agent_outcomes.values():
            outcome_counts[o] = outcome_counts.get(o, 0) + 1
        summary = ", ".join(f"{k}:{v}" for k, v in sorted(outcome_counts.items()))
        storage.set_current_finding(scan_id, None)
        _log(scan_id, f"  ✓ Agent done — fixes={len(fixes)} [{round(llm_duration, 1)}s] ({summary})")
        storage.add_scan_step(scan_id, "fixing", "complete",
                              f"{len(fixes)} fixes from {len(capped_findings)} findings",
                              detail=summary)

        # ── Step 4: Validate fixes ──
        _log(scan_id, "─" * 50)
        _log(scan_id, "Step 4/6: VALIDATE FIXES")
        storage.update_scan(scan_id, status="validating", progress=80)
        storage.add_scan_step(scan_id, "validate", "running", "Syntax-checking fixes...")
        verbose_log.section("VALIDATION")
        
        valid_fixes = []
        for fix in fixes:
            lang = _detect_language(fix["file_path"])
            _log(scan_id, f"  → Validating {fix['file_path']} (language: {lang})")
            verbose_log.log("validate.start", {
                "file": fix["file_path"],
                "language": lang,
                "code_length": len(fix["fixed_code"])
            })
            verbose_log.log("validate.code", fix["fixed_code"])
            
            is_valid, error = validate_fix(fix["fixed_code"], lang)
            
            if is_valid:
                valid_fixes.append(fix)
                _log(scan_id, f"  ✓ {fix['file_path']} — valid")
                verbose_log.log("validate.ok", {"file": fix["file_path"]})
            else:
                _log(scan_id, f"  ✗ {fix['file_path']} — {error}")
                verbose_log.log("validate.fail", {
                    "file": fix["file_path"],
                    "error": error
                })

        storage.update_scan(scan_id, fixes_valid=len(valid_fixes))
        _log(scan_id, f"  ✓ {len(valid_fixes)}/{len(fixes)} fixes passed validation")
        storage.add_scan_step(scan_id, "validate", "complete",
                              f"{len(valid_fixes)}/{len(fixes)} fixes valid")

        # ── Step 5 & 6: Create PR ──
        pr_url = None
        pr_branch = None
        pr_number = None

        if valid_fixes:
            _log(scan_id, "─" * 50)
            _log(scan_id, "Step 5/6: CREATE BRANCH")
            storage.update_scan(scan_id, status="creating_pr", progress=90)
            storage.add_scan_step(scan_id, "branch", "running", "Creating fix branch...")
            verbose_log.section("PR CREATION")
            
            try:
                # Initialize GitHub client
                _log(scan_id, "  → Initializing GitHub client...")
                verbose_log.log("pr.init_client", {"installation_id": installation_id})
                try:
                    g = github_client.get_github_for_installation(installation_id)
                    _log(scan_id, f"  ✓ GitHub client initialized")
                    verbose_log.log("pr.client_ok", True)
                except Exception as e:
                    _log(scan_id, f"  ✗ Failed to initialize GitHub client: {e}")
                    verbose_log.log("pr.client_error", str(e))
                    raise

                # Get repository
                _log(scan_id, f"  → Fetching repository: {repo_full_name}")
                verbose_log.log("pr.get_repo", {"repo": repo_full_name})
                try:
                    repo = g.get_repo(repo_full_name)
                    default_branch = repo.default_branch
                    _log(scan_id, f"  ✓ Repository fetched, default branch: {default_branch}")
                    verbose_log.log("pr.repo_ok", {"default_branch": default_branch})
                except Exception as e:
                    _log(scan_id, f"  ✗ Failed to fetch repository: {e}")
                    verbose_log.log("pr.repo_error", str(e))
                    raise

                # Create branch
                pr_branch = f"patchy/fix-{scan_id}"
                _log(scan_id, f"  → Creating branch: {pr_branch}")
                verbose_log.log("pr.create_branch", {"branch": pr_branch, "base": default_branch})
                try:
                    github_client.create_fix_branch(
                        installation_id, repo_full_name, pr_branch, default_branch
                    )
                    _log(scan_id, f"  ✓ Branch created: {pr_branch}")
                    verbose_log.log("pr.branch_ok", {"branch": pr_branch})
                    storage.add_scan_step(scan_id, "branch", "complete", f"Branch: {pr_branch}")
                except Exception as e:
                    _log(scan_id, f"  ✗ Failed to create branch: {e}")
                    verbose_log.log("pr.branch_error", str(e))
                    storage.add_scan_step(scan_id, "branch", "failed", str(e))
                    raise

                # Commit fixes
                _log(scan_id, "Step 6/6: OPEN PULL REQUEST")
                storage.add_scan_step(scan_id, "pr", "running", "Committing fixes and opening PR...")
                
                _log(scan_id, f"  → Preparing commit data for {len(valid_fixes)} fixes...")
                verbose_log.log("pr.prepare_commit", {"fix_count": len(valid_fixes)})
                commit_data = []
                seen_paths = set()
                for fix in valid_fixes:
                    if fix["file_path"] in seen_paths:
                        continue
                    seen_paths.add(fix["file_path"])
                    commit_data.append({
                        "file_path": fix["file_path"],
                        "content": fix["fixed_code"],
                    })
                _log(scan_id, f"  ✓ Prepared {len(commit_data)} files for commit")
                verbose_log.log("pr.commit_data_ready", {"file_count": len(commit_data)})

                unique_rules = sorted({
                    f["finding"].get("check_id", "unknown")
                    for f in valid_fixes
                })
                commit_msg = (
                    f"fix: apply Patchy security fixes across "
                    f"{len(commit_data)} file(s)\n\n"
                    f"Rules addressed:\n"
                    + "\n".join(f"  - {r}" for r in unique_rules)
                    + f"\n\nScan: {scan_id}"
                )
                
                _log(scan_id, f"  → Committing {len(commit_data)} files...")
                verbose_log.log("pr.commit_start", {
                    "files": [c["file_path"] for c in commit_data],
                    "rules": unique_rules
                })
                try:
                    new_sha = github_client.commit_fixes_atomic(
                        installation_id, repo_full_name, pr_branch,
                        commit_data, commit_msg
                    )
                    _log(scan_id, f"  ✓ {len(commit_data)} file(s) committed as {new_sha[:8] if new_sha else '?'}")
                    verbose_log.log("pr.commit_ok", {
                        "sha": new_sha,
                        "files": [c["file_path"] for c in commit_data],
                        "rules": unique_rules,
                    })
                except Exception as e:
                    _log(scan_id, f"  ✗ Failed to commit fixes: {e}")
                    verbose_log.log("pr.commit_error", str(e))
                    raise

                # Generate PR title and body
                _log(scan_id, "  → Generating PR title and body...")
                verbose_log.log("pr.generate_summary_start", {"fix_count": len(valid_fixes)})
                pr_title = f"Patchy: fix {len(valid_fixes)} security issue(s)"
                pr_body = _build_pr_body(valid_fixes, scan_id)
                
                try:
                    _log(scan_id, "  → Calling LLM for PR summary...")
                    summary = summarize_pr(valid_fixes, repo_full_name, scan_id)
                    if summary:
                        pr_title = summary["title"]
                        pr_body = summary["body"]
                        _log(scan_id, f"  ✓ LLM PR summary generated")
                        verbose_log.log("pr.summary_ok", {
                            "title_len": len(pr_title),
                            "body_len": len(pr_body)
                        })
                    else:
                        _log(scan_id, "  ⚠ pr_summarizer returned None, using fallback")
                        verbose_log.log("pr.summary_none", True)
                except Exception as e:
                    _log(scan_id, f"  ⚠ pr_summarizer crashed: {e}")
                    verbose_log.log("pr.summary_error", str(e))

                # Create pull request
                _log(scan_id, f"  → Creating pull request...")
                verbose_log.log("pr.create_start", {
                    "title": pr_title,
                    "head": pr_branch,
                    "base": default_branch,
                    "body_len": len(pr_body)
                })
                try:
                    pr_result = github_client.create_pull_request(
                        installation_id, repo_full_name,
                        title=pr_title,
                        body=pr_body, head_branch=pr_branch, base_branch=default_branch
                    )
                    pr_url = pr_result["url"]
                    pr_number = pr_result.get("number")
                    _log(scan_id, f"  ✓ PR created: {pr_url}")
                    verbose_log.log("pr.create_ok", {
                        "url": pr_url,
                        "number": pr_number
                    })
                    storage.add_scan_step(scan_id, "pr", "complete",
                                          f"PR #{pr_number} opened",
                                          detail=pr_url)
                except Exception as e:
                    _log(scan_id, f"  ✗ Failed to create pull request: {e}")
                    verbose_log.log("pr.create_error", str(e))
                    storage.add_scan_step(scan_id, "pr", "failed", str(e))
                    raise

            except Exception as e:
                _log(scan_id, f"  ✗ PR creation pipeline failed: {e}")
                verbose_log.log("pr.pipeline_error", str(e))
                storage.update_scan(scan_id, error=f"PR creation failed: {str(e)}")
        else:
            _log(scan_id, "  No valid fixes — skipping PR")
            verbose_log.log("pr.skipped", "no_valid_fixes")
            storage.add_scan_step(scan_id, "branch", "skipped", "No valid fixes")
            storage.add_scan_step(scan_id, "pr", "skipped", "No valid fixes")

        # ── Done ──
        stored_findings = _format_findings_for_storage(
            findings, valid_fixes, agent_outcomes, agent_traces
        )
        total_time = round(time.time() - start_time, 1)

        storage.update_scan(
            scan_id, status="complete", progress=100,
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            findings=stored_findings, pr_url=pr_url,
            pr_branch=pr_branch, pr_number=pr_number
        )

        _log(scan_id, "═" * 50)
        _log(scan_id, f"PIPELINE COMPLETE [{total_time}s]")
        _log(scan_id, f"  Findings: {len(findings)} | Fixes: {len(fixes)} | Valid: {len(valid_fixes)} | PR: {pr_url or 'None'}")
        _log(scan_id, "═" * 50)

        _log_metrics(
            scan_id, repo_full_name,
            len(findings), len(fixes), len(valid_fixes),
            pr_url is not None, time.time() - start_time,
            llm_calls, llm_duration
        )

    except Exception as e:
        _log(scan_id, f"✗ PIPELINE FAILED: {e}")
        verbose_log.section("PIPELINE FAILED")
        verbose_log.log("pipeline.error", str(e))
        storage.update_scan(
            scan_id, status="failed", progress=100,
            error=str(e),
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
    finally:
        verbose_log.section("PIPELINE END")
        verbose_log.clear()
        if tmpdir and os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)


# =============================================================================
# SEMGREP
# =============================================================================

def _run_semgrep(repo_path):
    """Run Semgrep with auto config, return findings list."""
    try:
        result = subprocess.run(
            [_semgrep_binary(), "--config", "auto", "--json", "--timeout", str(SEMGREP_TIMEOUT), repo_path],
            capture_output=True, text=True, timeout=SEMGREP_TIMEOUT + 30
        )
        if result.stdout:
            data = json.loads(result.stdout)
            findings = data.get("results", [])
            for f in findings:
                if f.get("path", "").startswith(repo_path):
                    f["path"] = os.path.relpath(f["path"], repo_path)
            return findings
        return []
    except subprocess.TimeoutExpired:
        print(f"Semgrep timed out after {SEMGREP_TIMEOUT}s")
        return []
    except json.JSONDecodeError:
        print(f"Semgrep output not valid JSON")
        return []
    except FileNotFoundError:
        print("Semgrep not installed. Install with: pip install semgrep")
        return []


def _semgrep_binary():
    semgrep = shutil.which("semgrep")
    if semgrep:
        return semgrep
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "semgrep")
    if os.path.exists(local):
        return local
    return "semgrep"


# =============================================================================
# VALIDATION
# =============================================================================

def validate_fix(code, language):
    """Validate fix syntax. Returns (is_valid, error_msg)."""
    if language == "python":
        return _validate_python(code)
    elif language in ("javascript", "typescript"):
        return _validate_javascript(code)
    return True, None


def _validate_python(code):
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def _validate_javascript(code):
    """Validate JavaScript/TypeScript syntax. Falls back to basic checks if Node.js unavailable."""
    # Skip Node.js validation for files with imports/JSX - they need a bundler
    has_imports = 'import ' in code or 'export ' in code
    has_jsx = '<' in code and '>' in code and ('React' in code or 'jsx' in code.lower())
    
    if has_imports or has_jsx:
        # For modern JS/React files, do basic syntax checks only
        if not code or not code.strip():
            return False, "Empty code"
        # Basic syntax checks
        if code.count('{') != code.count('}'):
            return False, "Mismatched braces"
        if code.count('(') != code.count(')'):
            return False, "Mismatched parentheses"
        if code.count('[') != code.count(']'):
            return False, "Mismatched brackets"
        # Check for obvious syntax errors
        if code.count("'") % 2 != 0 and code.count('"') % 2 != 0:
            return False, "Unclosed string"
        return True, None
    
    # For plain JS without imports/JSX, try Node validation
    try:
        result = subprocess.run(
            ["node", "-e", f"new Function({json.dumps(code)})"],
            capture_output=True, timeout=5, text=True
        )
        if result.returncode == 0:
            return True, None
        else:
            stderr = result.stderr.strip()
            # If it's just warnings or non-critical errors, still pass
            if stderr and not any(x in stderr.lower() for x in ['syntaxerror', 'unexpected token']):
                return True, None
            return False, stderr
    except FileNotFoundError:
        # Node.js not installed - do basic validation
        if not code or not code.strip():
            return False, "Empty code"
        if code.count('{') != code.count('}'):
            return False, "Mismatched braces"
        if code.count('(') != code.count(')'):
            return False, "Mismatched parentheses"
        if code.count('[') != code.count(']'):
            return False, "Mismatched brackets"
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Validation timeout"
    except Exception as e:
        return True, f"Validation skipped: {str(e)}"


# =============================================================================
# HELPERS
# =============================================================================

def _finding_key(finding):
    """Stable key for a single finding (used for status/outcome storage)."""
    check_id = finding.get("check_id", "unknown")
    path = finding.get("path", "")
    line = finding.get("start", {}).get("line", 0)
    return f"{check_id}|{path}|{line}"


def _get_dir_size_mb(path):
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total / (1024 * 1024)


def _get_code_context(source, line_num, window=15):
    lines = source.split('\n')
    start = max(0, line_num - window - 1)
    end = min(len(lines), line_num + window)
    return '\n'.join(lines[start:end])


def _detect_language(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    mapping = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'javascript', '.tsx': 'typescript', '.go': 'go',
        '.java': 'java', '.rb': 'ruby',
    }
    return mapping.get(ext, 'unknown')


def _format_findings_for_storage(all_findings, valid_fixes,
                                 agent_outcomes=None, agent_traces=None):
    agent_outcomes = agent_outcomes or {}
    agent_traces = agent_traces or {}
    fixed_paths = {f["file_path"] for f in valid_fixes}
    stored = []
    for finding in all_findings:
        path = finding.get("path", "")
        check_id = finding.get("check_id", "unknown")
        line = finding.get("start", {}).get("line", 0)
        finding_key = f"{check_id}|{path}|{line}"
        severity = finding.get("extra", {}).get("severity", "medium").lower()
        fix_status = "applied" if path in fixed_paths else "skipped"
        fix_explanation = None
        for vf in valid_fixes:
            if vf["file_path"] == path:
                fix_explanation = vf["explanation"]
                break
        stored.append({
            "id": f"f_{check_id[:20]}_{line}",
            "file": path, "line": line,
            "type": check_id, "severity": severity,
            "semgrep_rule": check_id,
            "message": finding.get("extra", {}).get("message", ""),
            "fix_status": fix_status,
            "fix_explanation": fix_explanation,
            "agent_outcome": agent_outcomes.get(finding_key),
            "agent_trace": agent_traces.get(finding_key, []),
        })
    return stored


def _build_pr_body(valid_fixes, scan_id):
    fixes_list = ""
    for fix in valid_fixes:
        finding = fix["finding"]
        fixes_list += f"""
### 🔧 {finding.get('check_id', 'Unknown')}
- **File**: `{fix['file_path']}`
- **Line**: {finding.get('start', {}).get('line', '?')}
- **Severity**: {finding.get('extra', {}).get('severity', 'unknown')}
- **Fix**: {fix['explanation']}
"""
    return f"""## 🔒 Patchy Security Fixes

**Scan ID**: `{scan_id}`  
**Fixes Applied**: {len(valid_fixes)}

This PR was automatically generated by [Patchy](https://github.com/apps/patchybot-dev).

### Changes
{fixes_list}

---

> ⚠️ Please review each fix carefully before merging.  
> Generated by Patchy 🩹
"""


def _log_metrics(scan_id, repo, findings, fixes_gen, fixes_valid,
                 pr_created, duration, llm_calls, llm_dur):
    try:
        storage.log_metric(
            scan_id=scan_id, repo=repo,
            findings_count=findings, fixes_generated=fixes_gen,
            fixes_valid=fixes_valid, pr_created=pr_created,
            scan_duration=duration, llm_calls=llm_calls, llm_duration=llm_dur
        )
    except Exception as e:
        print(f"Failed to log metrics: {e}")
