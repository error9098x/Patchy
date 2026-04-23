/**
 * API Client for Patchy Backend
 * Central API layer with mock data for frontend development.
 * 
 * BACKEND DEPENDENCIES:
 * - GET  /api/repos          → Fetch user repositories
 * - POST /api/scan           → Trigger repository scan
 * - GET  /api/scans          → Fetch scan history
 * - GET  /api/scans/:id      → Fetch scan details
 * - GET  /api/scans/:id/status → Poll scan status
 * 
 * TODO: Replace MOCK_DATA with actual API calls when backend is ready
 * TODO: Implement WebSocket for real-time scan progress
 * TODO: Add error handling for API failures
 * TODO: Add authentication token to all requests
 */

const API = {
    BASE_URL: '/api',  // BACKEND: Update this in production

    // =========================================================================
    // HELPER: Make authenticated API request
    // =========================================================================
    
    async _fetch(endpoint, options = {}) {
        const url = `${this.BASE_URL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                // BACKEND: Add auth token header here
                // 'Authorization': `Bearer ${getToken()}`
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`[API] ${endpoint} failed:`, error);
            throw error;
        }
    },

    // =========================================================================
    // AUTHENTICATION
    // =========================================================================

    /** Redirect to GitHub OAuth login */
    login() {
        // BACKEND: Redirects to /login endpoint which starts OAuth flow
        window.location.href = '/login';
    },

    /** Logout and clear session */
    async logout() {
        // BACKEND: POST to /logout to clear server session
        window.location.href = '/logout';
    },

    // =========================================================================
    // REPOSITORIES
    // =========================================================================

    /**
     * Fetch user's GitHub repositories
     * BACKEND: GET /api/repos
     * Returns: Array of { id, name, full_name, language, last_scan, status, is_scanning, contributors }
     */
    async fetchRepos() {
        // TODO: Replace with actual fetch when backend ready
        // return await this._fetch('/repos');
        
        // Using mock data for frontend development
        return new Promise(resolve => {
            setTimeout(() => resolve(MOCK_DATA.repos), 500);
        });
    },

    /**
     * Trigger a security scan on a repository
     * BACKEND: POST /api/scan
     * Body: { repo_id: string, repo_name: string }
     * Returns: { scan_id, status }
     */
    async scanRepo(repoId, repoName) {
        // TODO: Replace with actual POST when backend ready
        // return await this._fetch('/scan', {
        //     method: 'POST',
        //     body: JSON.stringify({ repo_id: repoId, repo_name: repoName })
        // });
        
        return new Promise(resolve => {
            setTimeout(() => resolve({ scan_id: 'scan_' + Date.now(), status: 'scanning' }), 300);
        });
    },

    // =========================================================================
    // SCANS
    // =========================================================================

    /**
     * Fetch scan history
     * BACKEND: GET /api/scans
     * Returns: Array of scan summary objects
     */
    async fetchScanHistory() {
        // TODO: Replace with actual fetch when backend ready
        // return await this._fetch('/scans');
        
        return new Promise(resolve => {
            setTimeout(() => resolve(MOCK_DATA.scans), 500);
        });
    },

    /**
     * Fetch detailed scan results
     * BACKEND: GET /api/scans/:id
     * Returns: Scan object with findings array
     */
    async fetchScanDetails(scanId) {
        // TODO: Replace with actual fetch when backend ready
        // return await this._fetch(`/scans/${scanId}`);
        
        return new Promise(resolve => {
            setTimeout(() => resolve(MOCK_DATA.scanDetails), 500);
        });
    },

    /**
     * Poll scan status (for in-progress scans)
     * BACKEND: GET /api/scans/:id/status
     * Returns: { status: 'scanning' | 'complete' | 'failed', progress: number }
     */
    async fetchScanStatus(scanId) {
        // TODO: Replace with actual fetch when backend ready
        // return await this._fetch(`/scans/${scanId}/status`);
        
        return new Promise(resolve => {
            setTimeout(() => resolve({ status: 'complete', progress: 100 }), 1000);
        });
    }
};


// =============================================================================
// MOCK DATA for Frontend Development
// BACKEND: Remove this entire section when API is ready
// =============================================================================

const MOCK_DATA = {
    // -------------------------------------------------------------------------
    // Repositories (displayed on dashboard)
    // -------------------------------------------------------------------------
    repos: [
        {
            id: 'repo_1',
            name: 'Core Authentication API',
            full_name: 'patchy-hq / core-api',
            language: 'Python',
            last_scan: '2 hours ago',
            status: 'active',
            is_scanning: false,
            contributors: [
                'https://i.pravatar.cc/150?img=1',
                'https://i.pravatar.cc/150?img=2'
            ]
        },
        {
            id: 'repo_2',
            name: 'Frontend Client Apps',
            full_name: 'patchy-hq / web-dashboard',
            language: 'TypeScript',
            last_scan: '2 days ago',
            status: 'inactive',
            is_scanning: false,
            contributors: [
                'https://i.pravatar.cc/150?img=3'
            ]
        },
        {
            id: 'repo_3',
            name: 'Kubernetes Configurations',
            full_name: 'patchy-hq / infra-as-code',
            language: 'HCL',
            last_scan: '5 hrs ago',
            status: 'error',
            is_scanning: false,
            contributors: [
                'https://i.pravatar.cc/150?img=4',
                'https://i.pravatar.cc/150?img=5',
                'https://i.pravatar.cc/150?img=6',
                'https://i.pravatar.cc/150?img=7'
            ]
        }
    ],

    // -------------------------------------------------------------------------
    // Scan History (displayed on /scans)
    // -------------------------------------------------------------------------
    scans: [
        {
            id: 'scan_001',
            repo: 'api-gateway-service',
            commit: '#a8c93bf',
            timestamp: '12 mins ago',
            run_time: '45s run time',
            status: 'critical',
            findings: { critical: 3, medium: 5, low: 12 },
            pr_url: 'https://github.com/patchy-hq/api-gateway/pull/42'
        },
        {
            id: 'scan_002',
            repo: 'auth-provider-v2',
            commit: '#f42da11',
            timestamp: '2 hours ago',
            run_time: '1m 12s run time',
            status: 'warning',
            findings: { critical: 0, medium: 2, low: 4 },
            pr_url: 'https://github.com/patchy-hq/auth-provider/pull/18'
        },
        {
            id: 'scan_003',
            repo: 'frontend-web-app',
            commit: '#09bba9c',
            timestamp: '5 hours ago',
            run_time: '2m 04s run time',
            status: 'clean',
            findings: { critical: 0, medium: 0, low: 0 },
            pr_url: null
        }
    ],

    // -------------------------------------------------------------------------
    // Scan Details (displayed on /scans/:id)
    // -------------------------------------------------------------------------
    scanDetails: {
        id: 'scan_001',
        repo: 'backend-api-core',
        commit: 'a8f92b1',
        timestamp: '2 mins ago',
        author: 'dev-team-alpha',
        pr_url: 'https://github.com/patchy-hq/backend-api-core/pull/42',
        summary: { critical: 3, high: 5, moderate: 12 },
        findings: [
            {
                id: 'f_001',
                severity: 'critical',
                type: 'SQL Injection (SQLi)',
                description: 'User input is directly concatenated into a SQL query without parameterization, allowing arbitrary command execution.',
                file: 'app/database/queries.py',
                line: 42,
                is_expanded: true,
                fix_diff: [
                    { type: 'removed', line_num: 42, content: "   query = f\"SELECT * FROM users WHERE username = '{request.form['username']}'\"" },
                    { type: 'added', line_num: 42, content: '   query = "SELECT * FROM users WHERE username = %s"' },
                    { type: 'added', line_num: 43, content: "   cursor.execute(query, (request.form['username'],))" }
                ]
            },
            {
                id: 'f_002',
                severity: 'high',
                type: 'Cross-Site Scripting (XSS)',
                description: 'Unsanitized user input reflected directly into HTML output context.',
                file: 'templates/profile.html',
                line: 18,
                is_expanded: false,
                fix_diff: [
                    { type: 'removed', line_num: 18, content: '   <p>{{ user_bio }}</p>' },
                    { type: 'added', line_num: 18, content: '   <p>{{ user_bio | escape }}</p>' }
                ]
            },
            {
                id: 'f_003',
                severity: 'moderate',
                type: 'Insecure Deserialization',
                description: 'Use of pickle to deserialize untrusted data stream from external API.',
                file: 'services/worker.py',
                line: 112,
                is_expanded: false,
                fix_diff: [
                    { type: 'removed', line_num: 112, content: '   data = pickle.loads(response.content)' },
                    { type: 'added', line_num: 112, content: '   data = json.loads(response.content)' }
                ]
            }
        ]
    }
};
