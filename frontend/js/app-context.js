// ==========================================
// CONTEXT MANAGER - Controls workflow switching
// ==========================================

const AppContext = {
    // Initialize context manager
    init() {
        this.setupWorkflowToggle();
        this.setupDrawerToggle();
        this.setupMobileMenu();

        // Restore context from URL hash or AppState
        const hashContext = window.location.hash.replace('#/', '');
        const initialContext = hashContext || AppState.currentContext || 'discovery';

        if (initialContext !== 'discovery') {
            this.switchContext(initialContext);
        } else {
            this.updateMainContent('discovery');
            this.updateDrawerContent('discovery');
        }

        this.restoreUIState();
    },

    // Setup workflow section expand/collapse
    setupWorkflowToggle() {
        const workflowHeaders = document.querySelectorAll('.workflow-header');

        workflowHeaders.forEach(header => {
            header.addEventListener('click', () => {
                const workflow = header.dataset.workflow;

                // Toggle the workflow section
                this.toggleWorkflowSection(workflow);

                // Switch context when workflow is expanded
                const section = document.getElementById(`${workflow}-section`);
                if (section && !section.classList.contains('collapsed')) {
                    this.switchContext(workflow);
                }
            });
        });
    },

    // Toggle workflow section expanded/collapsed
    toggleWorkflowSection(workflow) {
        const section = document.getElementById(`${workflow}-section`);
        if (!section) return;

        const isCollapsed = section.classList.contains('collapsed');

        if (isCollapsed) {
            section.classList.remove('collapsed');
            AppState.workflowSections[workflow].expanded = true;

            // When planning section is expanded, refresh location defaults
            if (workflow === 'planning' && window.PlanningControls) {
                PlanningControls.updateLocationDefaults();
            }
        } else {
            section.classList.add('collapsed');
            AppState.workflowSections[workflow].expanded = false;
        }

        AppState.save();
    },

    // Setup drawer toggle
    setupDrawerToggle() {
        const toggle = document.getElementById('drawer-toggle');
        const drawer = document.getElementById('app-drawer');

        if (toggle && drawer) {
            toggle.addEventListener('click', () => {
                drawer.classList.toggle('closed');
                AppState.drawer.isOpen = !drawer.classList.contains('closed');
                AppState.save();

                // Force content reflow after drawer animation completes (250ms)
                setTimeout(() => {
                    window.dispatchEvent(new Event('resize'));
                }, 250);
            });
        }
    },

    // Setup mobile menu
    setupMobileMenu() {
        const menuToggle = document.getElementById('mobile-menu-toggle');
        const sidebar = document.getElementById('app-sidebar');
        const backdrop = document.getElementById('mobile-backdrop');

        if (menuToggle && sidebar && backdrop) {
            menuToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
                backdrop.classList.toggle('visible');
                AppState.mobile.sidebarOpen = sidebar.classList.contains('open');
            });

            backdrop.addEventListener('click', () => {
                sidebar.classList.remove('open');
                backdrop.classList.remove('visible');
                AppState.mobile.sidebarOpen = false;
            });
        }
    },

    // Restore UI state from AppState
    restoreUIState() {
        // Restore workflow section states
        Object.keys(AppState.workflowSections).forEach(workflow => {
            const section = document.getElementById(`${workflow}-section`);
            if (section) {
                if (AppState.workflowSections[workflow].expanded) {
                    section.classList.remove('collapsed');
                } else {
                    section.classList.add('collapsed');
                }
            }
        });

        // Restore drawer state
        const drawer = document.getElementById('app-drawer');
        if (drawer) {
            if (AppState.drawer.isOpen) {
                drawer.classList.remove('closed');
            } else {
                drawer.classList.add('closed');
            }
        }
    },

    // Switch to a specific context
    switchContext(newContext) {
        if (AppState.currentContext === newContext) return;

        const mainContent = document.getElementById('main-content');
        if (!mainContent) return;

        // Fade out
        mainContent.style.opacity = '0';

        setTimeout(() => {
            // Update state
            AppState.currentContext = newContext;

            // Update main content
            this.updateMainContent(newContext);

            // Update drawer content
            this.updateDrawerContent(newContext);

            // When switching to planning, refresh location defaults
            if (newContext === 'planning' && window.PlanningControls) {
                PlanningControls.updateLocationDefaults();
            }

            // Update URL hash
            window.location.hash = `/${newContext}`;

            // Save state
            AppState.save();

            // Fade in
            setTimeout(() => {
                mainContent.style.opacity = '1';
            }, 50);
        }, 200);
    },

    // Update main content area based on context
    updateMainContent(context) {
        const mainContent = document.getElementById('main-content');
        if (!mainContent) return;

        // Hide all context views
        const catalogView = document.getElementById('catalog-view');
        const planningView = document.getElementById('planning-view');
        const executionView = document.getElementById('execution-view');
        const processingView = document.getElementById('processing-view');

        if (catalogView) catalogView.style.display = 'none';
        if (planningView) planningView.style.display = 'none';
        if (executionView) executionView.style.display = 'none';
        if (processingView) processingView.style.display = 'none';

        // Show appropriate view
        switch (context) {
            case 'discovery':
                if (catalogView) catalogView.style.display = 'block';
                break;
            case 'planning':
                if (planningView) planningView.style.display = 'block';
                break;
            case 'execution':
                if (executionView) executionView.style.display = 'block';
                break;
            case 'processing':
                if (processingView) processingView.style.display = 'block';
                break;
        }
    },

    // Update drawer content based on context
    updateDrawerContent(context) {
        const drawerTabs = document.getElementById('drawer-tabs');
        if (!drawerTabs) return;

        // Context-specific drawer content
        const drawerContent = {
            discovery: this.getDiscoveryDrawerContent(),
            planning: this.getPlanningDrawerContent(),
            execution: this.getExecutionDrawerContent(),
            processing: this.getProcessingDrawerContent()
        };

        drawerTabs.innerHTML = drawerContent[context] || '';
    },

    getDiscoveryDrawerContent() {
        return `
            <div class="drawer-section">
                <h4>Advanced Filters</h4>
                <div class="filter-grid">
                    <div class="filter-item">
                        <label>Magnitude Range</label>
                        <div class="range-inputs">
                            <input type="number" id="mag-min" placeholder="Min" step="0.1" class="form-control form-control-sm">
                            <span>to</span>
                            <input type="number" id="mag-max" placeholder="Max" step="0.1" class="form-control form-control-sm">
                        </div>
                    </div>
                    <div class="filter-item">
                        <label>Size Range (arcmin)</label>
                        <div class="range-inputs">
                            <input type="number" id="size-min" placeholder="Min" class="form-control form-control-sm">
                            <span>to</span>
                            <input type="number" id="size-max" placeholder="Max" class="form-control form-control-sm">
                        </div>
                    </div>
                    <div class="filter-item">
                        <label>Altitude at Time</label>
                        <div class="range-inputs">
                            <input type="time" id="alt-time" class="form-control form-control-sm">
                            <input type="number" id="alt-min" placeholder="Min °" class="form-control form-control-sm">
                        </div>
                    </div>
                </div>
                <button class="btn btn-primary btn-sm" id="apply-advanced-filters">Apply Filters</button>
            </div>
        `;
    },

    getPlanningDrawerContent() {
        return `
            <div class="drawer-section">
                <h4>Planning Constraints</h4>
                <div class="constraint-grid">
                    <div class="constraint-item">
                        <label>
                            <input type="checkbox" id="avoid-moon" checked>
                            Avoid Moon (>30° separation)
                        </label>
                    </div>
                    <div class="constraint-item">
                        <label>Min Target Altitude</label>
                        <input type="number" id="min-altitude" value="30" min="0" max="90" class="form-control form-control-sm">
                    </div>
                    <div class="constraint-item">
                        <label>Max Airmass</label>
                        <input type="number" id="max-airmass" value="2.0" step="0.1" class="form-control form-control-sm">
                    </div>
                    <div class="constraint-item">
                        <label>Min Target Duration (min)</label>
                        <input type="number" id="min-duration" value="20" class="form-control form-control-sm">
                    </div>
                </div>
            </div>
        `;
    },

    getExecutionDrawerContent() {
        return `
            <div class="drawer-section">
                <h4>System Diagnostics</h4>
                <div class="diagnostic-grid">
                    <div class="diagnostic-item">
                        <label>CPU Usage:</label>
                        <span class="diagnostic-value">--</span>
                    </div>
                    <div class="diagnostic-item">
                        <label>Memory:</label>
                        <span class="diagnostic-value">--</span>
                    </div>
                    <div class="diagnostic-item">
                        <label>Disk Space:</label>
                        <span class="diagnostic-value">--</span>
                    </div>
                    <div class="diagnostic-item">
                        <label>Network:</label>
                        <span class="diagnostic-value">--</span>
                    </div>
                </div>
                <h4 style="margin-top: 20px;">Image Preview Settings</h4>
                <div class="preview-settings">
                    <label>
                        <input type="checkbox" id="auto-stretch" checked>
                        Auto-stretch preview images
                    </label>
                    <label>
                        <input type="checkbox" id="show-stats">
                        Show image statistics overlay
                    </label>
                </div>
            </div>
        `;
    },

    getProcessingDrawerContent() {
        return `
            <div class="drawer-section">
                <h4>Batch Processing</h4>
                <div class="batch-controls">
                    <button class="btn btn-secondary btn-sm">Select All New</button>
                    <button class="btn btn-secondary btn-sm">Select All Needs More</button>
                    <button class="btn btn-primary btn-sm">Batch Stack Selected</button>
                </div>
                <h4 style="margin-top: 20px;">Quality Thresholds</h4>
                <div class="quality-settings">
                    <div class="quality-item">
                        <label>Min FWHM (arcsec)</label>
                        <input type="number" id="min-fwhm" value="2.5" step="0.1" class="form-control form-control-sm">
                    </div>
                    <div class="quality-item">
                        <label>Max Eccentricity</label>
                        <input type="number" id="max-ecc" value="0.3" step="0.05" class="form-control form-control-sm">
                    </div>
                </div>
            </div>
        `;
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    AppContext.init();
    console.log('AppContext initialized');
});

// Make AppContext globally accessible
window.AppContext = AppContext;
