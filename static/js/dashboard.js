/**
 * Dashboard Controller
 * Manages repository list, scan triggers, and real-time updates.
 * 
 * BACKEND DEPENDENCIES:
 * - GET  /api/repos  - Fetch user repositories
 * - POST /api/scan   - Trigger repository scan
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
    const langColors = { 'Python': 'bg-yellow-400', 'JavaScript': 'bg-blue-400', 'TypeScript': 'bg-blue-400', 'Go': 'bg-cyan-400', 'HCL': 'bg-purple-400' };
    const langColor = langColors[repo.language] || 'bg-slate-400';
    let statusDot = repo.status === 'error' ? '<div class="w-2 h-2 rounded-full bg-error shadow-[0_0_8px_rgba(255,180,171,0.8)]"></div>' :
        repo.status === 'active' ? '<div class="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_#4edea3] animate-pulse"></div>' :
        '<div class="w-2 h-2 rounded-full bg-surface-variant"></div>';
    let lastScanText = repo.status === 'error'
        ? `<span class="font-body-sm text-body-sm text-error flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">warning</span> Scan Failed: ${escapeHtml(repo.last_scan)}</span>`
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
    showToast(`Scanning ${repo.name}...`, 'info');
    try {
        const result = await API.scanRepo(repoId, repo.full_name);
        await new Promise(resolve => setTimeout(resolve, 3000));
        showToast(`Scan complete for ${repo.name}! PR created.`, 'success');
    } catch (error) {
        showToast(`Scan failed for ${repo.name}.`, 'error');
    } finally {
        scanningRepos.delete(repoId);
        renderRepoGrid(allRepos);
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
