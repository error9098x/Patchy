/**
 * Scan Controller
 * Manages scan history list and scan detail pages.
 * Uses real API data (no mock data).
 */

let _scanDetailData = null;  // Cache for detail page

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
        if (!scans || scans.length === 0) {
            list.innerHTML = `
                <div class="text-center py-16">
                    <span class="material-symbols-outlined text-[48px] text-outline mb-4 block">search_off</span>
                    <h3 class="font-h3 text-h3 text-on-surface mb-2">No Scans Yet</h3>
                    <p class="text-on-surface-variant font-body-md">Run your first scan from the Repositories page.</p>
                </div>`;
            return;
        }
        list.innerHTML = scans.map(scan => renderScanCard(scan)).join('');
    } catch (error) {
        console.error('[Scan] Failed to load history:', error);
        showError('Failed to load scan history.');
    }
}

function renderScanCard(scan) {
    // Status icon - green for complete, red for error, blue for scanning
    let iconBg, iconColor, iconName;
    if (scan.status === 'error' || scan.status === 'failed') {
        iconBg = 'bg-error/10'; iconColor = 'text-error'; iconName = 'dangerous';
    } else if (scan.status === 'scanning' || scan.is_in_progress) {
        iconBg = 'bg-primary/10'; iconColor = 'text-primary'; iconName = 'radar';
    } else {
        // Complete - show green checkmark
        iconBg = 'bg-secondary/10'; iconColor = 'text-secondary'; iconName = 'check_circle';
    }

    // Severity badges - only show if there are findings
    let badges = '';
    if (scan.status === 'clean' || (scan.findings_count === 0 && scan.status === 'complete')) {
        badges = `<span class="bg-secondary/10 text-secondary border border-secondary/30 px-3 py-1 rounded-DEFAULT font-label-caps text-label-caps flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-secondary"></span> Clean
        </span>`;
    } else if (scan.findings_count > 0) {
        badges = `<span class="bg-tertiary/10 text-tertiary border border-tertiary/30 px-3 py-1 rounded-DEFAULT font-label-caps text-label-caps flex items-center gap-1">
            ${scan.findings_count} Finding${scan.findings_count > 1 ? 's' : ''}
        </span>`;
    }

    // Actions
    let actions = '';
    if (scan.is_in_progress) {
        actions += `<a href="/scans/${scan.id}/live" class="flex-1 lg:flex-none bg-primary text-on-primary hover:bg-primary-container transition-colors px-4 py-2 rounded-DEFAULT font-body-sm text-body-sm text-center flex items-center justify-center gap-xs">
            <span class="material-symbols-outlined text-[18px]">visibility</span> View Live
        </a>`;
    } else {
        // For completed scans, show PR button first if available
        if (scan.pr_url) {
            actions += `<a href="${escapeHtml(scan.pr_url)}" target="_blank" class="flex-1 lg:flex-none border border-outline-variant bg-transparent hover:bg-surface-bright hover:border-primary hover:text-primary text-on-surface transition-colors px-4 py-2 rounded-DEFAULT font-body-sm text-body-sm text-center">View PR</a>`;
        }
        actions += `<a href="/scans/${scan.id}/live" class="flex-1 lg:flex-none border border-outline-variant bg-transparent hover:bg-surface-bright hover:border-primary hover:text-primary text-on-surface transition-colors px-4 py-2 rounded-DEFAULT font-body-sm text-body-sm text-center">View Details</a>`;
    }

    const opacity = scan.status === 'clean' ? 'opacity-80 hover:opacity-100' : '';
    const commit = scan.commit || scan.scan_hash || scan.id.slice(-8);
    const timestamp = scan.timestamp || scan.started_at || '';
    const runTime = scan.run_time || '—';
    
    // Progress info for in-progress scans
    let progressInfo = '';
    if (scan.progress && scan.progress.detail) {
        progressInfo = `<div class="text-primary font-body-sm text-body-sm flex items-center gap-xs mt-2">
            <span class="material-symbols-outlined text-[16px] animate-pulse">autorenew</span>
            ${escapeHtml(scan.progress.detail)}
        </div>`;
    }

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
                        <span class="flex items-center gap-xs"><span class="material-symbols-outlined text-[16px]">fingerprint</span> ${escapeHtml(commit)}</span>
                        <span class="flex items-center gap-xs"><span class="material-symbols-outlined text-[16px]">schedule</span> ${escapeHtml(timestamp)}</span>
                        <span class="flex items-center gap-xs"><span class="material-symbols-outlined text-[16px]">timer</span> ${escapeHtml(runTime)}</span>
                    </div>
                    ${progressInfo}
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
        _scanDetailData = details;

        // Update header
        const repoName = document.getElementById('scan-repo-name');
        if (repoName) repoName.textContent = details.repo || '';
        const commit = document.getElementById('scan-commit');
        if (commit) commit.textContent = details.commit || details.scan_hash || '';
        const timeEl = document.getElementById('scan-time');
        if (timeEl) timeEl.textContent = details.timestamp || '';
        const author = document.getElementById('scan-author');
        if (author) author.textContent = details.author || 'patchy-bot';

        // Severity counts
        const summary = details.summary || {critical: 0, high: 0, moderate: 0};
        const crit = document.getElementById('count-critical');
        if (crit) crit.textContent = summary.critical || 0;
        const high = document.getElementById('count-high');
        if (high) high.textContent = summary.high || 0;
        const mod = document.getElementById('count-moderate');
        if (mod) mod.textContent = summary.moderate || 0;

        // Severity bar color
        const bar = document.getElementById('severity-bar');
        if (bar) {
            if (summary.critical > 0) bar.className = 'absolute top-0 left-0 w-1 h-full bg-error';
            else if (summary.high > 0) bar.className = 'absolute top-0 left-0 w-1 h-full bg-tertiary';
            else bar.className = 'absolute top-0 left-0 w-1 h-full bg-secondary';
        }

        // Error/Warning Banner
        if (details.error) {
            const errorBanner = document.createElement('div');
            errorBanner.className = 'bg-error/10 border border-error/30 rounded-lg p-4 flex items-start gap-3';
            errorBanner.innerHTML = `
                <span class="material-symbols-outlined text-error text-[24px]">error</span>
                <div class="flex-1">
                    <h3 class="font-body-md-bold text-body-md-bold text-error mb-1">Scan Error</h3>
                    <p class="text-on-surface-variant font-body-sm text-body-sm">${escapeHtml(details.error)}</p>
                </div>
            `;
            const mainContent = document.querySelector('.max-w-5xl');
            if (mainContent) {
                mainContent.insertBefore(errorBanner, document.getElementById('pr-link-container'));
            }
        }

        // PR link
        const prContainer = document.getElementById('pr-link-container');
        const prLink = document.getElementById('view-pr-link');
        if (prLink && details.pr_url) {
            prLink.href = details.pr_url;
            prLink.innerHTML = `
                <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"></path></svg>
                View Pull Request${details.pr_number ? ' #' + details.pr_number : ''}`;
        } else if (prContainer && !details.pr_url) {
            // Hide PR button if no PR
            if (prLink) prLink.style.display = 'none';
            
            // Show warning if fixes were generated but no PR
            if (details.fixes_generated > 0 && !details.error) {
                const warningBanner = document.createElement('div');
                warningBanner.className = 'bg-tertiary/10 border border-tertiary/30 rounded-lg p-4 flex items-start gap-3';
                warningBanner.innerHTML = `
                    <span class="material-symbols-outlined text-tertiary text-[24px]">warning</span>
                    <div class="flex-1">
                        <h3 class="font-body-md-bold text-body-md-bold text-tertiary mb-1">No Pull Request Created</h3>
                        <p class="text-on-surface-variant font-body-sm text-body-sm">
                            ${details.fixes_generated} fix(es) were generated but ${details.fixes_valid || 0} passed validation. 
                            ${details.fixes_valid === 0 ? 'All fixes failed validation checks.' : 'PR creation may have failed.'}
                        </p>
                    </div>
                `;
                const mainContent = document.querySelector('.max-w-5xl');
                if (mainContent) {
                    mainContent.insertBefore(warningBanner, prContainer);
                }
            }
        }

        // Findings
        const findings = details.findings || [];
        if (findings.length === 0) {
            findingsList.innerHTML = `
                <div class="text-center py-12 bg-surface-container-low rounded-lg border border-outline-variant">
                    <span class="material-symbols-outlined text-[48px] text-secondary mb-3 block" style="font-variation-settings: 'FILL' 1;">verified</span>
                    <h3 class="font-h3 text-h3 text-secondary mb-2">All Clear!</h3>
                    <p class="text-on-surface-variant font-body-md">No vulnerabilities detected in this scan.</p>
                </div>`;
        } else {
            findingsList.innerHTML = findings.map(f => renderFindingCard(f)).join('');
        }
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

    const desc = finding.description || finding.message || 'No description';
    const fixBadge = finding.fix_status === 'applied'
        ? '<span class="bg-secondary/10 text-secondary border border-secondary/30 px-2 py-0.5 rounded text-[11px] font-bold ml-2">FIXED</span>'
        : '';

    let expandedContent = '';
    if (finding.is_expanded && (finding.fix_explanation || finding.fix_diff)) {
        let explanationHtml = '';
        if (finding.fix_explanation) {
            explanationHtml = `
                <div class="bg-surface-container-highest px-4 py-2 text-on-surface-variant flex items-center gap-2 border-b border-outline-variant">
                    <span class="material-symbols-outlined text-sm">auto_fix_high</span> Fix Explanation
                </div>
                <div class="p-4 bg-[#0d1117] text-on-surface-variant text-body-sm">${escapeHtml(finding.fix_explanation)}</div>
            `;
        }
        
        let diffHtml = '';
        if (finding.fix_diff) {
            diffHtml = `
                <div class="bg-surface-container-highest px-4 py-2 text-on-surface-variant flex items-center gap-2 border-b border-t border-outline-variant">
                    <span class="material-symbols-outlined text-sm">difference</span> Code Changes
                </div>
                <div class="bg-[#0d1117] py-2 overflow-x-auto">
                    ${colorizeDiff(finding.fix_diff)}
                </div>
            `;
        }

        expandedContent = `
            <div class="p-4 bg-surface-container border-t border-outline-variant">
                <div class="font-mono text-mono rounded overflow-hidden border border-outline-variant">
                    ${explanationHtml}
                    ${diffHtml}
                </div>
            </div>`;
    }

    const btnClass = finding.is_expanded
        ? 'bg-primary text-on-primary hover:bg-primary-fixed shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]'
        : 'border border-outline-variant text-on-surface hover:bg-surface-container-high';
    const chevron = finding.is_expanded ? 'expand_more' : 'chevron_right';
    const hasFixContent = finding.fix_explanation || finding.fix_status === 'applied';

    return `
        <div class="bg-surface-container-low rounded-lg border border-outline-variant overflow-hidden hover:border-primary-container transition-colors mb-4" data-finding-id="${finding.id}">
            <div class="p-4 ${finding.is_expanded ? 'border-b border-outline-variant bg-surface-container-lowest' : ''} flex items-start justify-between gap-4">
                <div class="flex gap-3 items-start">
                    <div class="mt-1 ${iconClass} ${iconBg} p-1.5 rounded"><span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">${iconName}</span></div>
                    <div>
                        <h3 class="font-body-lg text-body-lg text-on-surface font-semibold">${escapeHtml(finding.type)}${fixBadge}</h3>
                        <p class="font-body-sm text-body-sm text-on-surface-variant mt-1">${escapeHtml(desc)}</p>
                        <div class="mt-3 flex items-center gap-2 font-mono text-mono text-on-surface-variant bg-surface-container-highest px-2 py-1 rounded border border-outline-variant inline-block">
                            <span class="material-symbols-outlined text-sm">code</span> ${escapeHtml(finding.file)}:${finding.line}
                        </div>
                    </div>
                </div>
                ${hasFixContent ? `<button class="${btnClass} px-4 py-2 rounded font-body-sm text-body-sm transition-colors flex items-center gap-2 whitespace-nowrap" onclick="toggleFinding('${finding.id}')">
                    View Fix <span class="material-symbols-outlined text-sm">${chevron}</span>
                </button>` : ''}
            </div>
            ${expandedContent}
        </div>`;
}

function toggleFinding(findingId) {
    if (!_scanDetailData || !_scanDetailData.findings) return;
    const finding = _scanDetailData.findings.find(f => f.id === findingId);
    if (finding) {
        finding.is_expanded = !finding.is_expanded;
        const list = document.getElementById('findings-list');
        if (list) list.innerHTML = _scanDetailData.findings.map(f => renderFindingCard(f)).join('');
    }
}

function rescan() {
    showToast('Re-scanning repository...', 'info');
    // TODO: implement actual rescan
}

function colorizeDiff(diffStr) {
    if (!diffStr) return '';
    return diffStr.split('\n').map(line => {
        const escaped = escapeHtml(line);
        if (line.startsWith('+') && !line.startsWith('+++')) {
            return `<div class="bg-secondary/10 text-[#7ee787] px-4 py-0.5 whitespace-pre font-mono text-[13px]">${escaped}</div>`;
        } else if (line.startsWith('-') && !line.startsWith('---')) {
            return `<div class="bg-error/10 text-[#ff7b72] px-4 py-0.5 whitespace-pre font-mono text-[13px]">${escaped}</div>`;
        } else if (line.startsWith('@@')) {
            return `<div class="text-[#79c0ff] px-4 py-2 whitespace-pre font-mono text-[13px] mt-2 border-t border-outline-variant/30">${escaped}</div>`;
        } else if (line.startsWith('---') || line.startsWith('+++')) {
            return `<div class="text-on-surface-variant px-4 py-1 whitespace-pre font-mono text-[13px] font-bold">${escaped}</div>`;
        } else {
            return `<div class="text-on-surface-variant px-4 py-0.5 whitespace-pre font-mono text-[13px] opacity-70">${escaped}</div>`;
        }
    }).join('');
}
