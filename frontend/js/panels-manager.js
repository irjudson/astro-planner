// ==========================================
// PANELS MANAGER
// Handles collapsible panels in sidebar
// ==========================================

const PanelsManager = {
    init() {
        this.setupPanelCollapse();
    },

    setupPanelCollapse() {
        // Find all collapsible panels
        const collapsiblePanels = document.querySelectorAll('.panel-collapsible');

        collapsiblePanels.forEach(panel => {
            const header = panel.querySelector('.panel-header');
            if (header) {
                header.addEventListener('click', () => {
                    this.togglePanel(panel);
                });
            }
        });
    },

    togglePanel(panel) {
        panel.classList.toggle('collapsed');

        // Update chevron
        const chevron = panel.querySelector('.panel-chevron');
        if (chevron) {
            if (panel.classList.contains('collapsed')) {
                chevron.textContent = '▶';
            } else {
                chevron.textContent = '▼';
            }
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    PanelsManager.init();
});
