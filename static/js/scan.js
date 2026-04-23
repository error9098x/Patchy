/**
 * Scan Controller
 * Manages scan history list and scan detail pages.
 * 
 * BACKEND DEPENDENCIES:
 * - GET /api/scans      - Fetch scan history
 * - GET /api/scans/:id  - Fetch scan details
 */

document.addEventListener('DOMContentLoaded', () => {
    const scanList = document.getElementById('scan-list');
    if (scanList) loadScanHistory();
});

// =============================================================================
// SCAN HISTORY
// =============================================================================

async function loadScanHistory() {
    const list = document.getElementById('scan-list');
    if (!list) return;
    list.innerHTML = '<div class="flex justify-center py-8"><div class="spinner"></div></div>';
    try {
        const scans = await API.fetchScanHistory();
        list.innerHTML = scans.map(scan => renderScanCard(scan)).join('');
    } catch (error) {
        console.error('[Scan] Failed to load history:', error);
        showError('Failed to load scan history.');
    }
}

function renderScanCard(scan) {
    // Severity icon/color
    let iconBg, iconColor, iconName;
    if (scan.status === 'critical') {
        iconBg = 'bg-error/10'; iconColor = 'text-error'; iconName = 'warning';
    } else if (scan.status === 'warning') {
        iconBg = 'bg-tertiary/10'; iconColor = 'text-tertiary'; iconName = 'error';
    } else {
        iconBg = 'bg-secondary/10'; iconColor = 'text-secondary'; iconName = 'check_circle';
    }

    // Severity badges
    let badges = '';
    if (scan.findings.critical > 0) {
        badges += `<span class="bg-error/10 text-error border border-error/30 px-3 py-1 rounded-DEFAULT font-label-caps text-label-caps shadow-[inset_0_0_8px_rgba(255,180,171,0.1)] flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-error animate-pulse"></span> ${scan.findings.critical} Critical
        </span>`;
    }
    if (scan.findings.medium > 0) {
        badges += `<span class="bg-tertiary/10 text-tertiary border border-tertiary/30 px-3 py-1 rounded-DEFAULT font-label-caps text-label-caps flex items-center gap-1">
            ${scan.findings.medium} Medium
        </span>`;
    }
    if (scan.findings.low > 0) {
        badges += `<span class="bg-surface-bright text-on-surface border border-outline-variant px-3 py-1 rounded-DEFAULT font-label-caps text-label-caps flex items-center gap-1">
            ${scan.findings.low} Low
        </span>`;
    }
    if (scan.status === 'clean') {
        badges = `<span class="bg-secondary/10 text-secondary border border-secondary/30 px-3 py-1 rounded-DEFAULT font-label-caps text-label-caps flex items-center gap-1">Clean Scan</span>`;
    }

    // Action buttons
    let actions = '';
    if (scan.pr_url) {
        actions += `<a href="${escapeHtml(scan.pr_url)}" target="_blank" class="flex-1 lg:flex-none border border-outline-variant bg-transparent hover:bg-surface-bright hover:border-primary hover:text-primary text-on-surface transition-colors px-4 py-2 rounded-DEFAULT font-body-sm text-body-sm text-center">View PR</a>`;
    }
    const detailBtnClass = scan.status === 'critical'
        ? 'bg-inverse-primary text-on-primary-container hover:bg-primary-container font-bold shadow-[inset_0_1px_1px_rgba(255,255,255,0.3)]'
        : 'border border-outline-variant bg-transparent hover:bg-surface-bright hover:border-primary hover:text-primary text-on-surface';
    actions += `<a href="/scans/${scan.id}" class="flex-1 lg:flex-none ${detailBtnClass} transition-colors px-4 py-2 rounded-DEFAULT font-body-sm text-body-sm text-center">View Details</a>`;

    const opacity = scan.status === 'clean' ? 'opacity-80 hover:opacity-100' : '';

    return `
        <div class="bg-[#161b22] border border-[#30363d] rounded-lg p-lg flex flex-col lg:flex-row lg:items-center justify-between gap-lg hover:bg-surface-container-high transition-colors group ${opacity}">
            <div class="flex items-start gap-md flex-1">
                <div class="${iconBg} ${iconColor} p-2 rounded-DEFAULT flex items-center justify-center shrink-0 border border-current/20">
                    <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">${iconName}</span>
                </div>
                <div class="flex flex-col gap-xs">
                    <h3 class="font-h3 text-h3 text-inverse-surface flex items-center gap-sm">
                        ${escapeHtml(scan.repo)}
                        <span class="text-on-surface-variant material-symbols-outlined text-[16px]">open_in_new</span>
                    </h3>
                    <div class="flex flex-wrap items-center gap-x-md gap-y-xs text-on-surface-variant font-mono text-mono">
                        <span class="flex items-center gap-xs"><span class="material-symbols-outlined text-[16px]">commit</span> ${escapeHtml(scan.commit)}</span>
                        <span class="flex items-center gap-xs"><span class="material-symbols-outlined text-[16px]">schedule</span> ${escapeHtml(scan.timestamp)}</span>
                        <span class="flex items-center gap-xs"><span class="material-symbols-outlined text-[16px]">timer</span> ${escapeHtml(scan.run_time)}</span>
                    </div>
                </div>
            </div>
            <div class="flex flex-wrap items-center gap-sm">${badges}</div>
            <div class="flex items-center gap-sm w-full lg:w-auto mt-md lg:mt-0 pt-md lg:pt-0 border-t lg:border-t-0 border-[#30363d]">${actions}</div>
        </div>`;
}

// =============================================================================
// SCAN DETAIL
// =============================================================================

async function loadScanDetail(scanId) {
    const findingsList = document.getElementById('findings-list');
    if (!findingsList) return;
    findingsList.innerHTML = '<div class="flex justify-center py-8"><div class="spinner"></div></div>';
    try {
        const details = await API.fetchScanDetails(scanId);
        // Update header info
        const repoName = document.getElementById('scan-repo-name');
        if (repoName) repoName.textContent = details.repo;
        const commit = document.getElementById('scan-commit');
        if (commit) commit.textContent = details.commit;
        const time = document.getElementById('scan-time');
        if (time) time.textContent = details.timestamp;
        const author = document.getElementById('scan-author');
        if (author) author.textContent = details.author;
        // Update severity counts
        const crit = document.getElementById('count-critical');
        if (crit) crit.textContent = details.summary.critical;
        const high = document.getElementById('count-high');
        if (high) high.textContent = details.summary.high;
        const mod = document.getElementById('count-moderate');
        if (mod) mod.textContent = details.summary.moderate;
        // Update PR link
        const prLink = document.getElementById('view-pr-link');
        if (prLink && details.pr_url) {
            prLink.href = details.pr_url;
            prLink.textContent = `View Pull Request`;
        }
        // Render findings
        findingsList.innerHTML = details.findings.map(f => renderFindingCard(f)).join('');
    } catch (error) {
        console.error('[Scan] Failed to load details:', error);
        showError('Failed to load scan details.');
    }
}

function renderFindingCard(finding) {
    let iconClass, iconBg, iconName;
    if (finding.severity === 'critical') {
        iconClass = 'text-error'; iconBg = 'bg-error-container/20'; iconName = 'warning';
    } else if (finding.severity === 'high') {
        iconClass = 'text-tertiary'; iconBg = 'bg-tertiary-container/20'; iconName = 'gpp_bad';
    } else {
        iconClass = 'text-secondary'; iconBg = 'bg-secondary-container/20'; iconName = 'lock_open';
    }
    const fileClass = finding.severity === 'critical'
        ? 'text-primary bg-primary-container/10 border-primary-container/20'
        : 'text-on-surface-variant bg-surface-container-highest border-outline-variant';
    
    let diffHtml = '';
    if (finding.is_expanded && finding.fix_diff) {
        const diffLines = finding.fix_diff.map(line => {
            if (line.type === 'removed') {
                return `<div class="flex text-on-surface-variant line-through bg-error/10 border-l-2 border-error mb-1 p-1"><span class="w-8 text-right mr-4 text-error opacity-70 select-none">${line.line_num}</span><span class="text-error">- ${escapeHtml(line.content)}</span></div>`;
            } else {
                return `<div class="flex text-on-surface bg-secondary/10 border-l-2 border-secondary p-1 mb-1"><span class="w-8 text-right mr-4 text-secondary opacity-70 select-none">${line.line_num}</span><span class="text-secondary">+ ${escapeHtml(line.content)}</span></div>`;
            }
        }).join('');
        diffHtml = `
            <div class="p-4 bg-surface-container border-t border-outline-variant" id="finding-diff-${finding.id}">
                <div class="font-mono text-mono rounded overflow-hidden border border-outline-variant">
                    <div class="bg-surface-container-highest px-4 py-2 text-on-surface-variant flex items-center gap-2 border-b border-outline-variant">
                        <span class="material-symbols-outlined text-sm">difference</span> Diff
                    </div>
                    <div class="p-4 bg-[#0d1117] overflow-x-auto">${diffLines}</div>
                </div>
            </div>`;
    }
    const btnClass = finding.is_expanded
        ? 'bg-primary text-on-primary hover:bg-primary-fixed shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]'
        : 'border border-outline-variant text-on-surface hover:bg-surface-container-high';
    const chevron = finding.is_expanded ? 'expand_more' : 'chevron_right';

    return `
        <div class="bg-surface-container-low rounded-lg border border-outline-variant overflow-hidden hover:border-primary-container transition-colors mb-4" data-finding-id="${finding.id}">
            <div class="p-4 ${finding.is_expanded ? 'border-b border-outline-variant bg-surface-container-lowest' : ''} flex items-start justify-between gap-4">
                <div class="flex gap-3 items-start">
                    <div class="mt-1 ${iconClass} ${iconBg} p-1.5 rounded"><span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">${iconName}</span></div>
                    <div>
                        <h3 class="font-body-lg text-body-lg text-on-surface font-semibold">${escapeHtml(finding.type)}</h3>
                        <p class="font-body-sm text-body-sm text-on-surface-variant mt-1">${escapeHtml(finding.description)}</p>
                        <div class="mt-3 flex items-center gap-2 font-mono text-mono ${fileClass} px-2 py-1 rounded border inline-block">
                            <span class="material-symbols-outlined text-sm">code</span> ${escapeHtml(finding.file)}:${finding.line}
                        </div>
                    </div>
                </div>
                <button class="${btnClass} px-4 py-2 rounded font-body-sm text-body-sm transition-colors flex items-center gap-2 whitespace-nowrap" onclick="toggleFinding('${finding.id}')">
                    View Fix <span class="material-symbols-outlined text-sm">${chevron}</span>
                </button>
            </div>
            ${diffHtml}
        </div>`;
}

function toggleFinding(findingId) {
    // Toggle the is_expanded state and re-render
    const details = MOCK_DATA.scanDetails;
    const finding = details.findings.find(f => f.id === findingId);
    if (finding) {
        finding.is_expanded = !finding.is_expanded;
        const list = document.getElementById('findings-list');
        if (list) list.innerHTML = details.findings.map(f => renderFindingCard(f)).join('');
    }
}

function rescan() {
    showToast('Re-scanning repository...', 'info');
    setTimeout(() => showToast('Scan complete! Results updated.', 'success'), 3000);
}
