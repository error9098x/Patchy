/**
 * API Client for Patchy Backend
 * Real API calls to Flask backend.
 * 
 * Endpoints:
 * - GET  /api/repos          → Fetch user repositories
 * - POST /api/scan           → Trigger repository scan
 * - GET  /api/scans          → Fetch scan history
 * - GET  /api/scans/:id      → Fetch scan details
 * - GET  /api/scans/:id/status → Poll scan status
 */

const API = {
    BASE_URL: '/api',

    // =========================================================================
    // HELPER: Make authenticated API request
    // =========================================================================
    
    async _fetch(endpoint, options = {}) {
        const url = `${this.BASE_URL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401 || response.status === 403) {
                // Session expired, redirect to login
                window.location.href = '/login';
                return;
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `API Error: ${response.status}`);
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

    login() {
        window.location.href = '/login';
    },

    async logout() {
        window.location.href = '/logout';
    },

    // =========================================================================
    // REPOSITORIES
    // =========================================================================

    /**
     * Fetch user's GitHub repositories
     * Returns: Array of { id, name, full_name, language, last_scan, status, is_scanning, contributors }
     */
    async fetchRepos() {
        return await this._fetch('/repos');
    },

    /**
     * Trigger a security scan on a repository
     * Body: { repo_name: string }
     * Returns: { scan_id, status }
     */
    async scanRepo(repoId, repoName) {
        return await this._fetch('/scan', {
            method: 'POST',
            body: JSON.stringify({ repo_id: repoId, repo_name: repoName })
        });
    },

    // =========================================================================
    // SCANS
    // =========================================================================

    /**
     * Fetch scan history
     * Returns: Array of scan summary objects
     */
    async fetchScanHistory() {
        return await this._fetch('/scans');
    },

    /**
     * Fetch detailed scan results
     * Returns: Scan object with findings array
     */
    async fetchScanDetails(scanId) {
        return await this._fetch(`/scans/${scanId}`);
    },

    /**
     * Poll scan status (for in-progress scans)
     * Returns: { status, progress }
     */
    async fetchScanStatus(scanId) {
        return await this._fetch(`/scans/${scanId}/status`);
    }
};
