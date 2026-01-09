// ==========================================
// OPERATOR DASHBOARD CONTROLLER
// Main controller for Seestar S50 operator interface
// ==========================================

const OperatorDashboard = {
    // State
    telemetryInterval: null,
    isConnected: false,
    currentCapabilities: null,
    currentTelemetry: null,

    // Initialize dashboard
    init() {
        console.log('OperatorDashboard: Initializing...');

        // Set up event listeners
        this.setupEventListeners();

        // Initialize UI state
        this.disableAllControls();

        // Check if already connected
        if (window.ConnectionManager && window.ConnectionManager.isConnected) {
            this.onConnected();
        }

        console.log('OperatorDashboard: Initialized');
    },

    // Setup event listeners
    setupEventListeners() {
        // Connection events
        document.addEventListener('telescope-connected', () => {
            console.log('OperatorDashboard: Telescope connected event received');
            this.onConnected();
        });

        document.addEventListener('telescope-disconnected', () => {
            console.log('OperatorDashboard: Telescope disconnected event received');
            this.onDisconnected();
        });

        // Capability events
        document.addEventListener('telescope-capabilities-loaded', (event) => {
            console.log('OperatorDashboard: Capabilities loaded event received', event.detail);
            this.onCapabilitiesLoaded(event.detail);
        });

        // Telemetry update events
        document.addEventListener('telescope-telemetry-update', (event) => {
            console.log('OperatorDashboard: Telemetry update received', event.detail);
            this.currentTelemetry = event.detail;
            this.updateTelemetryDisplay(event.detail);
        });
    },

    // Handle connection
    onConnected() {
        console.log('OperatorDashboard: Handling connection');
        this.isConnected = true;

        // Populate device info
        this.updateDeviceInfo();

        // Enable controls
        this.enableControls();

        // Start telemetry polling
        this.startTelemetryPolling();

        // Fetch capabilities if available
        if (window.TelescopeCapabilities) {
            window.TelescopeCapabilities.fetchCapabilities();
        }
    },

    // Handle disconnection
    onDisconnected() {
        console.log('OperatorDashboard: Handling disconnection');
        this.isConnected = false;

        // Stop telemetry polling
        this.stopTelemetryPolling();

        // Disable controls
        this.disableAllControls();

        // Clear device info
        this.clearDeviceInfo();

        // Clear telemetry
        this.clearTelemetryDisplay();

        // Reset capabilities
        this.currentCapabilities = null;
    },

    // Handle capabilities loaded
    onCapabilitiesLoaded(capabilitiesData) {
        console.log('OperatorDashboard: Processing capabilities', capabilitiesData);
        this.currentCapabilities = capabilitiesData;

        // Extract the actual capabilities and features from the data structure
        // capabilitiesData has format: { type, capabilities: {...}, features: {...} }
        const capabilities = capabilitiesData.capabilities || capabilitiesData;

        // Update panel visibility based on capabilities
        this.updateCapabilityPanels(capabilities);

        // Update feature visibility (pass full data object so checkFeature can access .features)
        this.updateFeatureVisibility(capabilitiesData);
    },

    // Update capability-based panel visibility
    updateCapabilityPanels(capabilities) {
        // Get all panels with data-capability attribute
        const panels = document.querySelectorAll('.operator-panel[data-capability]');

        panels.forEach(panel => {
            const requiredCapability = panel.dataset.capability;
            const isSupported = this.checkCapability(capabilities, requiredCapability);

            // Set data-supported attribute
            panel.dataset.supported = isSupported ? 'true' : 'false';

            console.log(`OperatorDashboard: Panel ${requiredCapability} - supported: ${isSupported}`);
        });
    },

    // Update Seestar-specific feature visibility
    updateFeatureVisibility(capabilities) {
        // Get all Seestar features
        const features = document.querySelectorAll('.seestar-feature[data-feature]');

        features.forEach(feature => {
            const requiredFeature = feature.dataset.feature;
            const isSupported = this.checkFeature(capabilities, requiredFeature);

            // Set data-supported attribute
            feature.dataset.supported = isSupported ? 'true' : 'false';

            console.log(`OperatorDashboard: Feature ${requiredFeature} - supported: ${isSupported}`);
        });
    },

    // Check if capability is supported
    checkCapability(capabilities, capabilityName) {
        if (!capabilities) return false;

        // First, try direct lookup (API returns: goto, autofocus, exposure, park, etc.)
        if (capabilities[capabilityName] === true) {
            return true;
        }

        // Fallback: try mapped names for backwards compatibility
        const capabilityMap = {
            'slew': capabilities.slew || capabilities.goto,
            'park': capabilities.park,
            'focus': capabilities.focuser || capabilities.autofocus,
            'autofocus': capabilities.focuser || capabilities.autofocus,
            'imaging': capabilities.imaging || capabilities.exposure,
            'exposure': capabilities.imaging || capabilities.exposure,
            'hardware': capabilities.hardware || capabilities.dew_heater,
            'goto': capabilities.slew || capabilities.goto
        };

        return capabilityMap[capabilityName] === true;
    },

    // Check if Seestar-specific feature is supported
    checkFeature(capabilitiesData, featureName) {
        if (!capabilitiesData) return false;

        // Parse dotted notation (e.g., "hardware.dew_heater" or "focuser.factory_reset")
        const parts = featureName.split('.');
        if (parts.length === 2) {
            const [category, feature] = parts;

            // First check if features object exists (new API format)
            if (capabilitiesData.features && capabilitiesData.features[category]) {
                return capabilitiesData.features[category][feature] === true;
            }

            // Also check direct category access for features passed from updateFeatureVisibility
            if (capabilitiesData[category] && capabilitiesData[category][feature] === true) {
                return true;
            }

            // Fallback: check in seestar object (old format)
            const seestarFeatures = capabilitiesData.seestar || {};
            if (seestarFeatures[feature] === true) {
                return true;
            }
        }

        // Fallback for simple names (backwards compatibility)
        const seestarFeatures = capabilitiesData.seestar || {};
        const featureMap = {
            'dew-heater': seestarFeatures.dew_heater,
            'dc-output': seestarFeatures.dc_output,
            'manual-mode': seestarFeatures.manual_mode,
            'factory-reset': seestarFeatures.factory_reset
        };

        return featureMap[featureName] === true;
    },

    // Enable controls after connection
    enableControls() {
        // Enable all buttons in operator panels
        const buttons = document.querySelectorAll('.operator-panel .btn:not(.btn-danger)');
        buttons.forEach(btn => {
            btn.disabled = false;
        });

        // Enable all inputs
        const inputs = document.querySelectorAll('.operator-panel input, .operator-panel select');
        inputs.forEach(input => {
            input.disabled = false;
        });

        console.log('OperatorDashboard: Controls enabled');
    },

    // Disable all controls
    disableAllControls() {
        // Disable all buttons except disconnect
        const buttons = document.querySelectorAll('.operator-panel .btn:not(.btn-danger)');
        buttons.forEach(btn => {
            btn.disabled = true;
        });

        // Disable all inputs
        const inputs = document.querySelectorAll('.operator-panel input, .operator-panel select');
        inputs.forEach(input => {
            input.disabled = true;
        });

        console.log('OperatorDashboard: Controls disabled');
    },

    // Update device info panel
    updateDeviceInfo() {
        const deviceName = window.ConnectionManager?.currentDevice?.name ||
                          this.currentTelemetry?.device_name ||
                          'Seestar S50';
        const firmware = this.currentTelemetry?.firmware_version ||
                        window.ConnectionManager?.currentDevice?.firmware ||
                        'Unknown';
        const signal = this.currentTelemetry?.signal_strength || '--';

        const deviceNameEl = document.getElementById('device-name');
        const firmwareEl = document.getElementById('device-firmware');
        const signalEl = document.getElementById('device-signal');

        if (deviceNameEl) deviceNameEl.textContent = deviceName;
        if (firmwareEl) firmwareEl.textContent = firmware;
        if (signalEl) signalEl.textContent = signal;
    },

    // Clear device info
    clearDeviceInfo() {
        const deviceNameEl = document.getElementById('device-name');
        const firmwareEl = document.getElementById('device-firmware');

        if (deviceNameEl) deviceNameEl.textContent = 'Not Connected';
        if (firmwareEl) firmwareEl.textContent = '--';
    },

    // Start telemetry polling
    startTelemetryPolling() {
        // Clear any existing interval
        this.stopTelemetryPolling();

        // Poll every 2 seconds
        this.telemetryInterval = setInterval(() => {
            this.fetchTelemetry();
        }, 2000);

        // Fetch immediately
        this.fetchTelemetry();

        console.log('OperatorDashboard: Telemetry polling started');
    },

    // Stop telemetry polling
    stopTelemetryPolling() {
        if (this.telemetryInterval) {
            clearInterval(this.telemetryInterval);
            this.telemetryInterval = null;
            console.log('OperatorDashboard: Telemetry polling stopped');
        }
    },

    // Fetch telemetry from backend
    async fetchTelemetry() {
        if (!this.isConnected) return;

        try {
            const response = await fetch('/api/telescope/status');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const telemetry = await response.json();
            this.currentTelemetry = telemetry;
            this.updateTelemetryDisplay(telemetry);

            // Dispatch event for other components
            document.dispatchEvent(new CustomEvent('telescope-telemetry-update', {
                detail: telemetry
            }));
        } catch (error) {
            console.error('OperatorDashboard: Failed to fetch telemetry:', error);
        }
    },

    // Update telemetry display
    updateTelemetryDisplay(telemetry) {
        if (!telemetry) return;

        // Update device info (firmware comes from telemetry)
        this.updateDeviceInfo();

        // Update RA/Dec/Alt/Az (using correct IDs)
        const raEl = document.getElementById('operator-telem-ra');
        const decEl = document.getElementById('operator-telem-dec');
        const altEl = document.getElementById('operator-telem-alt');
        const azEl = document.getElementById('operator-telem-az');

        if (raEl) raEl.textContent = this.formatRA(telemetry.ra) || '--:--:--';
        if (decEl) decEl.textContent = this.formatDec(telemetry.dec) || '--°--\'--"';
        if (altEl) altEl.textContent = telemetry.alt !== null && telemetry.alt !== undefined ? `${telemetry.alt.toFixed(1)}°` : '--°';
        if (azEl) azEl.textContent = telemetry.az !== null && telemetry.az !== undefined ? `${telemetry.az.toFixed(1)}°` : '--°';

        // Update tracking status
        const trackingStatus = telemetry.is_tracking ? 'Tracking' : 'Inactive';
        const trackingElement = document.getElementById('operator-tracking-status');
        if (trackingElement) {
            trackingElement.textContent = trackingStatus;
            trackingElement.style.color = telemetry.is_tracking ? '#00ff88' : 'rgba(255, 255, 255, 0.4)';
        }
    },

    // Clear telemetry display
    clearTelemetryDisplay() {
        const raEl = document.getElementById('operator-telem-ra');
        const decEl = document.getElementById('operator-telem-dec');
        const altEl = document.getElementById('operator-telem-alt');
        const azEl = document.getElementById('operator-telem-az');

        if (raEl) raEl.textContent = '--:--:--';
        if (decEl) decEl.textContent = '--°--\'--"';
        if (altEl) altEl.textContent = '--°';
        if (azEl) azEl.textContent = '--°';

        const trackingElement = document.getElementById('operator-tracking-status');
        if (trackingElement) {
            trackingElement.textContent = 'Inactive';
            trackingElement.style.color = 'rgba(255, 255, 255, 0.4)';
        }
    },

    // Format RA in HH:MM:SS format
    formatRA(ra) {
        if (ra === null || ra === undefined) return null;

        // Convert decimal hours to HH:MM:SS
        const hours = Math.floor(ra);
        const minutes = Math.floor((ra - hours) * 60);
        const seconds = Math.floor(((ra - hours) * 60 - minutes) * 60);

        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    },

    // Format Dec in ±DD:MM:SS format
    formatDec(dec) {
        if (dec === null || dec === undefined) return null;

        // Convert decimal degrees to ±DD:MM:SS
        const sign = dec >= 0 ? '+' : '-';
        const absDec = Math.abs(dec);
        const degrees = Math.floor(absDec);
        const minutes = Math.floor((absDec - degrees) * 60);
        const seconds = Math.floor(((absDec - degrees) * 60 - minutes) * 60);

        return `${sign}${String(degrees).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    },

    // Parse HMS format to decimal hours (for RA input)
    parseRA(raString) {
        if (!raString) return null;

        // Try HMS format first (HH:MM:SS)
        const hmsMatch = raString.match(/^(\d{1,2}):(\d{1,2}):(\d{1,2}(?:\.\d+)?)$/);
        if (hmsMatch) {
            const hours = parseInt(hmsMatch[1]);
            const minutes = parseInt(hmsMatch[2]);
            const seconds = parseFloat(hmsMatch[3]);

            const ra = hours + (minutes / 60) + (seconds / 3600);

            // Validate range (0-24 hours)
            if (ra < 0 || ra >= 24) {
                throw new Error('RA must be between 0 and 24 hours');
            }

            return ra;
        }

        // Try decimal format
        const decimal = parseFloat(raString);
        if (!isNaN(decimal)) {
            if (decimal < 0 || decimal >= 24) {
                throw new Error('RA must be between 0 and 24 hours');
            }
            return decimal;
        }

        throw new Error('Invalid RA format. Use HH:MM:SS or decimal hours');
    },

    // Parse DMS format to decimal degrees (for Dec input)
    parseDec(decString) {
        if (!decString) return null;

        // Try DMS format first (±DD:MM:SS)
        const dmsMatch = decString.match(/^([+-]?)(\d{1,2}):(\d{1,2}):(\d{1,2}(?:\.\d+)?)$/);
        if (dmsMatch) {
            const sign = dmsMatch[1] === '-' ? -1 : 1;
            const degrees = parseInt(dmsMatch[2]);
            const minutes = parseInt(dmsMatch[3]);
            const seconds = parseFloat(dmsMatch[4]);

            const dec = sign * (degrees + (minutes / 60) + (seconds / 3600));

            // Validate range (±90 degrees)
            if (dec < -90 || dec > 90) {
                throw new Error('Dec must be between -90 and +90 degrees');
            }

            return dec;
        }

        // Try decimal format
        const decimal = parseFloat(decString);
        if (!isNaN(decimal)) {
            if (decimal < -90 || decimal > 90) {
                throw new Error('Dec must be between -90 and +90 degrees');
            }
            return decimal;
        }

        throw new Error('Invalid Dec format. Use ±DD:MM:SS or decimal degrees');
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    OperatorDashboard.init();
    console.log('OperatorDashboard initialized');
});

// Make globally accessible
window.OperatorDashboard = OperatorDashboard;
