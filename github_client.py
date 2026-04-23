"""
GitHub App Client
Handles GitHub App authentication, repo access, and PR creation.
Uses PyGithub with GitHub App (JWT) authentication.
"""

import os
import hmac
import hashlib
import requests
from github import Github, GithubIntegration, Auth, InputGitTreeElement


# Config from .env
APP_ID = os.getenv('GITHUB_APP_ID', '')
CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', '')
PRIVATE_KEY_PATH = os.getenv('GITHUB_APP_PRIVATE_KEY_PATH', '')
APP_SLUG = os.getenv('GITHUB_APP_SLUG', 'patchybot-dev')


def get_app_install_url():
    """URL to install the GitHub App on user's account/repos."""
    return f"https://github.com/apps/{APP_SLUG}/installations/new"


def _installation_token(installation_id):
    """Get a fresh installation access token (expires in 1hr)."""
    gi = _get_integration()
    return gi.get_access_token(installation_id).token


def _read_private_key():
    """Read GitHub App private key from file."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), PRIVATE_KEY_PATH)
    if not os.path.exists(path):
        # Try absolute path
        path = PRIVATE_KEY_PATH
    with open(path, 'r') as f:
        return f.read()


def _get_integration():
    """Create GithubIntegration instance for App-level auth."""
    private_key = _read_private_key()
    auth = Auth.AppAuth(APP_ID, private_key)
    return GithubIntegration(auth=auth)


# =============================================================================
# OAUTH FLOW (for user identity)
# =============================================================================

def get_oauth_login_url(state=None):
    """Build GitHub App user authorization URL.

    GitHub Apps do NOT use OAuth scopes — permissions are declared on the App
    itself. We only need client_id (+ optional state for CSRF).
    """
    url = "https://github.com/login/oauth/authorize"
    params = f"?client_id={CLIENT_ID}"
    if state:
        params += f"&state={state}"
    return url + params


def exchange_code_for_token(code):
    """Exchange OAuth code for user access token."""
    resp = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code
        },
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise ValueError(f"OAuth error: {data['error_description']}")
    return data["access_token"]


def get_user_info(access_token):
    """Fetch GitHub user profile with user access token."""
    g = Github(auth=Auth.Token(access_token))
    user = g.get_user()
    return {
        "username": user.login,
        "avatar_url": user.avatar_url,
        "name": user.name or user.login,
        "id": user.id
    }


def get_user_installations(access_token):
    """Get installations accessible to user (via user token)."""
    resp = requests.get(
        "https://api.github.com/user/installations",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json"
        },
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    all_insts = data.get("installations", [])
    # Only keep installations of OUR app — user may have many apps installed.
    try:
        our_app_id = int(APP_ID) if APP_ID else None
    except (TypeError, ValueError):
        our_app_id = None
    if our_app_id:
        return [i for i in all_insts if i.get("app_id") == our_app_id]
    return all_insts


# =============================================================================
# APP INSTALLATION (for repo access)
# =============================================================================

def get_github_for_installation(installation_id):
    """Get authenticated Github instance for an installation."""
    gi = _get_integration()
    return gi.get_github_for_installation(installation_id)


def get_installation_repos(installation_id):
    """List repos this installation has access to.

    Uses the correct endpoint `GET /installation/repositories` with the
    installation access token. Paginates until all repos are collected.
    """
    token = _installation_token(installation_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    repos = []
    page = 1
    while True:
        resp = requests.get(
            "https://api.github.com/installation/repositories",
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("repositories", [])
        for r in batch:
            repos.append({
                "id": str(r["id"]),
                "name": r["name"],
                "full_name": r["full_name"],
                "language": r.get("language") or "Unknown",
                "private": r.get("private", False),
                "default_branch": r.get("default_branch", "main"),
                "clone_url": r.get("clone_url", ""),
                "size_kb": r.get("size", 0),
                "last_scan": None,
                "status": "active",
                "is_scanning": False,
                "contributors": [],
            })
        if len(batch) < 100:
            break
        page += 1
    return repos


# =============================================================================
# PR CREATION
# =============================================================================

def create_fix_branch(installation_id, repo_full_name, branch_name, base_branch="main"):
    """Create a new branch from base branch."""
    g = get_github_for_installation(installation_id)
    repo = g.get_repo(repo_full_name)

    # Get base branch SHA
    base_ref = repo.get_git_ref(f"heads/{base_branch}")
    base_sha = base_ref.object.sha

    # Create new branch
    repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
    return base_sha


def commit_fixes(installation_id, repo_full_name, branch_name, fixes):
    """Commit fixed files to branch.
    
    fixes: list of {"file_path": str, "content": str, "message": str}
    """
    g = get_github_for_installation(installation_id)
    repo = g.get_repo(repo_full_name)

    for fix in fixes:
        try:
            # Get existing file to get its SHA
            existing = repo.get_contents(fix["file_path"], ref=branch_name)
            repo.update_file(
                path=fix["file_path"],
                message=fix.get("message", f"fix: patch {fix['file_path']}"),
                content=fix["content"],
                sha=existing.sha,
                branch=branch_name
            )
        except Exception as e:
            print(f"Failed to commit fix for {fix['file_path']}: {e}")
            continue


def commit_fixes_atomic(installation_id, repo_full_name, branch_name,
                         fixes, message):
    """Commit all fixes as ONE atomic commit via Git Data API.

    fixes: list of {"file_path": str, "content": str}
    message: single commit message for the whole batch.

    Returns: new commit SHA.
    """
    import base64

    if not fixes:
        return None

    # Deduplicate: keep only the last content for each file_path.
    by_path = {}
    for fix in fixes:
        by_path[fix["file_path"]] = fix["content"]

    g = get_github_for_installation(installation_id)
    repo = g.get_repo(repo_full_name)

    ref = repo.get_git_ref(f"heads/{branch_name}")
    parent_sha = ref.object.sha
    parent_commit = repo.get_git_commit(parent_sha)
    base_tree = parent_commit.tree

    elements = []
    for path, content in by_path.items():
        # Use base64 encoding to ensure byte-accurate blob creation.
        # UTF-8 string mode can produce different blob SHAs than the
        # original file (encoding quirks), causing GitHub to show
        # full-file diffs even when only a few lines changed.
        content_bytes = content.encode("utf-8")
        b64 = base64.b64encode(content_bytes).decode("ascii")
        blob = repo.create_git_blob(b64, "base64")
        elements.append(InputGitTreeElement(
            path=path, mode="100644", type="blob", sha=blob.sha
        ))

    new_tree = repo.create_git_tree(elements, base_tree)
    new_commit = repo.create_git_commit(message, new_tree, [parent_commit])
    ref.edit(new_commit.sha)
    return new_commit.sha


def create_pull_request(installation_id, repo_full_name, title, body, head_branch, base_branch="main"):
    """Create a pull request with fixes."""
    g = get_github_for_installation(installation_id)
    repo = g.get_repo(repo_full_name)

    pr = repo.create_pull(
        title=title,
        body=body,
        head=head_branch,
        base=base_branch
    )
    return {
        "number": pr.number,
        "url": pr.html_url,
        "title": pr.title
    }


# =============================================================================
# ISSUE COMMENTS
# =============================================================================

def post_issue_comment(installation_id, repo_full_name, issue_number, body):
    """Post a comment on an issue."""
    g = get_github_for_installation(installation_id)
    repo = g.get_repo(repo_full_name)
    issue = repo.get_issue(issue_number)
    comment = issue.create_comment(body)
    return comment.id


def get_issue_context(installation_id, repo_full_name, issue_number):
    """Get issue title, body, and recent comments."""
    g = get_github_for_installation(installation_id)
    repo = g.get_repo(repo_full_name)
    issue = repo.get_issue(issue_number)

    comments = []
    for c in issue.get_comments()[:10]:  # Last 10 comments
        comments.append(f"@{c.user.login}: {c.body}")

    return {
        "title": issue.title,
        "body": issue.body or "",
        "comments": comments,
        "repo_name": repo_full_name
    }


# =============================================================================
# WEBHOOK VERIFICATION
# =============================================================================

def verify_webhook_signature(payload_body, signature_header):
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not signature_header:
        return False
    
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature_header)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("Testing GitHub App connection...")
    try:
        gi = _get_integration()
        installations = list(gi.get_installations())
        print(f"✅ Found {len(installations)} installation(s)")
        for inst in installations:
            print(f"   - Installation {inst.id} on {inst.raw_data.get('account', {}).get('login', '?')}")
    except Exception as e:
        print(f"❌ Failed: {e}")
