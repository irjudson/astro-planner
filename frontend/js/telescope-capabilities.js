// ==========================================
// TELESCOPE CAPABILITIES MANAGER
// ==========================================

const TelescopeCapabilities = {
    capabilities: null,
    features: null,
    telescopeType: null,

    async init() {
        // Load capabilities when telescope connects
        document.addEventListener('telescope-connected', () => {
            this.loadCapabilities();
        });

        document.addEventListener('telescope-disconnected', () => {
            this.clearCapabilities();
        });

        // Load capabilities if already connected
        if (AppState.connection.isConnected) {
            this.loadCapabilities();
        }
    },

    async loadCapabilities() {
        try {
            const response = await fetch('/api/telescope/features/capabilities');

            if (!response.ok) {
                throw new Error('Failed to load capabilities');
            }

            const data = await response.json();

            this.telescopeType = data.telescope_type;
            this.capabilities = data.capabilities;
            this.features = data.features;

            console.log('Telescope capabilities loaded:', {
                type: this.telescopeType,
                capabilities: this.capabilities,
                features: this.features
            });

            // Dispatch event for UI components to update
            document.dispatchEvent(new CustomEvent('telescope-capabilities-loaded', {
                detail: {
                    type: this.telescopeType,
                    capabilities: this.capabilities,
                    features: this.features
                }
            }));

            // Update UI components
            this.updateUIForCapabilities();
        } catch (error) {
            console.error('Failed to load telescope capabilities:', error);
        }
    },

    clearCapabilities() {
        this.telescopeType = null;
        this.capabilities = null;
        this.features = null;

        document.dispatchEvent(new Event('telescope-capabilities-cleared'));
    },

    hasCapability(capability) {
        return this.capabilities && this.capabilities[capability] === true;
    },

    hasFeature(category, feature) {
        return this.features &&
               this.features[category] &&
               this.features[category][feature] === true;
    },

    getFeatureCategories() {
        return this.features ? Object.keys(this.features) : [];
    },

    getFeaturesInCategory(category) {
        return this.features && this.features[category] ? this.features[category] : {};
    },

    updateUIForCapabilities() {
        // Show/hide panels based on capabilities
        this.updateHardwarePanel();
        this.updateImagingPanel();
        this.updateAdvancedFeatures();
    },

    updateHardwarePanel() {
        const hardwarePanel = document.getElementById('hardware-panel');
        if (!hardwarePanel) return;

        // Show hardware panel if any hardware features available
        const hasHardwareFeatures = this.features && this.features.hardware;
        if (hasHardwareFeatures) {
            hardwarePanel.style.display = 'block';
            this.populateHardwareControls();
        } else {
            hardwarePanel.style.display = 'none';
        }
    },

    updateImagingPanel() {
        const imagingPanel = document.getElementById('imaging-panel');
        if (!imagingPanel) return;

        // Add imaging-specific controls based on features
        if (this.hasFeature('imaging', 'dithering')) {
            this.showDitheringControls();
        }

        if (this.hasFeature('imaging', 'manual_exposure')) {
            this.showManualExposureControls();
        }
    },

    updateAdvancedFeatures() {
        // Check if we should show advanced drawer tabs
        const hasAdvancedFeatures = this.features && (
            this.features.wifi ||
            this.features.alignment ||
            this.features.system ||
            this.features.advanced
        );

        if (hasAdvancedFeatures) {
            this.createAdvancedDrawerTabs();
        }
    },

    populateHardwareControls() {
        const hardwareBody = document.querySelector('#hardware-panel .panel-body');
        if (!hardwareBody) return;

        let html = '';

        // Dew Heater
        if (this.hasFeature('hardware', 'dew_heater')) {
            html += `
                <div class="hardware-control">
                    <div class="control-header">
                        <label>Dew Heater</label>
                        <div class="control-actions">
                            <button class="btn btn-sm btn-secondary" id="dew-heater-off">Off</button>
                            <button class="btn btn-sm btn-primary" id="dew-heater-on">On</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="dew-heater-power">Power Level (%)</label>
                        <input type="range" id="dew-heater-power" min="0" max="100" value="90" class="form-range">
                        <span id="dew-heater-power-value">90%</span>
                    </div>
                </div>
            `;
        }

        // DC Output
        if (this.hasFeature('hardware', 'dc_output')) {
            html += `
                <div class="hardware-control">
                    <label>DC Output</label>
                    <div class="control-actions">
                        <button class="btn btn-sm btn-secondary" id="dc-output-off">Off</button>
                        <button class="btn btn-sm btn-primary" id="dc-output-on">On</button>
                    </div>
                </div>
            `;
        }

        hardwareBody.innerHTML = html;

        // Wire up event listeners
        this.setupHardwareEventListeners();
    },

    setupHardwareEventListeners() {
        const dewHeaterOn = document.getElementById('dew-heater-on');
        const dewHeaterOff = document.getElementById('dew-heater-off');
        const dewHeaterPower = document.getElementById('dew-heater-power');
        const dewHeaterPowerValue = document.getElementById('dew-heater-power-value');

        if (dewHeaterPower && dewHeaterPowerValue) {
            dewHeaterPower.addEventListener('input', (e) => {
                dewHeaterPowerValue.textContent = `${e.target.value}%`;
            });
        }

        if (dewHeaterOn) {
            dewHeaterOn.addEventListener('click', () => this.setDewHeater(true));
        }

        if (dewHeaterOff) {
            dewHeaterOff.addEventListener('click', () => this.setDewHeater(false));
        }
    },

    async setDewHeater(enabled) {
        const powerLevel = parseInt(document.getElementById('dew-heater-power')?.value || 90);

        try {
            const response = await fetch('/api/telescope/features/hardware/dew-heater', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    enabled: enabled,
                    power_level: powerLevel
                })
            });

            if (!response.ok) {
                throw new Error('Failed to set dew heater');
            }

            const data = await response.json();
            console.log('Dew heater updated:', data);

            // Update button states
            const onBtn = document.getElementById('dew-heater-on');
            const offBtn = document.getElementById('dew-heater-off');

            if (enabled) {
                onBtn?.classList.add('active');
                offBtn?.classList.remove('active');
            } else {
                onBtn?.classList.remove('active');
                offBtn?.classList.add('active');
            }
        } catch (error) {
            console.error('Failed to set dew heater:', error);
            alert('Failed to control dew heater: ' + error.message);
        }
    },

    showDitheringControls() {
        // Already in imaging panel, just ensure it's visible
        const ditheringCheckbox = document.getElementById('enable-dithering');
        if (ditheringCheckbox) {
            ditheringCheckbox.parentElement.style.display = 'block';
        }
    },

    showManualExposureControls() {
        // Already in imaging panel
        const exposureTime = document.getElementById('exposure-time');
        const gain = document.getElementById('gain');
        if (exposureTime) exposureTime.parentElement.style.display = 'block';
        if (gain) gain.parentElement.style.display = 'block';
    },

    createAdvancedDrawerTabs() {
        // This will be called to populate the drawer with advanced feature tabs
        const drawerTabs = document.getElementById('drawer-tabs');
        if (!drawerTabs) return;

        let tabs = '<div class="drawer-tab-list">';

        if (this.features.wifi) {
            tabs += '<button class="drawer-tab" data-tab="wifi">WiFi</button>';
        }

        if (this.features.alignment) {
            tabs += '<button class="drawer-tab" data-tab="alignment">Alignment</button>';
        }

        if (this.features.system) {
            tabs += '<button class="drawer-tab" data-tab="system">System</button>';
        }

        if (this.features.advanced) {
            tabs += '<button class="drawer-tab" data-tab="advanced">Advanced</button>';
        }

        tabs += '</div>';
        tabs += '<div class="drawer-tab-content" id="drawer-tab-content"></div>';

        drawerTabs.innerHTML = tabs;

        // Setup tab switching
        this.setupDrawerTabs();
    },

    setupDrawerTabs() {
        const tabButtons = document.querySelectorAll('.drawer-tab');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                this.switchDrawerTab(tab);

                // Update active state
                tabButtons.forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
            });
        });

        // Activate first tab
        if (tabButtons.length > 0) {
            tabButtons[0].click();
        }
    },

    switchDrawerTab(tab) {
        const contentEl = document.getElementById('drawer-tab-content');
        if (!contentEl) return;

        switch (tab) {
            case 'wifi':
                this.renderWiFiTab(contentEl);
                break;
            case 'alignment':
                this.renderAlignmentTab(contentEl);
                break;
            case 'system':
                this.renderSystemTab(contentEl);
                break;
            case 'advanced':
                this.renderAdvancedTab(contentEl);
                break;
        }
    },

    renderWiFiTab(container) {
        container.innerHTML = `
            <div class="wifi-controls">
                <h4>WiFi Networks</h4>
                <button class="btn btn-primary" id="scan-wifi-btn">Scan Networks</button>
                <div id="wifi-networks-list"></div>
            </div>
        `;

        document.getElementById('scan-wifi-btn')?.addEventListener('click', () => {
            this.scanWiFiNetworks();
        });
    },

    renderAlignmentTab(container) {
        container.innerHTML = `
            <div class="alignment-controls">
                <h4>Polar Alignment</h4>
                <button class="btn btn-primary" id="check-polar-btn">Check Polar Alignment</button>
                <button class="btn btn-secondary" id="clear-polar-btn">Clear Polar Alignment</button>

                <h4>Compass Calibration</h4>
                <button class="btn btn-primary" id="start-compass-btn">Start Calibration</button>
                <button class="btn btn-secondary" id="stop-compass-btn">Stop Calibration</button>
            </div>
        `;
    },

    renderSystemTab(container) {
        container.innerHTML = `
            <div class="system-controls">
                <h4>System Information</h4>
                <button class="btn btn-primary" id="get-system-info-btn">Get Info</button>
                <div id="system-info-display"></div>

                <h4>Power</h4>
                <button class="btn btn-secondary" id="shutdown-btn">Shutdown</button>
                <button class="btn btn-secondary" id="reboot-btn">Reboot</button>
            </div>
        `;

        // Wire up event listeners
        document.getElementById('get-system-info-btn')?.addEventListener('click', () => {
            this.getSystemInfo();
        });

        document.getElementById('shutdown-btn')?.addEventListener('click', () => {
            if (confirm('Shutdown telescope? This will power off the device.')) {
                this.shutdownTelescope();
            }
        });

        document.getElementById('reboot-btn')?.addEventListener('click', () => {
            if (confirm('Reboot telescope? This will restart the device.')) {
                this.rebootTelescope();
            }
        });
    },

    renderAdvancedTab(container) {
        container.innerHTML = `
            <div class="advanced-controls">
                <h4>Advanced Features</h4>
                <button class="btn btn-primary" id="demo-mode-btn">Toggle Demo Mode</button>
                <button class="btn btn-primary" id="planet-scan-btn">Planet Scan</button>
            </div>
        `;
    },

    async scanWiFiNetworks() {
        try {
            const response = await fetch('/api/telescope/features/wifi/scan');
            if (!response.ok) throw new Error('WiFi scan failed');

            const data = await response.json();
            const listEl = document.getElementById('wifi-networks-list');
            if (listEl && data.networks) {
                listEl.innerHTML = data.networks.map(network => `
                    <div class="wifi-network">
                        <span>${network.ssid}</span>
                        <span>${network.signal}</span>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('WiFi scan failed:', error);
            alert('WiFi scan failed: ' + error.message);
        }
    },

    async getSystemInfo() {
        const displayEl = document.getElementById('system-info-display');
        if (!displayEl) return;

        displayEl.textContent = 'Loading system information...';

        try {
            const response = await fetch('/api/telescope/features/system/info');
            if (!response.ok) throw new Error('Failed to get system info');

            const data = await response.json();

            // Format the system info nicely
            let html = '<div class="system-info-grid">';

            if (data.device_name) {
                html += `<div class="info-row"><label>Device:</label><span>${data.device_name}</span></div>`;
            }
            if (data.firmware_version) {
                html += `<div class="info-row"><label>Firmware:</label><span>${data.firmware_version}</span></div>`;
            }
            if (data.hardware_version) {
                html += `<div class="info-row"><label>Hardware:</label><span>${data.hardware_version}</span></div>`;
            }
            if (data.serial_number) {
                html += `<div class="info-row"><label>Serial:</label><span>${data.serial_number}</span></div>`;
            }
            if (data.uptime_seconds !== undefined) {
                const hours = Math.floor(data.uptime_seconds / 3600);
                const minutes = Math.floor((data.uptime_seconds % 3600) / 60);
                html += `<div class="info-row"><label>Uptime:</label><span>${hours}h ${minutes}m</span></div>`;
            }
            if (data.temperature_c !== undefined) {
                html += `<div class="info-row"><label>Temperature:</label><span>${data.temperature_c.toFixed(1)}°C</span></div>`;
            }
            if (data.storage_used_mb !== undefined && data.storage_total_mb !== undefined) {
                const usedGB = (data.storage_used_mb / 1024).toFixed(2);
                const totalGB = (data.storage_total_mb / 1024).toFixed(2);
                const percent = ((data.storage_used_mb / data.storage_total_mb) * 100).toFixed(1);
                html += `<div class="info-row"><label>Storage:</label><span>${usedGB}GB / ${totalGB}GB (${percent}%)</span></div>`;
            }

            html += '</div>';
            displayEl.innerHTML = html;
        } catch (error) {
            console.error('Failed to get system info:', error);
            displayEl.textContent = 'Failed to load system information: ' + error.message;
        }
    },

    async shutdownTelescope() {
        try {
            const response = await fetch('/api/telescope/features/system/shutdown', {
                method: 'POST'
            });
            if (!response.ok) throw new Error('Shutdown command failed');

            alert('Shutdown command sent successfully');
        } catch (error) {
            console.error('Failed to shutdown telescope:', error);
            alert('Failed to shutdown: ' + error.message);
        }
    },

    async rebootTelescope() {
        try {
            const response = await fetch('/api/telescope/features/system/reboot', {
                method: 'POST'
            });
            if (!response.ok) throw new Error('Reboot command failed');

            alert('Reboot command sent successfully');
        } catch (error) {
            console.error('Failed to reboot telescope:', error);
            alert('Failed to reboot: ' + error.message);
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    TelescopeCapabilities.init();
});
