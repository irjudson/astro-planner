// ==========================================
// CONTEXT MANAGER - Controls workflow switching
// ==========================================

const AppContext = {
    // Initialize context manager
    init() {
        this.setupWorkflowToggle();
        this.setupDrawerToggle();
        this.setupMobileMenu();
        this.restoreUIState();
    },

    // Setup workflow section expand/collapse
    setupWorkflowToggle() {
        const workflowHeaders = document.querySelectorAll('.workflow-header');
        workflowHeaders.forEach(header => {
            header.addEventListener('click', (e) => {
                const workflow = header.dataset.workflow;
                this.toggleWorkflowSection(workflow);
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

        console.log(`Switching context: ${AppState.currentContext} → ${newContext}`);

        AppState.currentContext = newContext;
        AppState.save();

        // Update main content area
        this.updateMainContent(newContext);

        // Update drawer content
        this.updateDrawerContent(newContext);
    },

    // Update main content area based on context
    updateMainContent(context) {
        const mainContent = document.getElementById('main-content');
        if (!mainContent) return;

        // Add fade out
        mainContent.style.opacity = '0';

        setTimeout(() => {
            // Update content based on context
            switch (context) {
                case 'discovery':
                    mainContent.innerHTML = '<h2>Catalog Grid</h2><p>Discovery content coming soon</p>';
                    break;
                case 'planning':
                    mainContent.innerHTML = '<h2>Planning Results</h2><p>Planning content coming soon</p>';
                    break;
                case 'execution':
                    mainContent.innerHTML = '<h2>Execution View</h2><p>Execution content coming soon</p>';
                    break;
                case 'processing':
                    mainContent.innerHTML = '<h2>Processing Workspace</h2><p>Processing content coming soon</p>';
                    break;
            }

            // Fade in
            mainContent.style.opacity = '1';
        }, 200);
    },

    // Update drawer content based on context
    updateDrawerContent(context) {
        const drawerTabs = document.getElementById('drawer-tabs');
        if (!drawerTabs) return;

        drawerTabs.style.opacity = '0';

        setTimeout(() => {
            switch (context) {
                case 'discovery':
                    drawerTabs.innerHTML = '<p>Discovery drawer: Advanced Filters, Custom Queries</p>';
                    break;
                case 'planning':
                    drawerTabs.innerHTML = '<p>Planning drawer: Constraints, Optimization</p>';
                    break;
                case 'execution':
                    drawerTabs.innerHTML = '<p>Execution drawer: Advanced Imaging, System, WiFi, Calibration, Hardware</p>';
                    break;
                case 'processing':
                    drawerTabs.innerHTML = '<p>Processing drawer: Processing Parameters, Batch Operations</p>';
                    break;
            }

            drawerTabs.style.opacity = '1';
        }, 150);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    AppContext.init();
    console.log('AppContext initialized');
});
