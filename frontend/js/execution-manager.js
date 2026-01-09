// ==========================================
// EXECUTION MANAGER
// ==========================================

const ExecutionManager = {
    statusPollingInterval: null,
    statusPollingRate: 2000, // Poll every 2 seconds when executing

    init() {
        this.setupEventListeners();
        this.setupPanelCollapse();
    },

    setupEventListeners() {
        // Execution control buttons
        const startBtn = document.getElementById('start-execution-btn');
        const pauseBtn = document.getElementById('pause-execution-btn');
        const stopBtn = document.getElementById('stop-execution-btn');

        if (startBtn) {
            startBtn.addEventListener('click', () => this.startExecution());
        }

        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.pauseExecution());
        }

        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopExecution());
        }

        // Telescope control buttons
        const gotoBtn = document.getElementById('goto-target-btn');
        const parkBtn = document.getElementById('park-telescope-btn');

        if (gotoBtn) {
            gotoBtn.addEventListener('click', () => this.gotoTarget());
        }

        if (parkBtn) {
            parkBtn.addEventListener('click', () => this.parkTelescope());
        }

        // Imaging parameter changes
        const exposureTime = document.getElementById('exposure-time');
        const gain = document.getElementById('gain');
        const frameCount = document.getElementById('frame-count');
        const enableDithering = document.getElementById('enable-dithering');

        if (exposureTime) {
            exposureTime.addEventListener('change', (e) => {
                AppState.execution.exposureTime = parseFloat(e.target.value);
            });
        }

        if (gain) {
            gain.addEventListener('change', (e) => {
                AppState.execution.gain = parseInt(e.target.value);
            });
        }

        if (frameCount) {
            frameCount.addEventListener('change', (e) => {
                AppState.execution.frameCount = parseInt(e.target.value);
            });
        }

        if (enableDithering) {
            enableDithering.addEventListener('change', (e) => {
                AppState.execution.ditheringEnabled = e.target.checked;
            });
        }
    },

    setupPanelCollapse() {
        // Make execution panels collapsible
        const panels = document.querySelectorAll('#execution-section .panel-collapsible');
        panels.forEach(panel => {
            const header = panel.querySelector('.panel-header');
            if (header) {
                header.addEventListener('click', () => {
                    panel.classList.toggle('collapsed');
                });
            }
        });
    },

    async startExecution() {
        const targetSelect = document.getElementById('execution-target');
        const targetId = targetSelect?.value;

        if (!targetId) {
            this.showError('Please select a target');
            return;
        }

        if (!AppState.connection.isConnected) {
            this.showError('Please connect to telescope first');
            return;
        }

        try {
            // Start exposure on telescope
            const response = await fetch('/api/telescope/start-exposure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    target_id: parseInt(targetId),
                    exposure_time: AppState.execution.exposureTime || 10,
                    gain: AppState.execution.gain || 80,
                    count: AppState.execution.frameCount || 50
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to start exposure');
            }

            const data = await response.json();

            // Update UI
            this.updateExecutionButtons(true);
            this.showProgress(true);

            // Start polling telescope status
            this.startStatusPolling();

            console.log('Execution started:', data);
        } catch (error) {
            console.error('Failed to start execution:', error);
            this.showError(error.message || 'Failed to start execution');
        }
    },

    async pauseExecution() {
        try {
            const response = await fetch('/api/telescope/pause-exposure', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to pause execution');
            }

            console.log('Execution paused');
        } catch (error) {
            console.error('Failed to pause execution:', error);
            this.showError(error.message || 'Failed to pause execution');
        }
    },

    async stopExecution() {
        try {
            const response = await fetch('/api/telescope/stop-exposure', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to stop execution');
            }

            // Update UI
            this.updateExecutionButtons(false);
            this.showProgress(false);

            // Stop polling telescope status
            this.stopStatusPolling();

            console.log('Execution stopped');
        } catch (error) {
            console.error('Failed to stop execution:', error);
            this.showError(error.message || 'Failed to stop execution');
        }
    },

    async gotoTarget() {
        const targetSelect = document.getElementById('execution-target');
        const targetId = targetSelect?.value;

        if (!targetId) {
            this.showError('Please select a target');
            return;
        }

        if (!AppState.connection.isConnected) {
            this.showError('Please connect to telescope first');
            return;
        }

        try {
            const response = await fetch('/api/telescope/goto', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    target_id: parseInt(targetId)
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to goto target');
            }

            console.log('Slewing to target');
        } catch (error) {
            console.error('Failed to goto target:', error);
            this.showError(error.message || 'Failed to goto target');
        }
    },

    async parkTelescope() {
        if (!AppState.connection.isConnected) {
            this.showError('Please connect to telescope first');
            return;
        }

        try {
            const response = await fetch('/api/telescope/park', {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to park telescope');
            }

            console.log('Telescope parked');
        } catch (error) {
            console.error('Failed to park telescope:', error);
            this.showError(error.message || 'Failed to park telescope');
        }
    },

    updateExecutionButtons(executing) {
        const startBtn = document.getElementById('start-execution-btn');
        const pauseBtn = document.getElementById('pause-execution-btn');
        const stopBtn = document.getElementById('stop-execution-btn');

        if (startBtn) {
            startBtn.disabled = executing;
        }

        if (pauseBtn) {
            pauseBtn.disabled = !executing;
        }

        if (stopBtn) {
            stopBtn.disabled = !executing;
        }
    },

    showProgress(show) {
        const progressEl = document.getElementById('execution-progress');
        if (progressEl) {
            progressEl.style.display = show ? 'block' : 'none';
        }
    },

    updateProgress(current, total) {
        const progressFill = document.getElementById('execution-progress-fill');
        const progressText = document.getElementById('execution-progress-text');

        if (progressFill && total > 0) {
            const percentage = (current / total) * 100;
            progressFill.style.width = `${percentage}%`;
        }

        if (progressText) {
            progressText.textContent = `${current} / ${total} frames`;
        }
    },

    async updateTelescopeStatus() {
        if (!AppState.connection.isConnected) {
            return;
        }

        try {
            const response = await fetch('/api/telescope/status');

            if (!response.ok) {
                throw new Error('Failed to get telescope status');
            }

            const status = await response.json();

            // Update telescope coordinates in execution panel
            const raEl = document.getElementById('telescope-ra');
            const decEl = document.getElementById('telescope-dec');
            const altEl = document.getElementById('telescope-alt');
            const azEl = document.getElementById('telescope-az');
            const trackingEl = document.getElementById('tracking-status');

            // Also update telemetry tab elements
            const telemRaEl = document.getElementById('telem-ra');
            const telemDecEl = document.getElementById('telem-dec');
            const telemAltEl = document.getElementById('telem-alt');
            const telemAzEl = document.getElementById('telem-az');

            const raText = (status.ra !== null && status.ra !== undefined)
                ? this.formatRA(status.ra)
                : '--:--:--';

            const decText = (status.dec !== null && status.dec !== undefined)
                ? this.formatDec(status.dec)
                : '--°--\'--"';

            const altText = (status.alt !== null && status.alt !== undefined)
                ? `${status.alt.toFixed(1)}°`
                : '--°';

            const azText = (status.az !== null && status.az !== undefined)
                ? `${status.az.toFixed(1)}°`
                : '--°';

            // Update execution panel
            if (raEl) raEl.textContent = raText;
            if (decEl) decEl.textContent = decText;
            if (altEl) altEl.textContent = altText;
            if (azEl) azEl.textContent = azText;

            if (trackingEl) {
                trackingEl.textContent = status.is_tracking ? 'Active' : 'Inactive';
                trackingEl.className = `status-value ${status.is_tracking ? 'status-active' : 'status-inactive'}`;
            }

            // Update telemetry tab
            if (telemRaEl) telemRaEl.textContent = raText;
            if (telemDecEl) telemDecEl.textContent = decText;
            if (telemAltEl) telemAltEl.textContent = altText;
            if (telemAzEl) telemAzEl.textContent = azText;

            // Update exposure progress if exposing
            if (status.is_exposing && status.exposure_progress) {
                this.updateProgress(
                    status.exposure_progress.current || 0,
                    status.exposure_progress.total || 0
                );
            }
        } catch (error) {
            console.error('Failed to update telescope status:', error);
        }
    },

    formatRA(ra) {
        // Convert decimal hours to HH:MM:SS
        const hours = Math.floor(ra);
        const minutes = Math.floor((ra - hours) * 60);
        const seconds = Math.floor(((ra - hours) * 60 - minutes) * 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    },

    formatDec(dec) {
        // Convert decimal degrees to DD:MM:SS
        const sign = dec >= 0 ? '+' : '-';
        const absDec = Math.abs(dec);
        const degrees = Math.floor(absDec);
        const minutes = Math.floor((absDec - degrees) * 60);
        const seconds = Math.floor(((absDec - degrees) * 60 - minutes) * 60);
        return `${sign}${degrees.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    },

    startStatusPolling() {
        this.stopStatusPolling(); // Clear any existing interval
        this.statusPollingInterval = setInterval(() => {
            this.updateTelescopeStatus();
        }, this.statusPollingRate);

        // Update immediately
        this.updateTelescopeStatus();
    },

    stopStatusPolling() {
        if (this.statusPollingInterval) {
            clearInterval(this.statusPollingInterval);
            this.statusPollingInterval = null;
        }
    },

    showError(message) {
        alert(message);
    },

    /**
     * Update operator dashboard execution queue and current target
     * @param {object} executionData - Execution data with plan, targets, and progress
     */
    updateOperatorDashboardQueue(executionData) {
        if (!executionData) {
            console.warn('ExecutionManager: No execution data provided for dashboard update');
            return;
        }

        // Update current target display
        const currentTargetDisplay = document.getElementById('operator-current-target');
        const currentTargetName = document.getElementById('current-target-name');

        if (executionData.currentTarget && currentTargetDisplay) {
            currentTargetDisplay.style.display = 'block';

            if (currentTargetName) {
                const phase = executionData.currentPhase || 'idle';
                const phaseText = {
                    'slewing': 'Slewing',
                    'focusing': 'Focusing',
                    'stacking': `Stacking (${executionData.framesCurrent}/${executionData.framesTotal})`,
                    'complete': 'Complete',
                    'idle': 'Idle'
                };
                currentTargetName.textContent = `${executionData.currentTarget.name || 'Unknown'} - ${phaseText[phase]}`;
            }
        } else if (currentTargetDisplay) {
            currentTargetDisplay.style.display = 'none';
        }

        // Update progress bar
        const progressBarFill = document.getElementById('execution-progress');
        if (progressBarFill && executionData.progress !== undefined) {
            progressBarFill.style.width = `${executionData.progress}%`;
        }

        // Update execution queue
        const queueDisplay = document.getElementById('operator-execution-queue');
        if (!queueDisplay) {
            console.warn('ExecutionManager: Queue display element not found');
            return;
        }

        // Clear existing queue
        queueDisplay.innerHTML = '';

        // Check if we have targets
        if (!executionData.targets || executionData.targets.length === 0) {
            queueDisplay.innerHTML = '<div class="empty-state">No targets in queue</div>';
            return;
        }

        // Populate queue items
        executionData.targets.forEach((target, index) => {
            const queueItem = document.createElement('div');
            queueItem.className = 'queue-item';

            // Mark active target
            if (index === executionData.currentTargetIndex) {
                queueItem.classList.add('active');
            }

            // Create queue item content
            const itemName = document.createElement('span');
            itemName.className = 'queue-item-name';
            itemName.textContent = target.name || `Target ${index + 1}`;

            const itemTime = document.createElement('span');
            itemTime.className = 'queue-item-time';

            // Show estimated time or status
            if (index < executionData.currentTargetIndex) {
                itemTime.textContent = '✓ Complete';
            } else if (index === executionData.currentTargetIndex) {
                if (executionData.estimatedRemainingSeconds) {
                    const minutes = Math.floor(executionData.estimatedRemainingSeconds / 60);
                    itemTime.textContent = `~${minutes}m remaining`;
                } else {
                    itemTime.textContent = 'In progress';
                }
            } else {
                // Future targets - show estimated exposure time if available
                if (target.exposureTime && target.frameCount) {
                    const totalMinutes = Math.floor((target.exposureTime * target.frameCount) / 60);
                    itemTime.textContent = `~${totalMinutes}m`;
                } else {
                    itemTime.textContent = 'Queued';
                }
            }

            queueItem.appendChild(itemName);
            queueItem.appendChild(itemTime);
            queueDisplay.appendChild(queueItem);
        });

        console.log('ExecutionManager: Operator dashboard queue updated', executionData);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    ExecutionManager.init();
});

// Update telescope status when connected
window.addEventListener('telescope-connected', () => {
    ExecutionManager.updateTelescopeStatus();
    ExecutionManager.startStatusPolling();
});

window.addEventListener('telescope-disconnected', () => {
    ExecutionManager.stopStatusPolling();
});
