// ==========================================
// PREFERENCES MANAGER
// ==========================================

const PreferencesManager = {
    init() {
        this.setupEventListeners();
        this.loadCurrentPreferences();
    },

    setupEventListeners() {
        const settingsBtn = document.getElementById('settings-btn');
        const settingsModal = document.getElementById('settings-modal');
        const settingsCloseBtn = document.getElementById('settings-modal-close');
        const unitsToggle = document.getElementById('units-toggle');

        // Open settings modal
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.openSettings();
            });
        }

        // Close settings modal
        if (settingsCloseBtn) {
            settingsCloseBtn.addEventListener('click', () => {
                this.closeSettings();
            });
        }

        // Close on backdrop click
        if (settingsModal) {
            settingsModal.addEventListener('click', (e) => {
                if (e.target === settingsModal) {
                    this.closeSettings();
                }
            });
        }

        // Units toggle
        if (unitsToggle) {
            unitsToggle.addEventListener('change', (e) => {
                this.updateUnits(e.target.value);
            });
        }
    },

    openSettings() {
        const settingsModal = document.getElementById('settings-modal');
        if (settingsModal) {
            settingsModal.style.display = 'flex';
            this.loadCurrentPreferences();
        }
    },

    closeSettings() {
        const settingsModal = document.getElementById('settings-modal');
        if (settingsModal) {
            settingsModal.style.display = 'none';
        }
    },

    loadCurrentPreferences() {
        const unitsToggle = document.getElementById('units-toggle');
        if (unitsToggle) {
            unitsToggle.value = AppState.preferences.units;
        }
    },

    updateUnits(units) {
        AppState.preferences.units = units;
        AppState.save();

        // Trigger update of all displays that use units
        if (window.WeatherWidget) {
            WeatherWidget.updateDisplay();
        }

        // Future: trigger updates for other components
        // CatalogSearch.updateDisplay();
        // PlanningControls.updateDisplay();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    PreferencesManager.init();
});
