"""
Patchy PR Reviewer
Report-only PR security review for @mention workflows.
"""

import json
import os
import shutil
import subprocess
import tempfile

import github_client
from scan_pipeline import SEMGREP_TIMEOUT
from tools.nvidia_client import chat


REVIEW_KEYWORDS = (
    "review", "scan", "analyze", "analyse", "audit", "check this pr",
    "security review", "run semgrep", "look for vulnerabilities"
)


def is_review_request(comment_body):
    """Return True when a mention is asking Patchy to review/scan the PR."""
    body = (comment_body or "").lower()
    return any(k in body for k in REVIEW_KEYWORDS)


def review_pull_request(installation_id, repo_full_name, pull_number, comment_body):
    """Run a report-only Semgrep + LLM PR review and return markdown."""
    tmpdir = None
    try:
        pr_context = github_client.get_pull_request_context(
            installation_id, repo_full_name, pull_number
        )
        changed_files = pr_context.get("changed_files", [])
        changed_paths = [f["filename"] for f in changed_files if f.get("filename")]
        changed_ranges = _changed_line_ranges(changed_files)

        tmpdir = tempfile.mkdtemp(prefix="patchy_pr_review_")
        repo_path = os.path.join(tmpdir, "repo")
        _clone_pr(installation_id, repo_full_name, pull_number, repo_path)

        findings = _run_semgrep_on_paths(repo_path, changed_paths)
        classified = _classify_findings(findings, changed_ranges)

        return _summarize_review(
            pr_context=pr_context,
            comment_body=comment_body,
            classified=classified,
            semgrep_available=True,
        )
    except FileNotFoundError:
        return _fallback_review_message(
            "Semgrep is not installed in this environment, so I could not run static analysis."
        )
    except subprocess.TimeoutExpired:
        return _fallback_review_message(
            "Semgrep timed out before the review completed. Try again on a smaller PR or touched-file set."
        )
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or str(e)).strip()[:500]
        return _fallback_review_message(
            f"Patchy could not clone or check out the pull request branch. `{detail}`"
        )
    finally:
        if tmpdir and os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)


def answer_pull_request_question(installation_id, repo_full_name, pull_number, comment_body):
    """Answer a PR-thread question using PR metadata and recent comments."""
    pr_context = github_client.get_pull_request_context(
        installation_id, repo_full_name, pull_number
    )
    files_summary = "\n".join(
        f"- {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
        for f in pr_context.get("changed_files", [])[:25]
    )
    comments = "\n".join(pr_context.get("comments", [])[-10:])

    prompt = f"""A developer mentioned Patchy on this GitHub pull request.

Repository: {repo_full_name}
PR #{pull_number}: {pr_context.get('title')}
PR body:
{pr_context.get('body') or '(empty)'}

Changed files:
{files_summary or '(none)'}

Recent conversation:
{comments or '(none)'}

Developer's comment:
{comment_body}

Answer the developer's question as Patchy. Be concise, specific, security-focused, and use GitHub markdown.
If the question asks for a full review, say that Patchy can run one when asked with "review this PR".
"""
    return chat([
        {
            "role": "system",
            "content": "You are Patchy, a helpful GitHub security bot answering inside a pull request."
        },
        {"role": "user", "content": prompt},
    ], temperature=0.3, max_tokens=900)


def _clone_pr(installation_id, repo_full_name, pull_number, repo_path):
    token = github_client.get_installation_token(installation_id)
    clone_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
    subprocess.run(
        ["git", "clone", "--depth", "1", clone_url, repo_path],
        capture_output=True, text=True, timeout=60, check=True
    )
    subprocess.run(
        ["git", "fetch", "--depth", "1", "origin", f"pull/{pull_number}/head:patchy-pr-review"],
        cwd=repo_path, capture_output=True, text=True, timeout=60, check=True
    )
    subprocess.run(
        ["git", "checkout", "patchy-pr-review"],
        cwd=repo_path, capture_output=True, text=True, timeout=30, check=True
    )


def _run_semgrep_on_paths(repo_path, file_paths):
    existing = [
        os.path.join(repo_path, p)
        for p in file_paths
        if p and os.path.isfile(os.path.join(repo_path, p))
    ]
    if not existing:
        return []

    result = subprocess.run(
        [_semgrep_binary(), "--config", "auto", "--json", "--timeout", str(SEMGREP_TIMEOUT), *existing],
        capture_output=True, text=True, timeout=SEMGREP_TIMEOUT + 30
    )
    if not result.stdout:
        return []

    data = json.loads(result.stdout)
    findings = data.get("results", [])
    for f in findings:
        if f.get("path", "").startswith(repo_path):
            f["path"] = os.path.relpath(f["path"], repo_path)
    return findings


def _semgrep_binary():
    semgrep = shutil.which("semgrep")
    if semgrep:
        return semgrep
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "semgrep")
    if os.path.exists(local):
        return local
    return "semgrep"


def _changed_line_ranges(changed_files):
    by_file = {}
    for file_info in changed_files:
        filename = file_info.get("filename")
        patch = file_info.get("patch") or ""
        if not filename or not patch:
            by_file[filename] = []
            continue
        ranges = []
        new_line = None
        for line in patch.splitlines():
            if line.startswith("@@"):
                marker = line.split("@@")[1].strip()
                plus_part = next((p for p in marker.split() if p.startswith("+")), "+0")
                start_text = plus_part[1:].split(",", 1)[0]
                try:
                    new_line = int(start_text)
                except ValueError:
                    new_line = None
                continue
            if new_line is None:
                continue
            if line.startswith("+") and not line.startswith("+++"):
                ranges.append((new_line, new_line))
                new_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                continue
            else:
                new_line += 1
        by_file[filename] = _merge_ranges(ranges)
    return by_file


def _merge_ranges(ranges):
    if not ranges:
        return []
    merged = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _classify_findings(findings, changed_ranges):
    introduced = []
    existing = []
    for finding in findings:
        path = finding.get("path", "")
        line = finding.get("start", {}).get("line", 0)
        bucket = "existing_in_touched_file"
        for start, end in changed_ranges.get(path, []):
            if start <= line <= end:
                bucket = "introduced_or_modified_by_pr"
                break
        item = _compact_finding(finding, bucket)
        if bucket == "introduced_or_modified_by_pr":
            introduced.append(item)
        else:
            existing.append(item)
    return {
        "introduced": introduced,
        "existing": existing,
        "total": len(findings),
    }


def _compact_finding(finding, bucket):
    extra = finding.get("extra", {})
    return {
        "bucket": bucket,
        "rule": finding.get("check_id", "unknown"),
        "file": finding.get("path", ""),
        "line": finding.get("start", {}).get("line"),
        "severity": (extra.get("severity") or "unknown").lower(),
        "message": extra.get("message", ""),
    }


def _summarize_review(pr_context, comment_body, classified, semgrep_available):
    introduced = classified.get("introduced", [])
    existing = classified.get("existing", [])
    finding_json = json.dumps(classified, indent=2)[:12000]
    changed_files = "\n".join(
        f"- {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})"
        for f in pr_context.get("changed_files", [])[:40]
    )

    prompt = f"""Write a GitHub PR security review comment for Patchy.

Repository: {pr_context.get('repo_name')}
PR #{pr_context.get('number')}: {pr_context.get('title')}
Author: {pr_context.get('author')}
Developer request: {comment_body}

Changed files:
{changed_files or '(none)'}

Semgrep was run only on touched files from the PR branch.
Findings are classified by whether the finding line is inside an added/modified PR line range.

Classified findings JSON:
{finding_json}

Required structure:
## Patchy PR Review
### PR-introduced security risks
### Existing findings in touched files
### Recommendation

Rules:
- Do not claim the PR introduced findings from the existing bucket.
- If a section has no findings, say so clearly.
- Keep it under 500 words.
- Include file:line and rule names for concrete findings.
- Be honest that this is static analysis plus context review, not a guarantee.
"""
    try:
        return chat([
            {
                "role": "system",
                "content": "You are Patchy, a precise security bot writing pull request review comments."
            },
            {"role": "user", "content": prompt},
        ], temperature=0.2, max_tokens=1400)
    except Exception as e:
        return _deterministic_review(pr_context, introduced, existing, str(e), semgrep_available)


def _deterministic_review(pr_context, introduced, existing, llm_error, semgrep_available):
    lines = [
        "## Patchy PR Review",
        "",
        "### PR-introduced security risks",
    ]
    if introduced:
        for f in introduced[:10]:
            lines.append(f"- `{f['file']}:{f['line']}` `{f['rule']}` ({f['severity']}): {f['message']}")
    else:
        lines.append("- No Semgrep findings landed directly on changed PR lines.")

    lines.extend(["", "### Existing findings in touched files"])
    if existing:
        for f in existing[:10]:
            lines.append(f"- `{f['file']}:{f['line']}` `{f['rule']}` ({f['severity']}): {f['message']}")
    else:
        lines.append("- No additional Semgrep findings found in touched files.")

    lines.extend([
        "",
        "### Recommendation",
        "- Review any PR-introduced findings before merge.",
        "- Treat existing findings as separate cleanup unless this PR is already touching that code path.",
    ])
    if not semgrep_available:
        lines.append("- Semgrep did not complete, so this review is limited.")
    if llm_error:
        lines.append(f"\n_LLM summary unavailable: {llm_error}_")
    lines.append(f"\n_Static analysis context: PR #{pr_context.get('number')} on `{pr_context.get('repo_name')}`._")
    return "\n".join(lines)


def _fallback_review_message(reason):
    return f"""## Patchy PR Review

I could not complete the report-only review.

### Reason
{reason}

### Recommendation
Please try again after the local Patchy environment has Semgrep available and the repository can be cloned by the GitHub App installation.
"""
