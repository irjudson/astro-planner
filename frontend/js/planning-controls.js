/**
 * Planning Controls Module
 * Handles planning panel interactions
 */

const PlanningControls = {
    /**
     * Initialize planning controls
     */
    init() {
        this.attachEventListeners();
        this.loadDevicesForPlanning();
        this.setDefaultDateTime();
    },

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Mosaic checkbox toggle
        const mosaicCheckbox = document.getElementById('enable-mosaic');
        const mosaicConfig = document.getElementById('mosaic-config');

        if (mosaicCheckbox && mosaicConfig) {
            mosaicCheckbox.addEventListener('change', (e) => {
                mosaicConfig.style.display = e.target.checked ? 'block' : 'none';
            });
        }

        // Generate Plan button
        const generateBtn = document.getElementById('generate-plan-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.handleGeneratePlan());
        }

        // Export buttons (placeholders)
        const exportPdfBtn = document.getElementById('export-pdf-btn');
        const exportCsvBtn = document.getElementById('export-csv-btn');
        const exportIcalBtn = document.getElementById('export-ical-btn');

        if (exportPdfBtn) exportPdfBtn.addEventListener('click', () => this.handleExport('pdf'));
        if (exportCsvBtn) exportCsvBtn.addEventListener('click', () => this.handleExport('csv'));
        if (exportIcalBtn) exportIcalBtn.addEventListener('click', () => this.handleExport('ical'));

        // Start Execution button
        const startExecBtn = document.getElementById('start-execution-btn');
        if (startExecBtn) {
            startExecBtn.addEventListener('click', () => this.handleStartExecution());
        }

        // Create Custom Plan button
        const createCustomPlanBtn = document.getElementById('create-custom-plan-btn');
        if (createCustomPlanBtn) {
            createCustomPlanBtn.addEventListener('click', () => this.handleCreateCustomPlan());
        }
    },

    /**
     * Load devices for planning device dropdown
     */
    async loadDevicesForPlanning() {
        try {
            const response = await fetch('/api/settings/devices');
            if (!response.ok) return;

            const devices = await response.json();
            const deviceSelect = document.getElementById('plan-device');

            if (deviceSelect) {
                deviceSelect.innerHTML = '<option value="">Select device...</option>';
                devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.id;
                    option.textContent = device.name;
                    deviceSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading devices:', error);
        }
    },

    /**
     * Set default date/time to tonight and load location defaults
     */
    setDefaultDateTime() {
        const dateInput = document.getElementById('plan-date');
        const startTimeInput = document.getElementById('plan-start-time');
        const endTimeInput = document.getElementById('plan-end-time');

        if (dateInput) {
            const today = new Date();
            dateInput.value = today.toISOString().split('T')[0];
        }

        if (startTimeInput) {
            startTimeInput.value = '20:00';
        }

        if (endTimeInput) {
            endTimeInput.value = '04:00';
        }

        // Load location defaults from preferences
        this.updateLocationDefaults();
    },

    /**
     * Update location fields with defaults from preferences
     */
    async updateLocationDefaults() {
        console.log('updateLocationDefaults called');

        // First, try to load fresh preferences from database
        try {
            const response = await fetch('/api/user/preferences');
            if (response.ok) {
                const prefs = await response.json();
                console.log('Loaded preferences from API:', prefs);

                // Update AppState
                if (window.AppState) {
                    AppState.preferences.latitude = prefs.latitude;
                    AppState.preferences.longitude = prefs.longitude;
                    AppState.preferences.elevation = prefs.elevation;
                    AppState.preferences.defaultDeviceId = prefs.default_device_id;
                }

                // Update form fields
                const latInput = document.getElementById('plan-latitude');
                const lonInput = document.getElementById('plan-longitude');
                const elevInput = document.getElementById('plan-elevation');
                const deviceSelect = document.getElementById('plan-device');

                if (latInput && prefs.latitude !== null) {
                    latInput.value = prefs.latitude;
                    console.log('Set latitude:', prefs.latitude);
                }

                if (lonInput && prefs.longitude !== null) {
                    lonInput.value = prefs.longitude;
                    console.log('Set longitude:', prefs.longitude);
                }

                if (elevInput && prefs.elevation !== null) {
                    elevInput.value = prefs.elevation;
                    console.log('Set elevation:', prefs.elevation);
                }

                if (deviceSelect && prefs.default_device_id) {
                    deviceSelect.value = prefs.default_device_id;
                    console.log('Set device:', prefs.default_device_id);
                }

                return;
            }
        } catch (error) {
            console.warn('Failed to load preferences from API, using AppState:', error);
        }

        // Fallback to AppState if API fails
        const latInput = document.getElementById('plan-latitude');
        const lonInput = document.getElementById('plan-longitude');
        const elevInput = document.getElementById('plan-elevation');
        const deviceSelect = document.getElementById('plan-device');

        if (latInput && AppState.preferences.latitude !== null) {
            latInput.value = AppState.preferences.latitude;
        }

        if (lonInput && AppState.preferences.longitude !== null) {
            lonInput.value = AppState.preferences.longitude;
        }

        if (elevInput && AppState.preferences.elevation !== null) {
            elevInput.value = AppState.preferences.elevation;
        }

        if (deviceSelect && AppState.preferences.defaultDeviceId) {
            deviceSelect.value = AppState.preferences.defaultDeviceId;
        }
    },

    /**
     * Handle Create Custom Plan button click
     */
    async handleCreateCustomPlan() {
        console.log('handleCreateCustomPlan called');

        // Get selected targets from AppState
        const selectedTargets = window.AppState?.discovery?.selectedTargets || [];
        console.log('Selected targets:', selectedTargets);

        if (selectedTargets.length === 0) {
            alert('Please select at least one target from the catalog');
            return;
        }

        console.log('Creating custom plan with', selectedTargets.length, 'targets');

        // Switch to planning workflow
        if (window.AppContext) {
            console.log('Switching to planning context');
            AppContext.switchContext('planning');

            // Expand Planning workflow section
            const planningSection = document.getElementById('planning-section');
            if (planningSection && planningSection.classList.contains('collapsed')) {
                console.log('Expanding planning section');
                AppContext.toggleWorkflowSection('planning');
            }

            // Display custom plan targets
            this.displayCustomPlanTargets(selectedTargets);

            // Show notification
            const notification = document.createElement('div');
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 217, 255, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
            notification.textContent = `Custom plan created with ${selectedTargets.length} target${selectedTargets.length > 1 ? 's' : ''}`;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);
        } else {
            console.error('AppContext not found!');
        }
    },

    /**
     * Display custom plan targets in planning view
     */
    displayCustomPlanTargets(targets) {
        const customPlanSection = document.getElementById('custom-plan-targets');
        const emptyState = document.getElementById('plan-empty-state');
        const targetsList = document.getElementById('custom-targets-list');

        if (!customPlanSection || !targetsList) return;

        // Hide empty state, show custom plan
        if (emptyState) emptyState.style.display = 'none';
        customPlanSection.style.display = 'block';

        // Build targets list HTML
        targetsList.innerHTML = targets.map((target, index) => `
            <div class="custom-target-item">
                <div class="target-number">${index + 1}</div>
                <div class="target-info">
                    <div class="target-name">${this.escapeHtml(target.name)}</div>
                    <div class="target-details">
                        ${target.type ? `<span class="badge">${target.type}</span>` : ''}
                        ${target.constellation ? `<span class="detail">Const: ${target.constellation}</span>` : ''}
                        ${target.magnitude !== null ? `<span class="detail">Mag: ${target.magnitude.toFixed(1)}</span>` : ''}
                        ${target.size ? `<span class="detail">Size: ${target.size}</span>` : ''}
                    </div>
                </div>
                <button class="btn btn-sm btn-secondary remove-target-btn" data-index="${index}">Remove</button>
            </div>
        `).join('');

        // Attach remove button listeners
        targetsList.querySelectorAll('.remove-target-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.removeTargetFromCustomPlan(index);
            });
        });
    },

    /**
     * Remove target from custom plan
     */
    removeTargetFromCustomPlan(index) {
        if (!window.AppState) return;

        AppState.discovery.selectedTargets.splice(index, 1);
        AppState.save();

        if (AppState.discovery.selectedTargets.length === 0) {
            // Show empty state again
            const customPlanSection = document.getElementById('custom-plan-targets');
            const emptyState = document.getElementById('plan-empty-state');
            if (customPlanSection) customPlanSection.style.display = 'none';
            if (emptyState) emptyState.style.display = 'block';
        } else {
            // Refresh display
            this.displayCustomPlanTargets(AppState.discovery.selectedTargets);
        }

        // Update catalog search view too
        if (window.CatalogSearch && window.CatalogSearch.updateSelectedTargetsList) {
            CatalogSearch.updateSelectedTargetsList();
        }
    },

    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Handle Generate Plan button click
     */
    async handleGeneratePlan() {
        console.log('Generating plan...');

        try {
            // Gather plan parameters
            const latitude = parseFloat(document.getElementById('plan-latitude')?.value);
            const longitude = parseFloat(document.getElementById('plan-longitude')?.value);
            const elevation = parseFloat(document.getElementById('plan-elevation')?.value) || 0;
            const date = document.getElementById('plan-date')?.value;
            const startTime = document.getElementById('plan-start-time')?.value;
            const endTime = document.getElementById('plan-end-time')?.value;
            const minAltitude = parseInt(document.getElementById('min-altitude')?.value) || 30;
            const maxMoonPhase = parseInt(document.getElementById('max-moon-phase')?.value) || 50;
            const deviceId = parseInt(document.getElementById('plan-device')?.value);

            if (!latitude || !longitude) {
                alert('Please enter location coordinates');
                return;
            }

            if (!date || !startTime || !endTime) {
                alert('Please enter observation date and time range');
                return;
            }

            // Get selected targets
            const selectedTargets = AppState.discovery?.selectedTargets || [];
            const targetIds = selectedTargets.map(t => t.id).filter(id => id);

            if (targetIds.length === 0) {
                alert('Please select targets from the catalog first');
                return;
            }

            // Call planning API
            const response = await fetch('/api/plans/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    location: {
                        latitude,
                        longitude,
                        elevation
                    },
                    observation_date: date,
                    start_time: startTime,
                    end_time: endTime,
                    target_ids: targetIds,
                    constraints: {
                        min_altitude: minAltitude,
                        max_moon_illumination: maxMoonPhase / 100
                    },
                    device_id: deviceId || null
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Plan generation failed');
            }

            const planData = await response.json();
            console.log('Plan generated:', planData);

            // Store plan in AppState
            AppState.planning.generatedPlan = planData;
            AppState.save();

            // Show plan results
            this.showPlanResults(planData);

        } catch (error) {
            console.error('Error generating plan:', error);
            alert('Failed to generate plan: ' + error.message);
        }
    },

    /**
     * Show plan results
     */
    showPlanResults(planData) {
        // Hide empty state
        const emptyState = document.getElementById('plan-empty-state');
        if (emptyState) emptyState.style.display = 'none';

        // Show plan summary
        const planSummary = document.getElementById('plan-summary');
        const planDate = document.getElementById('plan-summary-date');
        const totalTargets = document.getElementById('plan-total-targets');
        const duration = document.getElementById('plan-duration');
        const startTime = document.getElementById('plan-start');
        const endTime = document.getElementById('plan-end');

        if (planDate) planDate.textContent = planData.observation_date || '--';
        if (totalTargets) totalTargets.textContent = planData.targets?.length || 0;
        if (duration) duration.textContent = this.calculateDuration(planData.start_time, planData.end_time);
        if (startTime) startTime.textContent = planData.start_time || '--';
        if (endTime) endTime.textContent = planData.end_time || '--';

        if (planSummary) {
            planSummary.style.display = 'block';
        }

        // Show planned targets table
        const plannedTargets = document.getElementById('planned-targets');
        const targetsBody = document.getElementById('planned-targets-body');

        if (targetsBody && planData.targets) {
            targetsBody.innerHTML = planData.targets.map(target => `
                <tr>
                    <td>${target.start_time || '--'}</td>
                    <td>${this.escapeHtml(target.name || '--')}</td>
                    <td>${this.escapeHtml(target.type || '--')}</td>
                    <td>${target.altitude ? target.altitude.toFixed(1) + '°' : '--'}</td>
                    <td>${target.duration || '--'}</td>
                    <td>${target.priority || '--'}</td>
                </tr>
            `).join('');

            if (plannedTargets) {
                plannedTargets.style.display = 'block';
            }
        }
    },

    /**
     * Calculate duration between two times
     */
    calculateDuration(startTime, endTime) {
        if (!startTime || !endTime) return '--';

        try {
            const [startHour, startMin] = startTime.split(':').map(Number);
            const [endHour, endMin] = endTime.split(':').map(Number);

            let durationMins = (endHour * 60 + endMin) - (startHour * 60 + startMin);

            // Handle crossing midnight
            if (durationMins < 0) {
                durationMins += 24 * 60;
            }

            const hours = Math.floor(durationMins / 60);
            const mins = durationMins % 60;

            return `${hours}h ${mins}m`;
        } catch (e) {
            return '--';
        }
    },

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Handle export button click
     */
    handleExport(format) {
        console.log(`Exporting plan as ${format}...`);
        // TODO: Implement export functionality
        alert(`Export as ${format.toUpperCase()} - Coming soon!`);
    },

    /**
     * Handle Start Execution button click
     */
    handleStartExecution() {
        console.log('Starting execution...');

        // Switch to execution context
        if (window.AppContext) {
            AppContext.switchContext('execution');

            // Expand Execution workflow section
            const executionSection = document.getElementById('execution-section');
            if (executionSection && executionSection.classList.contains('collapsed')) {
                AppContext.toggleWorkflowSection('execution');
            }
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    PlanningControls.init();
});

// Make PlanningControls globally accessible
window.PlanningControls = PlanningControls;
