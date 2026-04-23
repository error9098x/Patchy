/**
 * Patchy - Global JavaScript
 * Shared utilities used across all pages.
 * 
 * Features:
 * - Toast notification system
 * - Theme management
 * - Mobile sidebar toggle
 * - Utility helpers
 */

// =============================================================================
// THEME MANAGEMENT
// =============================================================================

const theme = {
    current: localStorage.getItem('patchy-theme') || 'dark',

    toggle() {
        this.current = this.current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', this.current);
        document.documentElement.classList.toggle('dark', this.current === 'dark');
        localStorage.setItem('patchy-theme', this.current);
    },

    init() {
        document.documentElement.setAttribute('data-theme', this.current);
        document.documentElement.classList.toggle('dark', this.current === 'dark');
    }
};

// Initialize theme on load
theme.init();


// =============================================================================
// TOAST NOTIFICATION SYSTEM
// =============================================================================

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {'success'|'error'|'info'} type - Toast type
 * @param {number} duration - Auto-dismiss after ms (default: 4000)
 */
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconMap = {
        success: 'check_circle',
        error: 'error',
        info: 'info'
    };

    toast.innerHTML = `
        <span class="material-symbols-outlined text-[20px]" style="font-variation-settings: 'FILL' 1;">${iconMap[type]}</span>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" class="ml-auto text-on-surface-variant hover:text-on-surface transition-colors" aria-label="Dismiss">
            <span class="material-symbols-outlined text-[16px]">close</span>
        </button>
    `;

    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Auto-dismiss
    if (duration > 0) {
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}


// =============================================================================
// MOBILE SIDEBAR TOGGLE
// =============================================================================

function initMobileSidebar() {
    const toggle = document.getElementById('mobile-menu-toggle');
    const sidebar = document.querySelector('.app-sidebar');
    
    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('open') && 
                !sidebar.contains(e.target) && 
                !toggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }
}


// =============================================================================
// SCAN MODAL
// =============================================================================

function showScanModal() {
    const modal = document.getElementById('scan-modal');
    if (modal) {
        modal.classList.add('active');
        populateScanModalRepoList();
    }
}

function hideScanModal() {
    const modal = document.getElementById('scan-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

async function populateScanModalRepoList() {
    const list = document.getElementById('scan-modal-repo-list');
    if (!list) return;
    
    try {
        const repos = await API.fetchRepos();
        list.innerHTML = repos.map(repo => `
            <button class="w-full text-left p-3 bg-surface-container-low border border-outline-variant rounded hover:border-primary hover:bg-surface-container transition-all flex items-center justify-between gap-3"
                    onclick="handleScanClick('${repo.id}'); hideScanModal();">
                <div>
                    <div class="font-body-md text-on-surface">${repo.name}</div>
                    <div class="font-mono text-mono text-on-surface-variant">${repo.full_name}</div>
                </div>
                <span class="material-symbols-outlined text-primary text-[20px]">radar</span>
            </button>
        `).join('');
    } catch (error) {
        list.innerHTML = '<p class="text-on-surface-variant p-4">Failed to load repositories.</p>';
    }
}


// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Format a timestamp relative to now
 * @param {string|Date} date - Date to format
 * @returns {string} Relative time string
 */
function formatRelativeTime(date) {
    const now = new Date();
    const past = new Date(date);
    const diffMs = now - past;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

/**
 * Escape HTML to prevent XSS in dynamic content
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * Debounce function calls
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in ms
 * @returns {Function} Debounced function
 */
function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}


// =============================================================================
// ERROR HANDLING
// =============================================================================

function showError(message) {
    const errorState = document.getElementById('error-scan');
    const errorMessage = document.getElementById('error-message');
    
    if (errorState && errorMessage) {
        errorMessage.textContent = message;
        errorState.classList.remove('hidden');
    }
    
    showToast(message, 'error');
}

function hideError() {
    const errorState = document.getElementById('error-scan');
    if (errorState) {
        errorState.classList.add('hidden');
    }
}


// =============================================================================
// KEYBOARD SHORTCUTS
// =============================================================================

document.addEventListener('keydown', (e) => {
    // Escape to close modals
    if (e.key === 'Escape') {
        hideScanModal();
        hideError();
    }
    
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('repo-search');
        if (searchInput) searchInput.focus();
    }
});


// =============================================================================
// INITIALIZATION
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initMobileSidebar();
});
