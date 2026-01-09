// ==========================================
// EXECUTION TABS MANAGER
// Handles tab switching in Execution view
// ==========================================

const ExecutionTabs = {
    currentTab: 'execution',

    init() {
        this.setupTabSwitching();
        this.setupLibraryTab();
        this.setupTelemetryTab();
        this.setupLiveViewTab();
    },

    setupTabSwitching() {
        const tabButtons = document.querySelectorAll('.execution-tab');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;
                this.switchTab(tabName);
            });
        });
    },

    switchTab(tabName) {
        // Update button states
        const tabButtons = document.querySelectorAll('.execution-tab');
        tabButtons.forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update pane visibility
        const panes = document.querySelectorAll('.tab-pane');
        panes.forEach(pane => {
            if (pane.id === `${tabName}-tab`) {
                pane.classList.add('active');
            } else {
                pane.classList.remove('active');
            }
        });

        this.currentTab = tabName;
        AppState.execution.activeTab = tabName;
        AppState.save();

        // Load content for the tab if needed
        if (tabName === 'library') {
            this.loadLibrary();
        } else if (tabName === 'telemetry') {
            this.updateTelemetry();
        } else if (tabName === 'liveview') {
            // Live view loading happens on button click
        }
    },

    // ==========================================
    // LIBRARY TAB
    // ==========================================

    setupLibraryTab() {
        // Search input
        const searchInput = document.getElementById('library-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterLibrary(e.target.value);
            });
        }

        // Filter dropdown
        const filterSelect = document.getElementById('library-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', () => {
                this.loadLibrary();
            });
        }

        // Sort dropdown
        const sortSelect = document.getElementById('library-sort');
        if (sortSelect) {
            sortSelect.addEventListener('change', () => {
                this.loadLibrary();
            });
        }

        // Transfer files button
        const transferBtn = document.getElementById('transfer-files-btn');
        if (transferBtn) {
            transferBtn.addEventListener('click', () => {
                this.transferFiles();
            });
        }
    },

    async loadLibrary() {
        const grid = document.getElementById('library-grid');
        if (!grid) return;

        grid.innerHTML = '<p class="text-secondary">Loading...</p>';

        try {
            const response = await fetch('/api/captures');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const captures = await response.json();
            AppState.execution.library = captures;

            this.renderLibrary(captures);
        } catch (error) {
            console.error('Failed to load library:', error);
            grid.innerHTML = '<p class="text-secondary">Failed to load capture history</p>';
        }
    },

    renderLibrary(captures) {
        const grid = document.getElementById('library-grid');
        if (!grid) return;

        // Apply filters
        const filter = document.getElementById('library-filter')?.value || 'all';
        const sort = document.getElementById('library-sort')?.value || 'recent';

        let filtered = [...captures];

        // Apply status filter
        if (filter !== 'all') {
            filtered = filtered.filter(c => c.status === filter);
        }

        // Apply sort
        switch (sort) {
            case 'recent':
                filtered.sort((a, b) => {
                    const dateB = b.last_captured_at ? new Date(b.last_captured_at) : new Date(0);
                    const dateA = a.last_captured_at ? new Date(a.last_captured_at) : new Date(0);
                    return dateB - dateA;
                });
                break;
            case 'name':
                filtered.sort((a, b) => {
                    const nameA = a.catalog_id || '';
                    const nameB = b.catalog_id || '';
                    return nameA.localeCompare(nameB);
                });
                break;
            case 'exposure':
                filtered.sort((a, b) => (b.total_exposure_seconds || 0) - (a.total_exposure_seconds || 0));
                break;
            case 'quality':
                filtered.sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
                break;
        }

        if (filtered.length === 0) {
            grid.innerHTML = '<p class="text-secondary">No targets found</p>';
            return;
        }

        // Render cards
        grid.innerHTML = filtered.map(capture => `
            <div class="target-card" data-catalog-id="${this.escapeHtml(capture.catalog_id)}">
                <h4>${this.escapeHtml(capture.catalog_id)}</h4>
                <div style="margin-bottom: 8px;">
                    <span class="status-badge status-${capture.status}">
                        ${this.getStatusIcon(capture.status)} ${this.formatStatus(capture.status)}
                    </span>
                </div>
                <p class="text-sm text-secondary">
                    ${capture.total_frames || 0} frames &bull; ${this.formatExposureTime(capture.total_exposure_seconds || 0)}
                </p>
                <p class="text-xs text-tertiary">${this.formatDate(capture.last_captured_at)}</p>
            </div>
        `).join('');

        // Add click handlers
        grid.querySelectorAll('.target-card').forEach(card => {
            card.addEventListener('click', () => {
                this.viewTargetDetails(card.dataset.catalogId);
            });
        });
    },

    filterLibrary(searchTerm) {
        const cards = document.querySelectorAll('.target-card');
        cards.forEach(card => {
            const catalogId = card.dataset.catalogId.toLowerCase();
            if (catalogId.includes(searchTerm.toLowerCase())) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    },

    viewTargetDetails(catalogId) {
        const target = AppState.execution.library.find(t => t.catalog_id === catalogId);
        if (!target) return;

        alert(`Target: ${target.catalog_id}\n` +
              `Status: ${this.formatStatus(target.status)}\n` +
              `Frames: ${target.total_frames || 0}\n` +
              `Exposure: ${this.formatExposureTime(target.total_exposure_seconds || 0)}\n` +
              `Quality: ${target.quality_score ? Math.round(target.quality_score) : 'N/A'}`);
    },

    async transferFiles() {
        if (!confirm('Transfer all new files from telescope to local storage?')) {
            return;
        }

        try {
            const response = await fetch('/api/captures/transfer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            alert(`Transfer complete: ${result.transferred || 0} files transferred, ${result.errors || 0} errors`);

            // Reload library
            this.loadLibrary();
        } catch (error) {
            console.error('Transfer failed:', error);
            alert('Transfer failed: ' + error.message);
        }
    },

    // ==========================================
    // TELEMETRY TAB
    // ==========================================

    setupTelemetryTab() {
        // Telemetry updates are handled by execution-manager.js
        // We just need to trigger updates when switching to this tab
    },

    updateTelemetry() {
        // Trigger telemetry update if execution manager is available
        if (window.ExecutionManager && window.ExecutionManager.updateTelescopeStatus) {
            ExecutionManager.updateTelescopeStatus();
        }
    },

    // ==========================================
    // LIVE VIEW TAB
    // ==========================================

    setupLiveViewTab() {
        const startBtn = document.getElementById('start-liveview-btn');
        const stopBtn = document.getElementById('stop-liveview-btn');
        const snapshotBtn = document.getElementById('snapshot-btn');

        if (startBtn) {
            startBtn.addEventListener('click', () => {
                this.startLiveView();
            });
        }

        if (stopBtn) {
            stopBtn.addEventListener('click', () => {
                this.stopLiveView();
            });
        }

        if (snapshotBtn) {
            snapshotBtn.addEventListener('click', () => {
                this.takeSnapshot();
            });
        }
    },

    async startLiveView() {
        // TODO: Implement live view streaming
        alert('Live view functionality coming soon!');
    },

    stopLiveView() {
        // TODO: Stop live view stream
    },

    takeSnapshot() {
        // TODO: Capture snapshot from live view
        alert('Snapshot functionality coming soon!');
    },

    // ==========================================
    // HELPER FUNCTIONS
    // ==========================================

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    getStatusIcon(status) {
        switch (status) {
            case 'complete':
                return '✓';
            case 'needs_more':
                return '⚠';
            case 'new':
                return '○';
            default:
                return '';
        }
    },

    formatStatus(status) {
        switch (status) {
            case 'complete':
                return 'Complete';
            case 'needs_more':
                return 'Needs More';
            case 'new':
                return 'New';
            default:
                return status;
        }
    },

    formatExposureTime(seconds) {
        if (!seconds) return '0m';

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    },

    formatDate(dateStr) {
        if (!dateStr) return 'Unknown';

        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) {
            return 'Today';
        } else if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays < 7) {
            return `${diffDays} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    },

    formatRA(hours) {
        if (hours === null || hours === undefined || isNaN(hours)) {
            return '--:--:--';
        }

        hours = ((hours % 24) + 24) % 24;

        const h = Math.floor(hours);
        const m = Math.floor((hours - h) * 60);
        const s = Math.floor(((hours - h) * 60 - m) * 60);
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    },

    formatDec(degrees) {
        if (degrees === null || degrees === undefined || isNaN(degrees)) {
            return '--°--\'--"';
        }

        degrees = Math.max(-90, Math.min(90, degrees));

        const sign = degrees >= 0 ? '+' : '-';
        const absDeg = Math.abs(degrees);
        const d = Math.floor(absDeg);
        const m = Math.floor((absDeg - d) * 60);
        const s = Math.floor(((absDeg - d) * 60 - m) * 60);
        return `${sign}${d}°${m.toString().padStart(2, '0')}'${s.toString().padStart(2, '0')}"`;
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    ExecutionTabs.init();

    // Restore active tab from state
    if (AppState.execution.activeTab) {
        ExecutionTabs.switchTab(AppState.execution.activeTab);
    }
});
