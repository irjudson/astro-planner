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

        // Placeholder drawer content based on context
        const drawerContent = {
            discovery: '<p>Advanced catalog filters and queries</p>',
            planning: '<p>Advanced planning constraints and optimization</p>',
            execution: '<p>Advanced imaging controls and system diagnostics</p>',
            processing: '<p>Advanced processing parameters and batch operations</p>'
        };

        drawerTabs.innerHTML = drawerContent[context] || '';
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    AppContext.init();
    console.log('AppContext initialized');
});
