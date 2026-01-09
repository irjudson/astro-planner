// ==========================================
// SIMPLIFIED TELESCOPE CONTROLS
// Clean, focused UX for Seestar telescope
// ==========================================

const TelescopeControls = {
    isConnected: false,
    currentTarget: null,
    telemetryInterval: null,

    init() {
        console.log('TelescopeControls: Initializing...');
        this.setupEventListeners();
        this.setupControlHandlers();
        this.disableAllControls();
        console.log('TelescopeControls: Initialized');
    },

    setupEventListeners() {
        // Connection events
        document.addEventListener('telescope-connected', () => this.onConnected());
        document.addEventListener('telescope-disconnected', () => this.onDisconnected());

        // Telemetry updates
        document.addEventListener('telescope-telemetry-update', (e) => {
            this.updateTelemetry(e.detail);
        });
    },

    setupControlHandlers() {
        // Connection
        this.on('telescope-panel-connect-btn', () => this.handleConnect());
        this.on('telescope-panel-disconnect-btn', () => this.handleDisconnect());

        // Telescope control
        this.on('slew-to-target-btn', () => this.handleSlewToTarget());
        this.on('stop-motion-btn', () => this.handleStopMotion());
        this.on('park-telescope-btn', () => this.handlePark());

        // Imaging
        this.on('start-imaging-btn', () => this.handleStartImaging());
        this.on('stop-imaging-btn', () => this.handleStopImaging());
        this.on('auto-focus-btn', () => this.handleAutoFocus());

        // Advanced controls (in bottom drawer)
        this.on('dew-heater-toggle', () => this.handleDewHeater());
        this.on('refresh-images-btn', () => this.handleRefreshImages());
    },

    // Helper to add event listener
    on(id, handler) {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('click', handler);
        }
    },

    // ==========================================
    // CONNECTION
    // ==========================================

    async handleConnect() {
        const hostInput = document.getElementById('telescope-host');
        const host = hostInput?.value || '192.168.2.47';

        try {
            const response = await fetch('/api/telescope/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ host, port: 4700 })
            });

            if (!response.ok) throw new Error('Connection failed');

            const data = await response.json();
            console.log('Connected:', data);
            this.showStatus('Connected to telescope', 'success');
        } catch (error) {
            console.error('Connection error:', error);
            this.showStatus(`Failed to connect: ${error.message}`, 'error');
        }
    },

    async handleDisconnect() {
        if (!confirm('Disconnect from telescope?')) return;

        try {
            await fetch('/api/telescope/disconnect', { method: 'POST' });
            this.showStatus('Disconnected', 'info');
        } catch (error) {
            console.error('Disconnect error:', error);
        }
    },

    onConnected() {
        this.isConnected = true;
        this.enableControls();
        this.startTelemetryPolling();
        this.showStatus('Telescope connected', 'success');

        // Update UI
        document.getElementById('connection-panel')?.classList.add('connected');
        document.getElementById('telescope-panel-connect-btn').disabled = true;
        document.getElementById('telescope-panel-disconnect-btn').disabled = false;
    },

    onDisconnected() {
        this.isConnected = false;
        this.disableAllControls();
        this.stopTelemetryPolling();

        // Update UI
        document.getElementById('connection-panel')?.classList.remove('connected');
        document.getElementById('telescope-panel-connect-btn').disabled = false;
        document.getElementById('telescope-panel-disconnect-btn').disabled = true;
    },

    // ==========================================
    // TELESCOPE CONTROL
    // ==========================================

    async handleSlewToTarget() {
        const raInput = document.getElementById('target-ra');
        const decInput = document.getElementById('target-dec');
        const nameInput = document.getElementById('target-name');

        const ra = raInput?.value;
        const dec = decInput?.value;
        const name = nameInput?.value || 'Target';

        if (!ra || !dec) {
            this.showStatus('Enter RA and Dec coordinates', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/telescope/goto', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ra, dec, target_name: name })
            });

            if (!response.ok) throw new Error('Slew command failed');

            this.showStatus(`Slewing to ${name}...`, 'info');
            this.currentTarget = name;
        } catch (error) {
            console.error('Slew error:', error);
            this.showStatus(`Slew failed: ${error.message}`, 'error');
        }
    },

    async handleStopMotion() {
        try {
            await fetch('/api/telescope/stop', { method: 'POST' });
            this.showStatus('Motion stopped', 'info');
        } catch (error) {
            console.error('Stop error:', error);
        }
    },

    async handlePark() {
        if (!confirm('Park telescope?')) return;

        try {
            await fetch('/api/telescope/park', { method: 'POST' });
            this.showStatus('Parking telescope...', 'info');
        } catch (error) {
            console.error('Park error:', error);
            this.showStatus(`Park failed: ${error.message}`, 'error');
        }
    },

    // ==========================================
    // IMAGING
    // ==========================================

    async handleStartImaging() {
        const exposure = document.getElementById('exposure-time')?.value || 10;
        const gain = document.getElementById('gain-value')?.value || 80;

        try {
            const response = await fetch('/api/telescope/imaging/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ exposure_ms: exposure * 1000, gain })
            });

            if (!response.ok) throw new Error('Failed to start imaging');

            this.showStatus('Imaging started', 'success');
            document.getElementById('start-imaging-btn').disabled = true;
            document.getElementById('stop-imaging-btn').disabled = false;
        } catch (error) {
            console.error('Imaging error:', error);
            this.showStatus(`Imaging failed: ${error.message}`, 'error');
        }
    },

    async handleStopImaging() {
        try {
            await fetch('/api/telescope/imaging/stop', { method: 'POST' });
            this.showStatus('Imaging stopped', 'info');
            document.getElementById('start-imaging-btn').disabled = false;
            document.getElementById('stop-imaging-btn').disabled = true;
        } catch (error) {
            console.error('Stop imaging error:', error);
        }
    },

    async handleAutoFocus() {
        try {
            await fetch('/api/telescope/focus/auto', { method: 'POST' });
            this.showStatus('Auto focus started...', 'info');
        } catch (error) {
            console.error('Auto focus error:', error);
            this.showStatus(`Auto focus failed: ${error.message}`, 'error');
        }
    },

    // ==========================================
    // ADVANCED CONTROLS
    // ==========================================

    async handleDewHeater() {
        const toggle = document.getElementById('dew-heater-toggle');
        const enabled = toggle?.checked || false;

        try {
            await fetch('/api/telescope/features/hardware/dew-heater', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled, power_level: 90 })
            });

            this.showStatus(`Dew heater ${enabled ? 'on' : 'off'}`, 'info');
        } catch (error) {
            console.error('Dew heater error:', error);
        }
    },

    async handleRefreshImages() {
        try {
            const response = await fetch('/api/telescope/images');
            const images = await response.json();

            this.updateImageList(images);
            this.showStatus(`Found ${images.length} images`, 'info');
        } catch (error) {
            console.error('Image list error:', error);
        }
    },

    // ==========================================
    // TELEMETRY & STATUS
    // ==========================================

    startTelemetryPolling() {
        this.stopTelemetryPolling();
        this.telemetryInterval = setInterval(() => this.fetchTelemetry(), 2000);
        this.fetchTelemetry(); // Initial fetch
    },

    stopTelemetryPolling() {
        if (this.telemetryInterval) {
            clearInterval(this.telemetryInterval);
            this.telemetryInterval = null;
        }
    },

    async fetchTelemetry() {
        try {
            const response = await fetch('/api/telescope/status');
            const status = await response.json();
            this.updateTelemetry(status);
        } catch (error) {
            console.error('Telemetry fetch error:', error);
        }
    },

    updateTelemetry(status) {
        // State and tracking
        this.setText('telescope-state', status.state || 'Unknown');
        this.setText('tracking-status', status.is_tracking ? 'Tracking' : 'Not tracking');

        // Coordinates
        if (status.current_ra_hours !== null) {
            this.setText('current-ra', this.formatRA(status.current_ra_hours));
            this.setText('current-dec', this.formatDec(status.current_dec_degrees));
        }

        // Target
        this.setText('current-target', status.current_target || 'None');
    },

    formatRA(hours) {
        const h = Math.floor(hours);
        const m = Math.floor((hours - h) * 60);
        const s = Math.floor(((hours - h) * 60 - m) * 60);
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    },

    formatDec(degrees) {
        const sign = degrees >= 0 ? '+' : '-';
        const absDeg = Math.abs(degrees);
        const d = Math.floor(absDeg);
        const m = Math.floor((absDeg - d) * 60);
        const s = Math.floor(((absDeg - d) * 60 - m) * 60);
        return `${sign}${d.toString().padStart(2, '0')}°${m.toString().padStart(2, '0')}'${s.toString().padStart(2, '0')}"`;
    },

    // ==========================================
    // UI HELPERS
    // ==========================================

    enableControls() {
        this.setDisabled('slew-to-target-btn', false);
        this.setDisabled('stop-motion-btn', false);
        this.setDisabled('park-telescope-btn', false);
        this.setDisabled('start-imaging-btn', false);
        this.setDisabled('auto-focus-btn', false);
    },

    disableAllControls() {
        this.setDisabled('slew-to-target-btn', true);
        this.setDisabled('stop-motion-btn', true);
        this.setDisabled('park-telescope-btn', true);
        this.setDisabled('start-imaging-btn', true);
        this.setDisabled('stop-imaging-btn', true);
        this.setDisabled('auto-focus-btn', true);
    },

    setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    },

    setDisabled(id, disabled) {
        const el = document.getElementById(id);
        if (el) el.disabled = disabled;
    },

    showStatus(message, type = 'info') {
        const statusEl = document.getElementById('control-status');
        if (!statusEl) return;

        statusEl.textContent = message;
        statusEl.className = `status-message status-${type}`;

        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = 'status-message';
        }, 5000);
    },

    updateImageList(images) {
        const listEl = document.getElementById('image-list');
        if (!listEl) return;

        if (images.length === 0) {
            listEl.innerHTML = '<p class="text-secondary">No images available</p>';
            return;
        }

        listEl.innerHTML = images.map(img => `
            <div class="image-item">
                <span>${img.filename}</span>
                <button class="btn btn-sm btn-secondary" onclick="TelescopeControls.downloadImage('${img.filename}')">Download</button>
            </div>
        `).join('');
    },

    async downloadImage(filename) {
        window.open(`/api/telescope/images/download?filename=${encodeURIComponent(filename)}`, '_blank');
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => TelescopeControls.init());
} else {
    TelescopeControls.init();
}
