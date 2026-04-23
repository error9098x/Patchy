"""
Patchy - Multi-Agent GitHub Security Bot
Flask Application Entry Point

BACKEND DEPENDENCIES:
- GitHub OAuth: Client ID/Secret in .env
- Cerebras API: API key in .env
- Semgrep: Installed system-wide

Routes:
- GET  /                 → Landing page
- GET  /login            → GitHub OAuth redirect
- GET  /callback         → OAuth callback
- GET  /logout           → Logout
- GET  /dashboard        → Repository dashboard
- GET  /scans            → Scan history
- GET  /scans/<scan_id>  → Individual scan details
- POST /api/scan         → Trigger scan (AJAX)
- GET  /api/repos        → Fetch repos (AJAX)
- GET  /api/scans        → Fetch scan history (AJAX)
- GET  /api/scans/<id>   → Fetch scan details (AJAX)
- POST /webhook/issues   → GitHub webhook for @mentions
"""

import os
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# =============================================================================
# CONFIGURATION
# =============================================================================

# BACKEND: Update these with real OAuth credentials
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY', '')

# =============================================================================
# PAGE ROUTES
# =============================================================================

@app.route('/')
def index():
    """Landing page - public, no auth required."""
    return render_template('index.html')


@app.route('/login')
def login():
    """Redirect to GitHub OAuth authorization page.
    
    BACKEND: Implement GitHub OAuth flow
    - Redirect to: https://github.com/login/oauth/authorize
    - Scopes: repo, user
    - State: CSRF token
    """
    # TODO: Implement GitHub OAuth redirect
    # github_auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo,user"
    # return redirect(github_auth_url)
    
    # TEMPORARY: Skip auth for frontend development
    session['user'] = {
        'username': 'aviral',
        'avatar_url': 'https://github.com/identicons/aviral.png',
        'repos_count': 12
    }
    return redirect(url_for('dashboard'))


@app.route('/callback')
def callback():
    """Handle GitHub OAuth callback.
    
    BACKEND: Exchange code for access token
    - POST https://github.com/login/oauth/access_token
    - Store token in session
    - Fetch user info from GitHub API
    """
    # TODO: Implement OAuth callback
    # code = request.args.get('code')
    # Exchange code for token, store in session
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    """Clear session and redirect to landing page."""
    session.clear()
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    """Repository dashboard - requires auth.
    
    BACKEND: Fetch user's repos from GitHub API
    - Use stored access token
    - Return repo list with metadata
    """
    # TODO: Check auth, redirect to login if not authenticated
    user = session.get('user', {})
    return render_template('dashboard.html', user=user, active_page='repositories')


@app.route('/scans')
def scans():
    """Scan history page - requires auth.
    
    BACKEND: Fetch scan history from JSON storage
    """
    user = session.get('user', {})
    return render_template('scan_results.html', user=user, active_page='vulnerabilities')


@app.route('/scans/<scan_id>')
def scan_detail(scan_id):
    """Individual scan detail page.
    
    BACKEND: Fetch specific scan from JSON storage
    """
    user = session.get('user', {})
    return render_template('scan_detail.html', user=user, scan_id=scan_id, active_page='vulnerabilities')


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/api/repos', methods=['GET'])
def api_repos():
    """Fetch user's GitHub repositories.
    
    BACKEND: Use PyGithub to fetch repos
    Returns: Array of { id, name, full_name, language, last_scan, is_scanning }
    """
    # TODO: Implement with real GitHub API
    return jsonify([])


@app.route('/api/scan', methods=['POST'])
def api_scan():
    """Trigger a security scan on a repository.
    
    BACKEND: 
    1. Agent 1 (Scanner): Run Semgrep on repo
    2. Agent 2 (Fix Generator): Use Cerebras LLM to generate fixes  
    3. Agent 3 (PR Creator): Create PR with fixes
    
    Body: { repo_id: string, repo_name: string }
    Returns: { scan_id, status }
    """
    # TODO: Implement multi-agent scan pipeline
    data = request.get_json()
    return jsonify({'scan_id': 'pending', 'status': 'not_implemented'})


@app.route('/api/scans', methods=['GET'])
def api_scans():
    """Fetch scan history.
    
    BACKEND: Read from scans.json
    Returns: Array of scan results
    """
    # TODO: Read from scans.json
    return jsonify([])


@app.route('/api/scans/<scan_id>', methods=['GET'])
def api_scan_details(scan_id):
    """Fetch detailed scan results.
    
    BACKEND: Read specific scan from scans.json
    Returns: Scan object with findings array
    """
    # TODO: Read specific scan
    return jsonify({})


@app.route('/api/scans/<scan_id>/status', methods=['GET'])
def api_scan_status(scan_id):
    """Check scan status for polling.
    
    BACKEND: Check if scan is still running
    Returns: { status: 'scanning' | 'complete' | 'failed', progress: number }
    """
    return jsonify({'status': 'complete', 'progress': 100})


# =============================================================================
# WEBHOOK ROUTES
# =============================================================================

@app.route('/webhook/issues', methods=['POST'])
def webhook_issues():
    """Handle GitHub webhook for issue @mentions.
    
    BACKEND:
    1. Verify webhook signature
    2. Check if bot is @mentioned
    3. Agent 4 (Issue Responder): Generate response with Cerebras
    4. Post comment via GitHub API
    """
    # TODO: Implement webhook handler
    return jsonify({'status': 'received'}), 200


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
