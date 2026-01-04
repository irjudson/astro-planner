// ==========================================
// CONNECTION MANAGER
// ==========================================

const ConnectionManager = {
    init() {
        this.loadDevices();
        this.setupEventListeners();
        this.setupModalListeners();
    },

    setupModalListeners() {
        const statusCompact = document.getElementById('connection-status-compact');
        const modal = document.getElementById('connection-modal');
        const closeBtn = document.getElementById('connection-modal-close');
        const openSettingsBtn = document.getElementById('open-settings-btn');

        if (statusCompact) {
            statusCompact.addEventListener('click', () => {
                this.openModal();
            });
        }

        if (closeBtn && modal) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        }

        if (openSettingsBtn) {
            openSettingsBtn.addEventListener('click', () => {
                modal.style.display = 'none';
                const settingsBtn = document.getElementById('settings-btn');
                if (settingsBtn) {
                    settingsBtn.click();
                }
            });
        }
    },

    openModal() {
        const modal = document.getElementById('connection-modal');
        if (modal) {
            this.updateModalDisplay();
            modal.style.display = 'flex';
        }
    },

    updateModalDisplay() {
        const deviceNameEl = document.getElementById('connection-device-name');
        const statusIndicatorEl = document.getElementById('connection-indicator-modal');
        const statusTextEl = document.getElementById('connection-status-text-modal');

        if (deviceNameEl) {
            deviceNameEl.textContent = AppState.connection.deviceId ?
                `Device ${AppState.connection.deviceId}` : 'None configured';
        }

        if (statusIndicatorEl) {
            statusIndicatorEl.className = AppState.connection.isConnected ?
                'status-indicator connected' : 'status-indicator disconnected';
        }

        if (statusTextEl) {
            statusTextEl.textContent = AppState.connection.isConnected ?
                'Connected' : 'Disconnected';
        }
    },

    setupEventListeners() {
        const deviceSelect = document.getElementById('device-select');
        const connectBtn = document.getElementById('connect-btn');
        const connectBtnCompact = document.getElementById('connect-btn-compact');

        if (deviceSelect) {
            deviceSelect.addEventListener('change', (e) => {
                const deviceId = e.target.value;
                if (connectBtn) connectBtn.disabled = !deviceId;
                if (connectBtnCompact) connectBtnCompact.disabled = !deviceId;
                AppState.connection.deviceId = deviceId;
            });
        }

        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                if (AppState.connection.isConnected) {
                    this.disconnect();
                } else {
                    this.connect();
                }
            });
        }

        if (connectBtnCompact) {
            connectBtnCompact.addEventListener('click', () => {
                if (AppState.connection.isConnected) {
                    this.disconnect();
                } else {
                    this.connect();
                }
            });
        }
    },

    async loadDevices() {
        try {
            const response = await fetch('/api/settings/devices');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const devices = await response.json();

            const select = document.getElementById('device-select');
            if (!select) return;

            select.innerHTML = '<option value="">Select device...</option>';

            let defaultDeviceId = null;
            devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.id;
                option.dataset.host = device.control_host;
                option.dataset.port = device.control_port || 4700;
                option.textContent = `${device.name} (${device.control_host})`;
                select.appendChild(option);

                if (device.is_default) {
                    defaultDeviceId = device.id;
                }
            });

            // Auto-select default device if no device is already selected
            if (!AppState.connection.deviceId && defaultDeviceId) {
                AppState.connection.deviceId = defaultDeviceId;
            }

            // Restore or select default device
            if (AppState.connection.deviceId) {
                select.value = AppState.connection.deviceId;
                const connectBtn = document.getElementById('connect-btn');
                const connectBtnCompact = document.getElementById('connect-btn-compact');
                if (connectBtn) connectBtn.disabled = false;
                if (connectBtnCompact) connectBtnCompact.disabled = false;
            }
        } catch (error) {
            console.error('Failed to load devices:', error);
            this.showError('Failed to load devices');
        }
    },

    async connect() {
        const deviceId = AppState.connection.deviceId;
        if (!deviceId) return;

        this.updateStatus('connecting', 'Connecting...');

        try {
            const response = await fetch('/api/telescope/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ device_id: parseInt(deviceId) })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Connection failed');
            }

            const data = await response.json();

            AppState.connection.isConnected = true;
            AppState.connection.status = 'connected';
            this.updateStatus('connected', 'Connected');

            const connectBtn = document.getElementById('connect-btn');
            const connectBtnCompact = document.getElementById('connect-btn-compact');

            if (connectBtn) {
                connectBtn.textContent = 'Disconnect';
                connectBtn.classList.remove('btn-primary');
                connectBtn.classList.add('btn-danger');
            }

            if (connectBtnCompact) {
                connectBtnCompact.title = 'Disconnect';
                connectBtnCompact.textContent = '⏏';
            }

            // Switch to execution context when device connects
            if (window.AppContext) {
                AppContext.switchContext('execution');
            }

            // Dispatch event for other components
            window.dispatchEvent(new Event('telescope-connected'));
        } catch (error) {
            console.error('Connection error:', error);
            this.updateStatus('error', 'Connection failed');
            this.showError(error.message || 'Failed to connect to device');
            AppState.connection.isConnected = false;
        }
    },

    async disconnect() {
        try {
            const response = await fetch('/api/telescope/disconnect', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Disconnect failed');
            }

            AppState.connection.isConnected = false;
            AppState.connection.status = 'disconnected';
            this.updateStatus('disconnected', 'Disconnected');

            const connectBtn = document.getElementById('connect-btn');
            const connectBtnCompact = document.getElementById('connect-btn-compact');

            if (connectBtn) {
                connectBtn.textContent = 'Connect';
                connectBtn.classList.remove('btn-danger');
                connectBtn.classList.add('btn-primary');
            }

            if (connectBtnCompact) {
                connectBtnCompact.title = 'Connect';
                connectBtnCompact.textContent = '⚡';
            }

            // Dispatch event for other components
            window.dispatchEvent(new Event('telescope-disconnected'));
        } catch (error) {
            console.error('Disconnect error:', error);
            this.showError(error.message || 'Failed to disconnect');
        }
    },

    updateStatus(state, text) {
        // Update compact status bar
        const compactIndicator = document.querySelector('#connection-status-compact .status-indicator');
        const compactLabel = document.querySelector('#connection-status-compact .status-label');

        if (compactIndicator) {
            compactIndicator.className = 'status-indicator ' + state;
        }

        if (compactLabel) {
            compactLabel.textContent = text;
        }

        // Update modal if open
        this.updateModalDisplay();
    },

    showError(message) {
        // Simple error display for now
        alert(message);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    ConnectionManager.init();
});
