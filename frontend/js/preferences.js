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
        const saveLocationBtn = document.getElementById('save-location-btn');
        const deviceSelect = document.getElementById('device-select');

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

        // Save location button
        if (saveLocationBtn) {
            saveLocationBtn.addEventListener('click', () => {
                this.saveLocation();
            });
        }

        // Detect location button
        const detectLocationBtn = document.getElementById('detect-location-btn');
        if (detectLocationBtn) {
            detectLocationBtn.addEventListener('click', () => {
                this.detectLocation();
            });
        }

        // Device select
        if (deviceSelect) {
            deviceSelect.addEventListener('change', (e) => {
                this.updateDefaultDevice(e.target.value);
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

    async loadCurrentPreferences() {
        // Load preferences from database
        try {
            const response = await fetch('/api/user/preferences');
            if (response.ok) {
                const prefs = await response.json();

                // Update AppState
                AppState.preferences.latitude = prefs.latitude;
                AppState.preferences.longitude = prefs.longitude;
                AppState.preferences.elevation = prefs.elevation;
                AppState.preferences.units = prefs.units || 'metric';
                AppState.preferences.defaultDeviceId = prefs.default_device_id;

                // Update form fields
                const unitsToggle = document.getElementById('units-toggle');
                if (unitsToggle) {
                    unitsToggle.value = prefs.units || 'metric';
                }

                const latInput = document.getElementById('settings-latitude');
                const lonInput = document.getElementById('settings-longitude');
                const elevInput = document.getElementById('settings-elevation');

                if (latInput && prefs.latitude !== null) {
                    latInput.value = prefs.latitude;
                }
                if (lonInput && prefs.longitude !== null) {
                    lonInput.value = prefs.longitude;
                }
                if (elevInput && prefs.elevation !== null) {
                    elevInput.value = prefs.elevation;
                }
            }
        } catch (error) {
            console.error('Failed to load preferences:', error);
        }

        // Load devices into dropdown
        await this.loadDevices();
    },

    async loadDevices() {
        try {
            const response = await fetch('/api/settings/devices');
            if (!response.ok) return;

            const devices = await response.json();
            const deviceSelect = document.getElementById('device-select');

            if (deviceSelect) {
                deviceSelect.innerHTML = '<option value="">None</option>';
                devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.id;
                    option.textContent = device.name;
                    deviceSelect.appendChild(option);
                });

                // Auto-select if only one device
                if (devices.length === 1 && !AppState.preferences.defaultDeviceId) {
                    AppState.preferences.defaultDeviceId = devices[0].id;
                    AppState.save();
                    deviceSelect.value = devices[0].id;
                    console.log('Auto-selected single device:', devices[0].name);
                }
                // Set current default if exists
                else if (AppState.preferences.defaultDeviceId) {
                    deviceSelect.value = AppState.preferences.defaultDeviceId;
                }
            }
        } catch (error) {
            console.error('Error loading devices:', error);
        }
    },

    async detectLocation() {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser');
            return;
        }

        const detectBtn = document.getElementById('detect-location-btn');
        const originalText = detectBtn ? detectBtn.textContent : '';
        if (detectBtn) detectBtn.textContent = 'Detecting...';

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const alt = position.coords.altitude || null;

                // Set values in form
                const latInput = document.getElementById('settings-latitude');
                const lonInput = document.getElementById('settings-longitude');
                const elevInput = document.getElementById('settings-elevation');

                if (latInput) latInput.value = lat.toFixed(4);
                if (lonInput) lonInput.value = lon.toFixed(4);

                // Try to get elevation from web service if not available
                if (!alt && lat && lon) {
                    try {
                        const elevResponse = await fetch(`https://api.open-elevation.com/api/v1/lookup?locations=${lat},${lon}`);
                        if (elevResponse.ok) {
                            const elevData = await elevResponse.json();
                            if (elevData.results && elevData.results.length > 0) {
                                const elevation = elevData.results[0].elevation;
                                if (elevInput) elevInput.value = Math.round(elevation);
                            }
                        }
                    } catch (error) {
                        console.warn('Could not fetch elevation:', error);
                    }
                }

                if (detectBtn) detectBtn.textContent = originalText;
                alert('Location detected! Click "Save Location" to save it.');
            },
            (error) => {
                console.error('Geolocation error:', error);
                if (detectBtn) detectBtn.textContent = originalText;
                let errorMsg = 'Failed to detect location';
                if (error.code === 1) {
                    errorMsg = 'Location permission denied. Please enable location access in your browser settings.';
                } else if (error.code === 2) {
                    errorMsg = 'Location unavailable. Please check your device settings.';
                } else if (error.code === 3) {
                    errorMsg = 'Location request timed out. Please try again or enter manually.';
                }
                alert(errorMsg);
            },
            {
                enableHighAccuracy: false, // Changed to false for better compatibility
                timeout: 30000, // Increased to 30 seconds
                maximumAge: 60000 // Allow cached position up to 1 minute old
            }
        );
    },

    async saveLocation() {
        const latInput = document.getElementById('settings-latitude');
        const lonInput = document.getElementById('settings-longitude');
        const elevInput = document.getElementById('settings-elevation');

        const latitude = latInput ? parseFloat(latInput.value) : null;
        const longitude = lonInput ? parseFloat(lonInput.value) : null;
        const elevation = elevInput ? parseFloat(elevInput.value) : null;

        // Validate
        if (latitude !== null && (latitude < -90 || latitude > 90)) {
            alert('Latitude must be between -90 and 90 degrees');
            return;
        }

        if (longitude !== null && (longitude < -180 || longitude > 180)) {
            alert('Longitude must be between -180 and 180 degrees');
            return;
        }

        try {
            // Save to database
            const response = await fetch('/api/user/preferences', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    latitude,
                    longitude,
                    elevation,
                    units: AppState.preferences.units,
                    default_device_id: AppState.preferences.defaultDeviceId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save preferences');
            }

            // Update local state
            AppState.preferences.latitude = latitude;
            AppState.preferences.longitude = longitude;
            AppState.preferences.elevation = elevation;

            alert('Location saved successfully');

            // Trigger update of planning controls if visible
            if (window.PlanningControls && window.PlanningControls.updateLocationDefaults) {
                PlanningControls.updateLocationDefaults();
            }
        } catch (error) {
            console.error('Failed to save location:', error);
            alert('Failed to save location: ' + error.message);
        }
    },

    async updateDefaultDevice(deviceId) {
        const deviceIdInt = deviceId ? parseInt(deviceId) : null;
        AppState.preferences.defaultDeviceId = deviceIdInt;

        try {
            // Save to database
            await fetch('/api/user/preferences', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    latitude: AppState.preferences.latitude,
                    longitude: AppState.preferences.longitude,
                    elevation: AppState.preferences.elevation,
                    units: AppState.preferences.units,
                    default_device_id: deviceIdInt
                })
            });
        } catch (error) {
            console.error('Failed to save default device:', error);
        }
    },

    async updateUnits(units) {
        AppState.preferences.units = units;

        try {
            // Save to database
            await fetch('/api/user/preferences', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    latitude: AppState.preferences.latitude,
                    longitude: AppState.preferences.longitude,
                    elevation: AppState.preferences.elevation,
                    units: units,
                    default_device_id: AppState.preferences.defaultDeviceId
                })
            });
        } catch (error) {
            console.error('Failed to save units preference:', error);
        }

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
