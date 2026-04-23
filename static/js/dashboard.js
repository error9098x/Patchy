/**
 * Dashboard Controller
 * Manages repository list, scan triggers, and real-time updates.
 */

const scanningRepos = new Set();
let allRepos = [];

document.addEventListener('DOMContentLoaded', () => { loadRepositories(); });

async function loadRepositories() {
    const grid = document.getElementById('repo-grid');
    if (!grid) return;
    grid.innerHTML = generateSkeletonCards(4);
    try {
        const repos = await API.fetchRepos();
        allRepos = repos;
        renderRepoGrid(repos);
    } catch (error) {
        console.error('[Dashboard] Failed to load repos:', error);
        showError('Failed to load repositories.');
    }
}

function renderRepoGrid(repos) {
    const grid = document.getElementById('repo-grid');
    if (!grid) return;
    const cardsHtml = repos.map(repo => renderRepoCard(repo)).join('');
    const ghostCard = `
        <button class="bg-transparent rounded-xl border-2 border-dashed border-surface-variant hover:border-primary hover:bg-surface-container/30 transition-all duration-300 p-6 flex flex-col justify-center items-center group h-64 cursor-pointer" onclick="showConnectRepo()">
            <div class="w-12 h-12 rounded-full bg-surface-bright border border-surface-variant group-hover:border-primary flex items-center justify-center mb-4 transition-colors">
                <span class="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors text-[24px]">add</span>
            </div>
            <h3 class="font-h3 text-h3 text-on-surface-variant group-hover:text-on-surface transition-colors">Connect Repository</h3>
            <p class="font-body-sm text-body-sm text-outline mt-2 text-center max-w-[200px]">Import a new project from your GitHub organization.</p>
        </button>`;
    grid.innerHTML = cardsHtml + ghostCard;
}

function renderRepoCard(repo) {
    const isScanning = scanningRepos.has(repo.id);
    const langColors = { 'Python': 'bg-yellow-400', 'JavaScript': 'bg-blue-400', 'TypeScript': 'bg-blue-400', 'Go': 'bg-cyan-400', 'HCL': 'bg-purple-400', 'HTML': 'bg-orange-400' };
    const langColor = langColors[repo.language] || 'bg-slate-400';
    let statusDot = repo.status === 'error' ? '<div class="w-2 h-2 rounded-full bg-error shadow-[0_0_8px_rgba(255,180,171,0.8)]"></div>' :
        repo.status === 'active' ? '<div class="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_#4edea3] animate-pulse"></div>' :
        '<div class="w-2 h-2 rounded-full bg-surface-variant"></div>';
    let lastScanText = repo.status === 'error'
        ? `<span class="font-body-sm text-body-sm text-error flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">warning</span> Scan Failed</span>`
        : `<span class="font-body-sm text-body-sm text-on-surface-variant flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">history</span> Last scan: ${escapeHtml(repo.last_scan || 'Never')}</span>`;
    const avatarsHtml = (repo.contributors || []).slice(0, 3).map(url =>
        `<img alt="Contributor" class="w-8 h-8 rounded-full border-2 border-surface-container" src="${escapeHtml(url)}"/>`).join('');
    const extraCount = (repo.contributors || []).length - 3;
    const extraBadge = extraCount > 0 ? `<div class="w-8 h-8 rounded-full border-2 border-surface-container bg-surface-bright flex items-center justify-center font-label-caps text-[10px] text-on-surface-variant">+${extraCount}</div>` : '';
    let scanBtn = isScanning
        ? `<button class="scan-btn bg-primary/10 text-primary border border-primary/30 font-label-caps text-label-caps py-2 px-4 rounded flex items-center gap-2 opacity-60 cursor-not-allowed" disabled><span class="spinner spinner-sm"></span> Scanning...</button>`
        : repo.status === 'error'
        ? `<button class="scan-btn bg-primary hover:bg-primary-container text-on-primary font-label-caps text-label-caps py-2 px-4 rounded flex items-center gap-2 transition-colors shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]" onclick="handleScanClick('${repo.id}')"><span class="material-symbols-outlined text-[16px]">refresh</span> Retry Scan</button>`
        : `<button class="scan-btn bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 font-label-caps text-label-caps py-2 px-4 rounded flex items-center gap-2 transition-colors" onclick="handleScanClick('${repo.id}')"><span class="material-symbols-outlined text-[16px]">radar</span> Scan Now</button>`;
    return `
        <div class="bg-surface-container rounded-xl border border-surface-variant hover:border-primary hover:shadow-[0_0_15px_rgba(75,142,255,0.15)] transition-all duration-300 p-6 flex flex-col justify-between group relative overflow-hidden h-64" data-repo-id="${repo.id}">
            <div class="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
            <div>
                <div class="flex justify-between items-start mb-4">
                    <div class="flex items-center gap-2 text-on-surface-variant"><span class="material-symbols-outlined text-xl">code_blocks</span><span class="font-mono text-mono">${escapeHtml(repo.full_name)}</span></div>
                    ${statusDot}
                </div>
                <h3 class="font-h3 text-h3 text-on-surface group-hover:text-primary transition-colors">${escapeHtml(repo.name)}</h3>
            </div>
            <div class="mt-auto">
                <div class="flex items-center gap-3 mb-4">
                    <span class="px-2.5 py-1 rounded bg-inverse-on-surface border border-outline-variant font-label-caps text-label-caps text-on-surface flex items-center gap-1.5"><span class="w-2 h-2 rounded-full ${langColor}"></span> ${escapeHtml(repo.language)}</span>
                    ${lastScanText}
                </div>
                <div class="border-t border-surface-variant pt-4 flex justify-between items-center">
                    <div class="flex -space-x-2">${avatarsHtml}${extraBadge}</div>
                    ${scanBtn}
                </div>
            </div>
        </div>`;
}

function generateSkeletonCards(count) {
    let html = '';
    for (let i = 0; i < count; i++) {
        html += `<div class="bg-surface-container rounded-xl border border-surface-variant p-6 h-64 flex flex-col justify-between animate-pulse"><div><div class="skeleton h-4 w-3/4 mb-4"></div><div class="skeleton h-6 w-1/2"></div></div><div><div class="skeleton h-4 w-1/3 mb-4"></div><div class="border-t border-surface-variant pt-4 flex justify-between"><div class="flex -space-x-2"><div class="skeleton w-8 h-8 rounded-full"></div></div><div class="skeleton h-8 w-24 rounded"></div></div></div></div>`;
    }
    return html;
}

async function handleScanClick(repoId) {
    if (scanningRepos.has(repoId)) return;
    const repo = allRepos.find(r => r.id === repoId);
    if (!repo) return;
    scanningRepos.add(repoId);
    renderRepoGrid(allRepos);

    try {
        const result = await API.scanRepo(repoId, repo.full_name);
        const scanId = result.scan_id;
        const scanHash = result.scan_hash || '';

        // Show progress modal
        showScanProgressModal(repo.name, scanId, scanHash);

        // Poll for status
        const pollInterval = setInterval(async () => {
            try {
                const status = await API.fetchScanStatus(scanId);
                updateScanProgressModal(status);

                if (status.status === 'complete') {
                    clearInterval(pollInterval);
                    scanningRepos.delete(repoId);
                    renderRepoGrid(allRepos);
                } else if (status.status === 'failed') {
                    clearInterval(pollInterval);
                    scanningRepos.delete(repoId);
                    renderRepoGrid(allRepos);
                }
            } catch (e) {
                clearInterval(pollInterval);
                scanningRepos.delete(repoId);
                renderRepoGrid(allRepos);
            }
        }, 2000);

    } catch (error) {
        showToast(`Scan failed for ${repo.name}.`, 'error');
        scanningRepos.delete(repoId);
        renderRepoGrid(allRepos);
    }
}


// =============================================================================
// SCAN PROGRESS MODAL
// =============================================================================

function showScanProgressModal(repoName, scanId, scanHash) {
    // Remove existing if any
    const existing = document.getElementById('scan-progress-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'scan-progress-modal';
    modal.className = 'modal-overlay active';
    modal.innerHTML = `
        <div class="modal-content p-0 max-w-lg" style="transform: scale(1);">
            <div class="p-5 border-b border-[#30363d] flex justify-between items-center">
                <div>
                    <h2 class="font-h3 text-h3 text-on-surface flex items-center gap-2">
                        <span class="material-symbols-outlined text-primary">radar</span>
                        Scanning in Progress
                    </h2>
                    <div class="font-mono text-mono text-on-surface-variant mt-1">${escapeHtml(repoName)} · ${escapeHtml(scanHash)}</div>
                </div>
                <button class="text-on-surface-variant hover:text-on-surface transition-colors" onclick="closeScanProgressModal()">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            <div class="p-5" id="scan-progress-body">
                <div class="mb-4">
                    <div class="flex justify-between text-body-sm mb-2">
                        <span class="text-on-surface-variant">Progress</span>
                        <span class="text-primary font-bold" id="progress-pct">5%</span>
                    </div>
                    <div class="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden">
                        <div class="h-full bg-gradient-to-r from-primary-container to-primary rounded-full transition-all duration-500" id="progress-bar" style="width: 5%"></div>
                    </div>
                </div>
                <ul class="progress-steps" id="modal-steps">
                    <li class="active" data-step="clone"><span class="step-icon"><span class="spinner spinner-sm"></span></span> Clone Repository</li>
                    <li class="pending" data-step="semgrep"><span class="step-icon"><span class="material-symbols-outlined text-[16px]">schedule</span></span> Semgrep Analysis</li>
                    <li class="pending" data-step="fixing"><span class="step-icon"><span class="material-symbols-outlined text-[16px]">schedule</span></span> AI Fix Generation</li>
                    <li class="pending" data-step="validate"><span class="step-icon"><span class="material-symbols-outlined text-[16px]">schedule</span></span> Validate Fixes</li>
                    <li class="pending" data-step="branch"><span class="step-icon"><span class="material-symbols-outlined text-[16px]">schedule</span></span> Create Branch</li>
                    <li class="pending" data-step="pr"><span class="step-icon"><span class="material-symbols-outlined text-[16px]">schedule</span></span> Open Pull Request</li>
                </ul>
                <div class="mt-4 text-center text-on-surface-variant font-body-sm" id="progress-detail">Initializing scan...</div>
            </div>
            <div class="p-4 border-t border-[#30363d] flex justify-between items-center">
                <a href="/scans/${scanId}/live" class="text-primary hover:text-primary-fixed font-body-sm flex items-center gap-1 transition-colors">
                    <span class="material-symbols-outlined text-[16px]">open_in_new</span>
                    View Full Details
                </a>
                <button class="text-on-surface-variant hover:text-error font-body-sm transition-colors" onclick="closeScanProgressModal()">Dismiss</button>
            </div>
        </div>`;
    document.body.appendChild(modal);
}

function updateScanProgressModal(status) {
    const bar = document.getElementById('progress-bar');
    const pct = document.getElementById('progress-pct');
    const detail = document.getElementById('progress-detail');
    const stepsEl = document.getElementById('modal-steps');

    if (bar) bar.style.width = (status.progress || 0) + '%';
    if (pct) pct.textContent = (status.progress || 0) + '%';

    // Update steps
    if (stepsEl && status.steps) {
        const items = stepsEl.querySelectorAll('li');
        status.steps.forEach((step, i) => {
            if (i >= items.length) return;
            const li = items[i];
            li.className = step.status === 'complete' ? 'complete' :
                           step.status === 'running' ? 'active' :
                           step.status === 'failed' ? 'complete' :
                           step.status === 'skipped' ? 'complete' : 'pending';
            const icon = li.querySelector('.step-icon');
            if (icon) {
                if (step.status === 'complete') {
                    icon.innerHTML = '<span class="material-symbols-outlined text-[16px]" style="font-variation-settings: \'FILL\' 1;">check_circle</span>';
                } else if (step.status === 'running') {
                    icon.innerHTML = '<span class="spinner spinner-sm"></span>';
                } else if (step.status === 'failed') {
                    icon.innerHTML = '<span class="material-symbols-outlined text-[16px] text-error" style="font-variation-settings: \'FILL\' 1;">error</span>';
                } else if (step.status === 'skipped') {
                    icon.innerHTML = '<span class="material-symbols-outlined text-[16px]">remove_circle_outline</span>';
                }
            }
            // Update label with message
            const label = step.label + (step.message ? ` — ${step.message}` : '') + (step.duration ? ` [${step.duration}s]` : '');
            // Set text content after icon
            const textNode = li.childNodes[li.childNodes.length - 1];
            if (textNode && textNode.nodeType === 3) {
                textNode.textContent = ' ' + label;
            }
        });
    }

    // Update detail text
    if (detail) {
        if (status.status === 'complete') {
            detail.innerHTML = `<span class="text-secondary flex items-center justify-center gap-2"><span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">check_circle</span> Scan complete! <a href="/scans/${status.id}" class="text-primary underline">View Results</a></span>`;
        } else if (status.status === 'failed') {
            detail.innerHTML = `<span class="text-error flex items-center justify-center gap-2"><span class="material-symbols-outlined">error</span> ${escapeHtml(status.error || 'Scan failed')}</span>`;
        } else {
            const running = (status.steps || []).find(s => s.status === 'running');
            detail.textContent = running ? running.message || running.label : 'Processing...';
        }
    }
}

function closeScanProgressModal() {
    const modal = document.getElementById('scan-progress-modal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}


const filterRepos = debounce((query) => {
    if (!query.trim()) { renderRepoGrid(allRepos); return; }
    const filtered = allRepos.filter(repo =>
        repo.name.toLowerCase().includes(query.toLowerCase()) ||
        repo.full_name.toLowerCase().includes(query.toLowerCase()) ||
        repo.language.toLowerCase().includes(query.toLowerCase()));
    renderRepoGrid(filtered);
}, 200);

function showConnectRepo() { showToast('Connect Repository feature coming soon!', 'info'); }
function retryLastScan() { hideError(); showToast('Retrying last scan...', 'info'); }
function cancelScan() { scanningRepos.clear(); renderRepoGrid(allRepos); showToast('Scan cancelled.', 'info'); }
