// ==========================================
// CONNECTION MANAGER
// ==========================================

const ConnectionManager = {
    init() {
        this.loadDevices();
        this.setupEventListeners();
    },

    setupEventListeners() {
        const deviceSelect = document.getElementById('device-select');
        const connectBtn = document.getElementById('connect-btn');

        if (deviceSelect) {
            deviceSelect.addEventListener('change', (e) => {
                const deviceId = e.target.value;
                connectBtn.disabled = !deviceId;
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

            devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.id;
                option.dataset.host = device.ip_address;
                option.dataset.port = device.port || 4700;
                option.textContent = `${device.name} (${device.ip_address})`;
                select.appendChild(option);
            });

            // Restore selected device if any
            if (AppState.connection.deviceId) {
                select.value = AppState.connection.deviceId;
                document.getElementById('connect-btn').disabled = false;
            }
        } catch (error) {
            console.error('Failed to load devices:', error);
            this.showError('Failed to load devices');
        }
    },

    async connect() {
        const deviceId = AppState.connection.deviceId;
        if (!deviceId) return;

        // Get device host and port from selected option
        const select = document.getElementById('device-select');
        const selectedOption = select?.options[select.selectedIndex];

        if (!selectedOption) return;

        const host = selectedOption.dataset.host;
        const port = parseInt(selectedOption.dataset.port || '4700');

        this.updateStatus('connecting', 'Connecting...');

        try {
            const response = await fetch('/api/telescope/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ host, port })
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
            if (connectBtn) {
                connectBtn.textContent = 'Disconnect';
                connectBtn.classList.remove('btn-primary');
                connectBtn.classList.add('btn-danger');
            }

            // Switch to execution context when device connects
            if (window.AppContext) {
                AppContext.switchContext('execution');
            }
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
            if (connectBtn) {
                connectBtn.textContent = 'Connect';
                connectBtn.classList.remove('btn-danger');
                connectBtn.classList.add('btn-primary');
            }
        } catch (error) {
            console.error('Disconnect error:', error);
            this.showError(error.message || 'Failed to disconnect');
        }
    },

    updateStatus(state, text) {
        const indicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');

        if (indicator) {
            indicator.className = 'status-indicator ' + state;
        }

        if (statusText) {
            statusText.textContent = text;
        }
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
