// ==========================================
// OPERATOR PANELS CONTROLLER
// Panel-specific control handlers and API calls
// ==========================================

const OperatorPanels = {
    // Initialize panel controls
    init() {
        console.log('OperatorPanels: Initializing...');

        // Setup all control handlers
        this.setupDevicePanel();
        this.setupTelescopeControls();
        this.setupFocusControls();
        this.setupImagingControls();
        this.setupHardwareControls();
        this.setupExecutionControls();
        this.setupLivePreview();

        console.log('OperatorPanels: Initialized');
    },

    // ==========================================
    // DEVICE STATUS PANEL
    // ==========================================

    setupDevicePanel() {
        const disconnectBtn = document.getElementById('operator-disconnect-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => {
                this.handleDisconnect();
            });
        }
    },

    async handleDisconnect() {
        if (!confirm('Disconnect from telescope?')) return;

        try {
            if (window.ConnectionManager) {
                await window.ConnectionManager.disconnect();
                console.log('OperatorPanels: Disconnected');
            }
        } catch (error) {
            console.error('OperatorPanels: Disconnect failed:', error);
            alert(`Failed to disconnect: ${error.message}`);
        }
    },

    // ==========================================
    // TELESCOPE CONTROL PANEL
    // ==========================================

    setupTelescopeControls() {
        // Goto coordinates button
        const gotoBtn = document.getElementById('goto-btn');
        if (gotoBtn) {
            gotoBtn.addEventListener('click', () => {
                this.handleGotoCoordinates();
            });
        }

        // Stop slew button
        const stopSlewBtn = document.getElementById('stop-slew-btn');
        if (stopSlewBtn) {
            stopSlewBtn.addEventListener('click', () => {
                this.handleStopSlew();
            });
        }

        // Open/Unpark button
        const openBtn = document.getElementById('open-btn');
        if (openBtn) {
            openBtn.addEventListener('click', () => {
                this.handleOpen();
            });
        }

        // Park button
        const parkBtn = document.getElementById('park-btn');
        if (parkBtn) {
            parkBtn.addEventListener('click', () => {
                this.handlePark();
            });
        }
    },

    async handleGotoCoordinates() {
        const raInput = document.getElementById('goto-ra');
        const decInput = document.getElementById('goto-dec');

        if (!raInput || !decInput) {
            console.error('OperatorPanels: RA/Dec inputs not found');
            return;
        }

        const raString = raInput.value.trim();
        const decString = decInput.value.trim();

        if (!raString || !decString) {
            alert('Please enter both RA and Dec coordinates');
            return;
        }

        try {
            // Parse coordinates using OperatorDashboard methods
            const ra = window.OperatorDashboard.parseRA(raString);
            const dec = window.OperatorDashboard.parseDec(decString);

            console.log(`OperatorPanels: Goto RA=${ra}, Dec=${dec}`);

            // Send to backend
            const response = await fetch('/api/telescope/goto', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ra, dec })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('OperatorPanels: Goto command sent', result);

            // Show feedback
            this.showFeedback('Slewing to coordinates...', 'success');
        } catch (error) {
            console.error('OperatorPanels: Goto failed:', error);
            alert(`Failed to slew: ${error.message}`);
        }
    },

    async handleStopSlew() {
        try {
            const response = await fetch('/api/telescope/stop-slew', {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            console.log('OperatorPanels: Stop slew command sent');
            this.showFeedback('Slew stopped', 'success');
        } catch (error) {
            console.error('OperatorPanels: Stop slew failed:', error);
            alert(`Failed to stop slew: ${error.message}`);
        }
    },

    async handleOpen() {
        if (!confirm('Open and unpark the telescope? This will activate the scope.')) return;

        try {
            const response = await fetch('/api/telescope/unpark', {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            console.log('OperatorPanels: Open/unpark command sent');
            this.showFeedback('Telescope opening and activating...', 'success');
        } catch (error) {
            console.error('OperatorPanels: Open/unpark failed:', error);
            alert(`Failed to open/unpark: ${error.message}`);
        }
    },

    async handlePark() {
        if (!confirm('Park the telescope?')) return;

        try {
            const response = await fetch('/api/telescope/park', {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            console.log('OperatorPanels: Park command sent');
            this.showFeedback('Telescope parking...', 'success');
        } catch (error) {
            console.error('OperatorPanels: Park failed:', error);
            alert(`Failed to park: ${error.message}`);
        }
    },

    // ==========================================
    // FOCUS CONTROL PANEL
    // ==========================================

    setupFocusControls() {
        // Autofocus button
        const autofocusBtn = document.getElementById('autofocus-btn');
        if (autofocusBtn) {
            autofocusBtn.addEventListener('click', () => {
                this.handleAutofocus();
            });
        }

        // Manual focus buttons
        const focusPlus10 = document.getElementById('focus-plus-10');
        const focusMinus10 = document.getElementById('focus-minus-10');
        const focusPlus100 = document.getElementById('focus-plus-100');
        const focusMinus100 = document.getElementById('focus-minus-100');

        if (focusPlus10) {
            focusPlus10.addEventListener('click', () => this.handleFocusMove(10));
        }
        if (focusMinus10) {
            focusMinus10.addEventListener('click', () => this.handleFocusMove(-10));
        }
        if (focusPlus100) {
            focusPlus100.addEventListener('click', () => this.handleFocusMove(100));
        }
        if (focusMinus100) {
            focusMinus100.addEventListener('click', () => this.handleFocusMove(-100));
        }

        // Factory reset button (Seestar-specific)
        const resetFocusBtn = document.getElementById('focus-reset-btn');
        if (resetFocusBtn) {
            resetFocusBtn.addEventListener('click', () => {
                this.handleResetFocuser();
            });
        }
    },

    async handleAutofocus() {
        try {
            console.log('OperatorPanels: Starting autofocus...');

            const response = await fetch('/api/telescope/features/imaging/autofocus', {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('OperatorPanels: Autofocus started', result);
            this.showFeedback('Autofocus started...', 'success');
        } catch (error) {
            console.error('OperatorPanels: Autofocus failed:', error);
            alert(`Failed to start autofocus: ${error.message}`);
        }
    },

    async handleFocusMove(offset) {
        try {
            console.log(`OperatorPanels: Moving focus by ${offset} steps`);

            const response = await fetch('/api/telescope/features/focuser/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ offset })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('OperatorPanels: Focus move command sent', result);
            this.showFeedback(`Moving focus ${offset > 0 ? '+' : ''}${offset}`, 'success');
        } catch (error) {
            console.error('OperatorPanels: Focus move failed:', error);
            alert(`Failed to move focus: ${error.message}`);
        }
    },

    async handleResetFocuser() {
        if (!confirm('Reset focuser to factory position? This is a Seestar-specific operation.')) return;

        try {
            const response = await fetch('/api/telescope/features/focuser/factory-reset', {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            console.log('OperatorPanels: Focuser reset command sent');
            this.showFeedback('Resetting focuser to factory position...', 'success');
        } catch (error) {
            console.error('OperatorPanels: Focuser reset failed:', error);
            alert(`Failed to reset focuser: ${error.message}`);
        }
    },

    // ==========================================
    // IMAGING SETTINGS PANEL
    // ==========================================

    setupImagingControls() {
        // Apply imaging settings button
        const applyImagingBtn = document.getElementById('apply-imaging-btn');
        if (applyImagingBtn) {
            applyImagingBtn.addEventListener('click', () => {
                this.handleApplyImaging();
            });
        }

        // Dew heater power slider - update value display
        const dewHeaterPower = document.getElementById('dew-heater-power');
        const dewHeaterValue = document.getElementById('dew-heater-power-display');
        if (dewHeaterPower && dewHeaterValue) {
            dewHeaterPower.addEventListener('input', (e) => {
                dewHeaterValue.textContent = e.target.value;
            });
        }
    },

    async handleApplyImaging() {
        const exposureInput = document.getElementById('imaging-exposure');
        const gainInput = document.getElementById('imaging-gain');

        if (!exposureInput || !gainInput) {
            console.error('OperatorPanels: Imaging inputs not found');
            return;
        }

        const exposure = parseFloat(exposureInput.value);
        const gain = parseInt(gainInput.value);

        if (isNaN(exposure) || isNaN(gain)) {
            alert('Please enter valid exposure and gain values');
            return;
        }

        try {
            console.log(`OperatorPanels: Setting exposure=${exposure}s, gain=${gain}`);

            const response = await fetch('/api/telescope/features/imaging/exposure', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ exposure, gain })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('OperatorPanels: Imaging settings applied', result);
            this.showFeedback('Imaging settings updated', 'success');
        } catch (error) {
            console.error('OperatorPanels: Apply imaging failed:', error);
            alert(`Failed to apply imaging settings: ${error.message}`);
        }
    },

    // ==========================================
    // HARDWARE CONTROLS PANEL (Seestar-specific)
    // ==========================================

    setupHardwareControls() {
        // Dew heater on/off buttons
        const dewHeaterOn = document.getElementById('dew-heater-on-btn');
        const dewHeaterOff = document.getElementById('dew-heater-off-btn');

        if (dewHeaterOn) {
            dewHeaterOn.addEventListener('click', () => {
                this.handleDewHeater(true);
            });
        }
        if (dewHeaterOff) {
            dewHeaterOff.addEventListener('click', () => {
                this.handleDewHeater(false);
            });
        }

        // Dew heater power slider change
        const dewHeaterPower = document.getElementById('dew-heater-power');
        if (dewHeaterPower) {
            // Apply power level when slider is released
            dewHeaterPower.addEventListener('change', (e) => {
                const power = parseInt(e.target.value);
                this.handleDewHeaterPower(power);
            });
        }

        // DC output on/off buttons
        const dcOutputOn = document.getElementById('dc-output-on-btn');
        const dcOutputOff = document.getElementById('dc-output-off-btn');

        if (dcOutputOn) {
            dcOutputOn.addEventListener('click', () => {
                this.handleDCOutput(true);
            });
        }
        if (dcOutputOff) {
            dcOutputOff.addEventListener('click', () => {
                this.handleDCOutput(false);
            });
        }
    },

    async handleDewHeater(enabled) {
        try {
            console.log(`OperatorPanels: Setting dew heater ${enabled ? 'ON' : 'OFF'}`);

            const response = await fetch('/api/telescope/features/hardware/dew-heater', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('OperatorPanels: Dew heater command sent', result);
            this.showFeedback(`Dew heater ${enabled ? 'enabled' : 'disabled'}`, 'success');
        } catch (error) {
            console.error('OperatorPanels: Dew heater control failed:', error);
            alert(`Failed to control dew heater: ${error.message}`);
        }
    },

    async handleDewHeaterPower(power) {
        try {
            console.log(`OperatorPanels: Setting dew heater power to ${power}%`);

            const response = await fetch('/api/telescope/features/hardware/dew-heater', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: true, power })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('OperatorPanels: Dew heater power updated', result);
            this.showFeedback(`Dew heater power: ${power}%`, 'success');
        } catch (error) {
            console.error('OperatorPanels: Dew heater power failed:', error);
            alert(`Failed to set dew heater power: ${error.message}`);
        }
    },

    async handleDCOutput(enabled) {
        try {
            console.log(`OperatorPanels: Setting DC output ${enabled ? 'ON' : 'OFF'}`);

            const response = await fetch('/api/telescope/features/hardware/dc-output', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('OperatorPanels: DC output command sent', result);
            this.showFeedback(`DC output ${enabled ? 'enabled' : 'disabled'}`, 'success');
        } catch (error) {
            console.error('OperatorPanels: DC output control failed:', error);
            alert(`Failed to control DC output: ${error.message}`);
        }
    },

    // ==========================================
    // EXECUTION CONTROL PANEL
    // ==========================================

    setupExecutionControls() {
        // Start execution button
        const startBtn = document.getElementById('start-execution-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                this.handleStartExecution();
            });
        }

        // Pause execution button
        const pauseBtn = document.getElementById('pause-execution-btn');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => {
                this.handlePauseExecution();
            });
        }

        // Stop execution button
        const stopBtn = document.getElementById('stop-execution-btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => {
                this.handleStopExecution();
            });
        }
    },

    async handleStartExecution() {
        try {
            console.log('OperatorPanels: Starting execution...');

            // This will be integrated with ExecutionManager
            if (window.ExecutionManager && window.ExecutionManager.startExecution) {
                await window.ExecutionManager.startExecution();
                this.showFeedback('Execution started', 'success');
            } else {
                console.warn('OperatorPanels: ExecutionManager not available');
                alert('Execution manager not initialized');
            }
        } catch (error) {
            console.error('OperatorPanels: Start execution failed:', error);
            alert(`Failed to start execution: ${error.message}`);
        }
    },

    async handlePauseExecution() {
        try {
            console.log('OperatorPanels: Pausing execution...');

            if (window.ExecutionManager && window.ExecutionManager.pauseExecution) {
                await window.ExecutionManager.pauseExecution();
                this.showFeedback('Execution paused', 'warning');
            } else {
                console.warn('OperatorPanels: ExecutionManager not available');
                alert('Execution manager not initialized');
            }
        } catch (error) {
            console.error('OperatorPanels: Pause execution failed:', error);
            alert(`Failed to pause execution: ${error.message}`);
        }
    },

    async handleStopExecution() {
        if (!confirm('Stop execution? This will abort the current plan.')) return;

        try {
            console.log('OperatorPanels: Stopping execution...');

            if (window.ExecutionManager && window.ExecutionManager.stopExecution) {
                await window.ExecutionManager.stopExecution();
                this.showFeedback('Execution stopped', 'danger');
            } else {
                console.warn('OperatorPanels: ExecutionManager not available');
                alert('Execution manager not initialized');
            }
        } catch (error) {
            console.error('OperatorPanels: Stop execution failed:', error);
            alert(`Failed to stop execution: ${error.message}`);
        }
    },

    // ==========================================
    // LIVE PREVIEW PANEL
    // ==========================================

    setupLivePreview() {
        // Start preview button
        const startPreviewBtn = document.getElementById('operator-start-preview-btn');
        if (startPreviewBtn) {
            startPreviewBtn.addEventListener('click', () => {
                this.handleStartPreview();
            });
        }

        // Stop preview button
        const stopPreviewBtn = document.getElementById('operator-stop-preview-btn');
        if (stopPreviewBtn) {
            stopPreviewBtn.addEventListener('click', () => {
                this.handleStopPreview();
            });
        }

        // Snapshot button
        const snapshotBtn = document.getElementById('operator-snapshot-btn');
        if (snapshotBtn) {
            snapshotBtn.addEventListener('click', () => {
                this.handleSnapshot();
            });
        }

        // Fullscreen button
        const fullscreenBtn = document.getElementById('operator-fullscreen-btn');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                this.handleFullscreen();
            });
        }
    },

    async handleStartPreview() {
        try {
            console.log('OperatorPanels: Starting live preview...');

            const liveviewFrame = document.getElementById('operator-liveview-frame');
            if (!liveviewFrame) return;

            // First, tell the telescope to start imaging (this creates the JPEG files)
            const response = await fetch('/api/telescope/start-imaging', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ restart: false })  // Don't restart, just continue
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            console.log('OperatorPanels: Telescope imaging started');

            // Create or get image element
            let img = liveviewFrame.querySelector('img');
            if (!img) {
                img = document.createElement('img');
                img.style.width = '100%';
                img.style.height = 'auto';
                img.style.display = 'block';
                liveviewFrame.innerHTML = '';
                liveviewFrame.appendChild(img);
            }

            // Start polling for preview images
            this.previewActive = true;
            this.pollPreviewImage(img);

            this.showFeedback('Live preview started', 'success');
        } catch (error) {
            console.error('OperatorPanels: Start preview failed:', error);
            alert(`Failed to start preview: ${error.message}`);
        }
    },

    async handleStopPreview() {
        try {
            console.log('OperatorPanels: Stopping live preview...');

            // Stop polling first
            this.previewActive = false;

            // Tell the telescope to stop imaging
            const response = await fetch('/api/telescope/stop-imaging', {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || `HTTP ${response.status}`);
            }

            console.log('OperatorPanels: Telescope imaging stopped');
            this.showFeedback('Preview stopped', 'success');
        } catch (error) {
            console.error('OperatorPanels: Stop preview failed:', error);
            alert(`Failed to stop preview: ${error.message}`);
        }
    },

    async pollPreviewImage(img) {
        if (!this.previewActive) return;

        try {
            // Fetch latest preview image
            const response = await fetch('/api/telescope/preview/latest');
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);

                // Revoke old object URL to prevent memory leak
                if (img.src && img.src.startsWith('blob:')) {
                    URL.revokeObjectURL(img.src);
                }

                img.src = url;
            }
        } catch (error) {
            console.error('OperatorPanels: Preview poll failed:', error);
        }

        // Poll again in 1 second
        if (this.previewActive) {
            setTimeout(() => this.pollPreviewImage(img), 1000);
        }
    },

    async handleSnapshot() {
        try {
            console.log('OperatorPanels: Taking snapshot...');
            this.showFeedback('Snapshot captured', 'success');
        } catch (error) {
            console.error('OperatorPanels: Snapshot failed:', error);
            alert(`Failed to capture snapshot: ${error.message}`);
        }
    },

    handleFullscreen() {
        const previewFrame = document.querySelector('.live-preview-frame');
        if (!previewFrame) return;

        if (!document.fullscreenElement) {
            previewFrame.requestFullscreen().catch(err => {
                console.error('OperatorPanels: Fullscreen failed:', err);
                alert(`Fullscreen failed: ${err.message}`);
            });
        } else {
            document.exitFullscreen();
        }
    },

    // ==========================================
    // UTILITY METHODS
    // ==========================================

    showFeedback(message, type = 'success') {
        // Create a temporary toast notification
        const toast = document.createElement('div');
        toast.className = `operator-toast operator-toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'success' ? 'rgba(0, 255, 136, 0.2)' :
                         type === 'warning' ? 'rgba(255, 165, 0, 0.2)' :
                         'rgba(255, 68, 68, 0.2)'};
            border: 1px solid ${type === 'success' ? '#00ff88' :
                                type === 'warning' ? '#ffa500' :
                                '#ff4444'};
            border-radius: 6px;
            color: white;
            font-size: 13px;
            z-index: 10000;
            animation: slideIn 300ms ease-out;
        `;

        document.body.appendChild(toast);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 300ms ease-in';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
};

// Add toast animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    OperatorPanels.init();
    console.log('OperatorPanels initialized');
});

// Make globally accessible
window.OperatorPanels = OperatorPanels;
