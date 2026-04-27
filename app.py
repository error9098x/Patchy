"""
Patchy - Multi-Agent GitHub Security Bot
Flask Application Entry Point
"""

import os
import time
import secrets
import threading
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from dotenv import load_dotenv

load_dotenv()

import github_client
import storage
import scan_pipeline
import issue_responder
import pr_summarizer

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Track running scans to prevent duplicates
_running_scans = set()


# =============================================================================
# HELPERS: Data transformation for frontend
# =============================================================================

def _format_relative_time(iso_str):
    """Convert ISO timestamp to relative time string."""
    if not iso_str:
        return "Unknown"
    try:
        t = time.mktime(time.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ"))
        diff = time.time() - t
        if diff < 60:
            return "Just now"
        if diff < 3600:
            m = int(diff / 60)
            return f"{m} min{'s' if m > 1 else ''} ago"
        if diff < 86400:
            h = int(diff / 3600)
            return f"{h} hour{'s' if h > 1 else ''} ago"
        d = int(diff / 86400)
        return f"{d} day{'s' if d > 1 else ''} ago"
    except Exception:
        return iso_str


def _compute_runtime(scan):
    """Compute scan runtime string."""
    s = scan.get("started_at")
    e = scan.get("completed_at")
    if not s:
        return "—"
    try:
        t0 = time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
        t1 = time.mktime(time.strptime(e, "%Y-%m-%dT%H:%M:%SZ")) if e else time.time()
        d = t1 - t0
        if d < 60:
            return f"{d:.0f}s"
        return f"{d/60:.1f}m"
    except Exception:
        return "—"


def _severity_counts(findings_list):
    """Count findings by severity using Semgrep's actual severity levels."""
    counts = {"error": 0, "warning": 0, "info": 0}
    
    for f in (findings_list or []):
        sev = f.get("severity", "warning").lower()
        if sev in counts:
            counts[sev] += 1
        # Handle any unexpected severity values
        elif sev not in counts:
            counts["warning"] += 1
    return counts


def _scan_display_status(scan):
    """Map internal status to display status for frontend."""
    if scan["status"] == "complete":
        counts = _severity_counts(scan.get("findings", []))
        if counts["error"] > 0:
            return "critical"
        if counts["warning"] > 0:
            return "warning"
        return "clean"
    if scan["status"] == "failed":
        return "error"
    return "scanning"


def _transform_scan_for_history(scan):
    """Transform raw scan record for scan history cards."""
    counts = _severity_counts(scan.get("findings", []))
    status = _scan_display_status(scan)
    
    # Add progress info for in-progress scans
    progress = None
    if scan["status"] in ["cloning", "scanning", "fixing", "validating", "creating_pr"]:
        steps = scan.get("steps", [])
        current_step = None
        for step in steps:
            if step.get("status") == "running":
                current_step = step
                break
        if current_step:
            progress = {
                "step": current_step.get("name", ""),
                "detail": current_step.get("detail", ""),
            }
    
    return {
        "id": scan["id"],
        "repo": scan.get("repo", ""),
        "status": status,
        "commit": scan.get("scan_hash", scan["id"][-8:]),
        "timestamp": _format_relative_time(scan.get("started_at")),
        "started_at": scan.get("started_at", ""),
        "run_time": _compute_runtime(scan),
        "findings": counts,
        "findings_count": scan.get("findings_count", 0),
        "pr_url": scan.get("pr_url"),
        "pr_number": scan.get("pr_number"),
        "scan_hash": scan.get("scan_hash", ""),
        "progress": progress,
        "is_in_progress": scan["status"] in ["cloning", "scanning", "fixing", "validating", "creating_pr"],
    }


def _transform_scan_for_detail(scan):
    """Transform raw scan record for scan detail page."""
    counts = _severity_counts(scan.get("findings", []))
    findings = []
    fixes = scan.get("fixes", [])
    for f in (scan.get("findings") or []):
        file_path = f.get("file", "")
        fix_diff = None
        for fix in fixes:
            if fix.get("file_path") == file_path and fix.get("original_code") and fix.get("fixed_code"):
                fix_diff = pr_summarizer.make_unified_diff(
                    fix.get("original_code", ""),
                    fix.get("fixed_code", ""),
                    file_path
                )
                break
                
        findings.append({
            "id": f.get("id", ""),
            "type": f.get("type", "Unknown"),
            "description": f.get("message", "No description available."),
            "file": file_path,
            "line": f.get("line", 0),
            "severity": f.get("severity", "medium"),
            "fix_status": f.get("fix_status", "skipped"),
            "fix_explanation": f.get("fix_explanation", ""),
            "semgrep_rule": f.get("semgrep_rule", ""),
            "is_expanded": False,
            "fix_diff": fix_diff,
        })
    return {
        "id": scan["id"],
        "repo": scan.get("repo", ""),
        "commit": scan.get("scan_hash", scan["id"][-8:]),
        "scan_hash": scan.get("scan_hash", ""),
        "timestamp": _format_relative_time(scan.get("started_at")),
        "started_at": scan.get("started_at", ""),
        "author": "patchy-bot",
        "status": scan.get("status", ""),
        "summary": {
            "error": counts["error"],
            "warning": counts["warning"],
            "info": counts["info"],
        },
        "findings": findings,
        "pr_url": scan.get("pr_url"),
        "pr_number": scan.get("pr_number"),
        "pr_branch": scan.get("pr_branch"),
        "error": scan.get("error"),
        "steps": scan.get("steps", []),
        "fixes_generated": scan.get("fixes_generated", 0),
        "fixes_valid": scan.get("fixes_valid", 0),
    }


# =============================================================================
# PAGE ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    state = secrets.token_hex(16)
    session['oauth_state'] = state
    auth_url = github_client.get_oauth_login_url(state=state)
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """Handle GitHub OAuth callback."""
    code = request.args.get('code')
    state = request.args.get('state')
    setup_action = request.args.get('setup_action')
    installation_id_param = request.args.get('installation_id')

    expected_state = session.pop('oauth_state', None)
    if not setup_action and state and expected_state and state != expected_state:
        return redirect(url_for('index', error='invalid_state'))

    if not code:
        if setup_action == 'install':
            return redirect(url_for('login'))
        return redirect(url_for('index', error='no_code'))

    try:
        access_token = github_client.exchange_code_for_token(code)
        user_info = github_client.get_user_info(access_token)
        installations = github_client.get_user_installations(access_token)

        session['user'] = user_info
        session['access_token'] = access_token
        session['installations'] = [
            {"id": inst["id"], "account": inst.get("account", {}).get("login", "")}
            for inst in installations
        ]

        if not installations:
            return redirect(github_client.get_app_install_url())

        return redirect(url_for('dashboard'))

    except Exception as e:
        import traceback
        print(f"OAuth callback failed: {e}")
        traceback.print_exc()
        return redirect(url_for('index', error='auth_failed'))


@app.route('/install')
def install():
    return redirect(github_client.get_app_install_url())


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# =============================================================================
# AI CHAT API
# =============================================================================

@app.route('/api/chat/<scan_id>', methods=['POST'])
def chat_with_scan(scan_id):
    """Stream AI chat responses about a specific scan."""
    import json
    import traceback
    
    try:
        from tools.nvidia_client import chat_stream
    except ImportError as e:
        print(f"[CHAT ERROR] Failed to import chat_stream: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Chat module not available'}), 500
    
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        history = data.get('history', [])
        
        print(f"[CHAT] Received message for scan {scan_id}: {user_message[:50]}...")
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Get scan details for context
        scan = storage.get_scan(scan_id)
        if not scan:
            print(f"[CHAT ERROR] Scan {scan_id} not found")
            return jsonify({'error': 'Scan not found'}), 404
        
        print(f"[CHAT] Found scan: {scan.get('repo', 'unknown')}, {scan.get('findings_count', 0)} findings")
        
        # Build context from scan
        findings_summary = []
        for f in scan.get('findings', [])[:10]:  # Limit to 10 findings for context
            findings_summary.append({
                'file': f.get('file', ''),
                'severity': f.get('severity', ''),
                'type': f.get('type', ''),
                'message': f.get('message', ''),
                'fix_status': f.get('fix_status', ''),
            })
        
        context = {
            'repo': scan.get('repo', ''),
            'status': scan.get('status', ''),
            'findings_count': scan.get('findings_count', 0),
            'fixes_generated': scan.get('fixes_generated', 0),
            'fixes_valid': scan.get('fixes_valid', 0),
            'pr_url': scan.get('pr_url'),
            'findings': findings_summary,
        }
        
        # System prompt
        system_prompt = f"""You are Patchy's security analysis assistant. You help developers understand security scan results.

Scan Context:
- Repository: {context['repo']}
- Status: {context['status']}
- Findings: {context['findings_count']} vulnerabilities detected
- Fixes: {context['fixes_generated']} generated, {context['fixes_valid']} valid
- PR: {'Created' if context['pr_url'] else 'Not created'}

Key Findings:
{json.dumps(findings_summary, indent=2)}

Guidelines:
- Be concise and helpful
- Use simple formatting: bullets (- or *), bold (**text**), italic (*text*)
- NO code blocks, NO large headings, NO complex markdown
- Keep responses focused and actionable
- If asked about specific vulnerabilities, reference the findings above
- Suggest next steps when appropriate"""

        # Build messages
        messages = [{'role': 'system', 'content': system_prompt}]
        
        # Add conversation history (last 5 exchanges to keep context manageable)
        for msg in history[-10:]:
            messages.append({'role': msg['role'], 'content': msg['content']})
        
        # Add current user message
        messages.append({'role': 'user', 'content': user_message})
        
        print(f"[CHAT] Calling LLM with {len(messages)} messages...")
        
        # Stream response
        def generate():
            try:
                chunk_count = 0
                has_content = False
                
                # Try streaming
                try:
                    for chunk in chat_stream(messages, temperature=0.7, max_tokens=500):
                        if chunk:
                            chunk_count += 1
                            has_content = True
                            if chunk_count == 1:
                                print(f"[CHAT] First chunk received: {chunk[:50]}")
                            yield f"data: {json.dumps({'content': chunk})}\n\n"
                    
                    if has_content:
                        print(f"[CHAT] Streamed {chunk_count} chunks successfully")
                        yield "data: [DONE]\n\n"
                    else:
                        print(f"[CHAT WARNING] No chunks received from stream, trying non-streaming...")
                        # Fallback to non-streaming
                        from tools.nvidia_client import chat
                        response = chat(messages, temperature=0.7, max_tokens=500)
                        print(f"[CHAT] Non-streaming response length: {len(response)}")
                        if response:
                            yield f"data: {json.dumps({'content': response})}\n\n"
                            yield "data: [DONE]\n\n"
                        else:
                            raise Exception("Empty response from LLM")
                            
                except Exception as stream_error:
                    print(f"[CHAT ERROR] Streaming failed: {stream_error}")
                    traceback.print_exc()
                    # Try non-streaming as fallback
                    from tools.nvidia_client import chat
                    response = chat(messages, temperature=0.7, max_tokens=500)
                    if response:
                        print(f"[CHAT] Fallback non-streaming succeeded: {len(response)} chars")
                        yield f"data: {json.dumps({'content': response})}\n\n"
                        yield "data: [DONE]\n\n"
                    else:
                        raise Exception(f"LLM call failed: {stream_error}")
                        
            except Exception as e:
                error_msg = f"Stream error: {str(e)}"
                print(f"[CHAT ERROR] {error_msg}")
                traceback.print_exc()
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        response = app.response_class(generate(), mimetype='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response
        
    except Exception as e:
        error_msg = f"Chat endpoint error: {str(e)}"
        print(f"[CHAT ERROR] {error_msg}")
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@app.route('/api/chat/test', methods=['GET'])
def test_chat():
    """Test endpoint to verify streaming works."""
    import json
    import time
    
    def generate():
        for i in range(5):
            yield f"data: {json.dumps({'content': f'Test chunk {i+1} '})}\n\n"
            time.sleep(0.1)
        yield "data: [DONE]\n\n"
    
    response = app.response_class(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


# =============================================================================
# AUTH HELPERS
# =============================================================================

def require_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/dashboard')
@require_auth
def dashboard():
    user = session.get('user', {})
    return render_template('dashboard.html', user=user, active_page='repositories')


@app.route('/scans')
@require_auth
def scans():
    user = session.get('user', {})
    return render_template('scan_results.html', user=user, active_page='vulnerabilities')


@app.route('/scans/<scan_id>')
@require_auth
def scan_detail(scan_id):
    user = session.get('user', {})
    return render_template('scan_detail.html', user=user, scan_id=scan_id, active_page='vulnerabilities')


@app.route('/scans/<scan_id>/live')
@require_auth
def scan_live(scan_id):
    """Live scan progress page."""
    user = session.get('user', {})
    return render_template('scan_live.html', user=user, scan_id=scan_id, active_page='vulnerabilities')


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/api/repos', methods=['GET'])
@require_auth
def api_repos():
    access_token = session.get('access_token')
    try:
        if access_token:
            live = github_client.get_user_installations(access_token)
            installations = [
                {"id": i["id"], "account": i.get("account", {}).get("login", "")}
                for i in live
            ]
            session['installations'] = installations
        else:
            installations = session.get('installations', [])
    except Exception as e:
        print(f"Failed to refresh installations: {e}")
        installations = session.get('installations', [])

    if not installations:
        return jsonify({
            "status": "error", "code": "NO_INSTALLATION",
            "message": "No GitHub App installation found. Install the app first.",
            "install_url": github_client.get_app_install_url(),
        }), 400

    try:
        all_repos = []
        for inst in installations:
            repos = github_client.get_installation_repos(inst["id"])
            all_scans = storage.get_all_scans()
            for repo in repos:
                for scan in all_scans:
                    if scan["repo"] == repo["full_name"]:
                        repo["last_scan"] = scan.get("completed_at", scan.get("started_at", ""))
                        if scan["status"] == "failed":
                            repo["status"] = "error"
                        break
                repo["is_scanning"] = repo["full_name"] in _running_scans
            all_repos.extend(repos)
        return jsonify(all_repos)
    except Exception as e:
        print(f"Failed to fetch repos: {e}")
        return jsonify({"status": "error", "code": "GITHUB_API_ERROR",
                        "message": str(e)}), 500


@app.route('/api/scan', methods=['POST'])
@require_auth
def api_scan():
    data = request.get_json()
    repo_name = data.get('repo_name', '')
    if not repo_name:
        return jsonify({"status": "error", "code": "MISSING_REPO",
                        "message": "repo_name is required"}), 400
    if repo_name in _running_scans:
        return jsonify({"status": "error", "code": "SCAN_IN_PROGRESS",
                        "message": "Scan already running for this repo"}), 409

    installations = session.get('installations', [])
    if not installations:
        return jsonify({"status": "error", "code": "NO_INSTALLATION",
                        "message": "No GitHub App installation found"}), 400

    installation_id = installations[0]["id"]
    scan_id = f"scan_{int(time.time())}"
    scan_record = storage.create_scan(scan_id, repo_name)
    _running_scans.add(repo_name)

    def _run():
        try:
            scan_pipeline.run_pipeline(repo_name, installation_id, scan_id)
        finally:
            _running_scans.discard(repo_name)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({
        "scan_id": scan_id,
        "scan_hash": scan_record.get("scan_hash", ""),
        "status": "cloning"
    })


@app.route('/api/scans', methods=['GET'])
@require_auth
def api_scans():
    """Fetch scan history — transformed for frontend cards."""
    raw_scans = storage.get_all_scans()
    transformed = [_transform_scan_for_history(s) for s in raw_scans]
    return jsonify(transformed)


@app.route('/api/scans/<scan_id>', methods=['GET'])
@require_auth
def api_scan_details(scan_id):
    """Fetch scan details — transformed for detail page."""
    scan = storage.get_scan(scan_id)
    if not scan:
        return jsonify({"status": "error", "code": "NOT_FOUND",
                        "message": "Scan not found"}), 404
    return jsonify(_transform_scan_for_detail(scan))


@app.route('/api/scans/<scan_id>/status', methods=['GET'])
def api_scan_status(scan_id):
    """Full status with steps for live progress polling."""
    status = storage.get_scan_status(scan_id)
    return jsonify(status)


# =============================================================================
# WEBHOOK ROUTE
# =============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    event_type = request.headers.get('X-GitHub-Event', '')
    signature = request.headers.get('X-Hub-Signature-256', '')
    payload_body = request.get_data()

    if event_type == 'issue_comment':
        result = issue_responder.handle_webhook(payload_body, signature)
        print(f"[WEBHOOK] issue_comment -> {result}")
        return jsonify(result), 200
    elif event_type == 'installation':
        print("[WEBHOOK] installation event received")
        return jsonify({"status": "ok", "message": "Installation event received"}), 200
    elif event_type == 'ping':
        print("[WEBHOOK] ping -> pong")
        return jsonify({"status": "ok", "message": "pong"}), 200
    print(f"[WEBHOOK] ignored event: {event_type}")
    return jsonify({"status": "ignored", "event": event_type}), 200


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, port=port)
