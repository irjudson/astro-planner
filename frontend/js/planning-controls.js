/**
 * Planning Controls Module
 * Handles planning panel interactions
 */

const PlanningControls = {
    currentLoadedPlan: null, // Store currently loaded plan for editing

    /**
     * Initialize planning controls
     */
    init() {
        this.attachEventListeners();
        this.loadDevicesForPlanning();
        this.setDefaultDateTime();
        this.loadSavedPlans();
        this.loadObservingPreferences();
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

        // Edit Plan button
        const editPlanBtn = document.getElementById('edit-plan-btn');
        if (editPlanBtn) {
            editPlanBtn.addEventListener('click', () => this.handleEditPlan());
        }

        // Save Custom Plan button
        const saveCustomPlanBtn = document.getElementById('save-custom-plan-btn');
        if (saveCustomPlanBtn) {
            saveCustomPlanBtn.addEventListener('click', () => this.handleSaveCustomPlan());
        }

        // Schedule & Optimize button
        const schedulePlanBtn = document.getElementById('schedule-plan-btn');
        if (schedulePlanBtn) {
            schedulePlanBtn.addEventListener('click', () => this.handleSchedulePlan());
        }

        // Observing preference fields - save on change
        const minAltInput = document.getElementById('min-altitude');
        const maxMoonInput = document.getElementById('max-moon-phase');
        const avoidMoonCheckbox = document.getElementById('avoid-moon');
        const prioritizeTransitsCheckbox = document.getElementById('prioritize-transits');

        if (minAltInput) {
            minAltInput.addEventListener('change', () => this.saveObservingPreferences());
        }
        if (maxMoonInput) {
            maxMoonInput.addEventListener('change', () => this.saveObservingPreferences());
        }
        if (avoidMoonCheckbox) {
            avoidMoonCheckbox.addEventListener('change', () => this.saveObservingPreferences());
        }
        if (prioritizeTransitsCheckbox) {
            prioritizeTransitsCheckbox.addEventListener('change', () => this.saveObservingPreferences());
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
     * Save observing preferences to database
     */
    async saveObservingPreferences() {
        const minAltInput = document.getElementById('min-altitude');
        const maxMoonInput = document.getElementById('max-moon-phase');
        const avoidMoonCheckbox = document.getElementById('avoid-moon');
        const prioritizeTransitsCheckbox = document.getElementById('prioritize-transits');

        if (!minAltInput || !maxMoonInput || !avoidMoonCheckbox || !prioritizeTransitsCheckbox) {
            return;
        }

        const prefs = {
            min_altitude: parseFloat(minAltInput.value) || 30,
            max_moon_phase: parseInt(maxMoonInput.value) || 50,
            avoid_moon: avoidMoonCheckbox.checked,
            prioritize_transits: prioritizeTransitsCheckbox.checked
        };

        try {
            // Get current preferences first
            const getResponse = await fetch('/api/user/preferences');
            if (getResponse.ok) {
                const currentPrefs = await getResponse.json();

                // Merge with observing preferences
                const updatedPrefs = {
                    ...currentPrefs,
                    ...prefs
                };

                const response = await fetch('/api/user/preferences', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updatedPrefs)
                });

                if (response.ok) {
                    console.log('Observing preferences saved');
                }
            }
        } catch (error) {
            console.error('Error saving observing preferences:', error);
        }
    },

    /**
     * Load observing preferences from database
     */
    async loadObservingPreferences() {
        try {
            const response = await fetch('/api/user/preferences');
            if (!response.ok) return;

            const prefs = await response.json();

            const minAltInput = document.getElementById('min-altitude');
            const maxMoonInput = document.getElementById('max-moon-phase');
            const avoidMoonCheckbox = document.getElementById('avoid-moon');
            const prioritizeTransitsCheckbox = document.getElementById('prioritize-transits');

            if (minAltInput && prefs.min_altitude !== undefined) {
                minAltInput.value = prefs.min_altitude;
            }
            if (maxMoonInput && prefs.max_moon_phase !== undefined) {
                maxMoonInput.value = prefs.max_moon_phase;
            }
            if (avoidMoonCheckbox && prefs.avoid_moon !== undefined) {
                avoidMoonCheckbox.checked = prefs.avoid_moon;
            }
            if (prioritizeTransitsCheckbox && prefs.prioritize_transits !== undefined) {
                prioritizeTransitsCheckbox.checked = prefs.prioritize_transits;
            }

            console.log('Observing preferences loaded');
        } catch (error) {
            console.error('Error loading observing preferences:', error);
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
     * Format ISO time to HH:MM
     */
    formatTime(isoTime) {
        if (!isoTime) return '--';
        try {
            const date = new Date(isoTime);
            return date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        } catch (e) {
            return '--';
        }
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
     * Load saved plans from database
     */
    async loadSavedPlans() {
        console.log('Loading saved plans...');

        const savedPlansSection = document.getElementById('saved-plans-section');
        const savedPlansList = document.getElementById('saved-plans-list');
        const planEmptyState = document.getElementById('plan-empty-state');

        if (!savedPlansSection || !savedPlansList) {
            console.warn('Saved plans section not found');
            return;
        }

        try {
            const response = await fetch('/api/plans/');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const plans = await response.json();
            console.log(`Loaded ${plans.length} saved plans`);

            if (plans.length === 0) {
                savedPlansList.innerHTML = '<p class="empty-state">No saved plans</p>';
                savedPlansSection.style.display = 'block'; // Still show the section
                // Show empty state when no plans
                if (planEmptyState) planEmptyState.style.display = 'block';
                return;
            }

            // Hide empty state when we have plans
            if (planEmptyState) planEmptyState.style.display = 'none';

            // Build plans list HTML
            savedPlansList.innerHTML = plans.map(plan => `
                <div class="saved-plan-item" data-plan-id="${plan.id}">
                    <div class="saved-plan-info">
                        <div class="saved-plan-name">${this.escapeHtml(plan.name)}</div>
                        <div class="saved-plan-meta">
                            ${plan.observing_date} • ${plan.location_name} • ${plan.total_targets} targets
                            ${plan.description ? `<br><span style="color: rgba(255, 255, 255, 0.5);">${this.escapeHtml(plan.description)}</span>` : ''}
                        </div>
                    </div>
                    <div class="saved-plan-actions">
                        <button class="btn btn-sm btn-primary load-plan-btn" data-plan-id="${plan.id}">Load</button>
                        <button class="btn btn-sm btn-secondary delete-plan-btn" data-plan-id="${plan.id}">Delete</button>
                    </div>
                </div>
            `).join('');

            // Show the section
            savedPlansSection.style.display = 'block';

            // Attach click handlers
            savedPlansList.querySelectorAll('.load-plan-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const planId = parseInt(btn.dataset.planId);
                    this.loadPlan(planId);
                });
            });

            savedPlansList.querySelectorAll('.delete-plan-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const planId = parseInt(btn.dataset.planId);
                    this.deletePlan(planId);
                });
            });

            // Make plan items clickable to load
            savedPlansList.querySelectorAll('.saved-plan-item').forEach(item => {
                item.addEventListener('click', () => {
                    const planId = parseInt(item.dataset.planId);
                    this.loadPlan(planId);
                });
            });

        } catch (error) {
            console.error('Error loading saved plans:', error);
            savedPlansList.innerHTML = '<p class="empty-state" style="color: rgba(255, 100, 100, 0.8);">Error loading plans</p>';
            savedPlansSection.style.display = 'block';
        }
    },

    /**
     * Load a specific plan
     */
    async loadPlan(planId) {
        console.log('Loading plan:', planId);

        try {
            const response = await fetch(`/api/plans/${planId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const planData = await response.json();
            console.log('Loaded plan data:', planData);

            // Display the loaded plan
            this.displayLoadedPlan(planData);

            // Show notification
            const notification = document.createElement('div');
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 217, 255, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
            notification.textContent = `Loaded plan: ${planData.name}`;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);

        } catch (error) {
            console.error('Error loading plan:', error);
            alert('Error loading plan: ' + error.message);
        }
    },

    /**
     * Display a loaded plan
     */
    displayLoadedPlan(planData) {
        // Store plan data for editing
        this.currentLoadedPlan = planData;

        // Hide empty state
        const emptyState = document.getElementById('plan-empty-state');
        const customPlanSection = document.getElementById('custom-plan-targets');
        const loadedPlanSummary = document.getElementById('loaded-plan-summary');
        const plannedTargets = document.getElementById('planned-targets');

        if (emptyState) emptyState.style.display = 'none';
        if (customPlanSection) customPlanSection.style.display = 'none';

        // Show plan summary
        if (loadedPlanSummary) {
            loadedPlanSummary.style.display = 'block';
            document.getElementById('plan-summary-date').textContent = planData.observing_date;
            document.getElementById('plan-total-targets').textContent = planData.plan.total_targets || 0;

            // Calculate duration from total_imaging_minutes
            const durationMinutes = planData.plan.session?.total_imaging_minutes || 0;
            const hours = Math.floor(durationMinutes / 60);
            const minutes = durationMinutes % 60;
            document.getElementById('plan-duration').textContent = `${hours}h ${minutes}m`;

            // Use imaging_start and imaging_end from session
            document.getElementById('plan-start').textContent = this.formatTime(planData.plan.session?.imaging_start) || '--';
            document.getElementById('plan-end').textContent = this.formatTime(planData.plan.session?.imaging_end) || '--';
        }

        // Show scheduled targets
        if (plannedTargets && planData.plan.scheduled_targets) {
            plannedTargets.style.display = 'block';
            const tbody = document.getElementById('planned-targets-body');
            if (tbody) {
                tbody.innerHTML = planData.plan.scheduled_targets.map(schedTarget => `
                    <tr>
                        <td>${this.formatTime(schedTarget.start_time)}</td>
                        <td>${this.escapeHtml(schedTarget.target?.name || schedTarget.target_name || '--')}</td>
                        <td>${this.escapeHtml(schedTarget.target?.object_type || schedTarget.type || '--')}</td>
                        <td>${schedTarget.start_altitude ? schedTarget.start_altitude.toFixed(1) + '°' : (schedTarget.altitude_deg ? schedTarget.altitude_deg.toFixed(1) + '°' : '--')}</td>
                        <td>${schedTarget.duration_minutes ? schedTarget.duration_minutes + ' min' : '--'}</td>
                        <td>${schedTarget.score?.total_score ? schedTarget.score.total_score.toFixed(2) : '--'}</td>
                    </tr>
                `).join('');
            }
        }
    },

    /**
     * Handle Edit Plan button - load plan data into form for modification
     */
    handleEditPlan() {
        if (!this.currentLoadedPlan || !window.AppState) {
            console.error('No plan loaded or AppState not available');
            return;
        }

        const plan = this.currentLoadedPlan.plan;

        // Populate location fields
        if (plan.location) {
            const latInput = document.getElementById('plan-latitude');
            const lonInput = document.getElementById('plan-longitude');
            const elevInput = document.getElementById('plan-elevation');

            if (latInput) latInput.value = plan.location.latitude;
            if (lonInput) lonInput.value = plan.location.longitude;
            if (elevInput) elevInput.value = plan.location.elevation || '';
        }

        // Populate date/time fields
        const dateInput = document.getElementById('plan-date');
        const startTimeInput = document.getElementById('plan-start-time');
        const endTimeInput = document.getElementById('plan-end-time');

        if (dateInput && this.currentLoadedPlan.observing_date) {
            dateInput.value = this.currentLoadedPlan.observing_date;
        }

        if (startTimeInput && plan.session?.imaging_start) {
            const startTime = new Date(plan.session.imaging_start);
            startTimeInput.value = startTime.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        }

        if (endTimeInput && plan.session?.imaging_end) {
            const endTime = new Date(plan.session.imaging_end);
            endTimeInput.value = endTime.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        }

        // Extract targets from scheduled_targets and convert to catalog format
        if (plan.scheduled_targets && plan.scheduled_targets.length > 0) {
            AppState.discovery.selectedTargets = plan.scheduled_targets.map(schedTarget => ({
                catalog_id: schedTarget.target?.catalog_id || schedTarget.catalog_id || '',
                name: schedTarget.target?.name || schedTarget.name || 'Unknown',
                type: schedTarget.target?.object_type || schedTarget.type || 'unknown',
                constellation: schedTarget.target?.constellation || '',
                magnitude: schedTarget.target?.magnitude,
                size: schedTarget.target?.size_arcmin ? `${schedTarget.target.size_arcmin.toFixed(1)}'` : '',
                ra_hours: schedTarget.target?.ra_hours,
                dec_degrees: schedTarget.target?.dec_degrees
            }));
            AppState.save();
        }

        // Hide plan summary and scheduled targets
        const loadedPlanSummary = document.getElementById('loaded-plan-summary');
        const plannedTargets = document.getElementById('planned-targets');
        if (loadedPlanSummary) loadedPlanSummary.style.display = 'none';
        if (plannedTargets) plannedTargets.style.display = 'none';

        // Show custom plan targets
        if (AppState.discovery.selectedTargets.length > 0) {
            this.displayCustomPlanTargets(AppState.discovery.selectedTargets);
        }

        // Show notification
        const notification = document.createElement('div');
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 217, 255, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
        notification.textContent = `Plan loaded for editing - ${AppState.discovery.selectedTargets.length} targets`;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);

        // Update catalog search view if available
        if (window.CatalogSearch && window.CatalogSearch.updateSelectedTargetsList) {
            CatalogSearch.updateSelectedTargetsList();
        }
    },

    /**
     * Delete a plan
     */
    async deletePlan(planId) {
        if (!confirm('Are you sure you want to delete this plan?')) {
            return;
        }

        try {
            const response = await fetch(`/api/plans/${planId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                // Try to get error detail from response
                let errorMsg = `HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.detail) {
                        errorMsg = errorData.detail;
                    }
                } catch (e) {
                    // Failed to parse error, use status code
                }
                throw new Error(errorMsg);
            }

            // Reload the plans list
            this.loadSavedPlans();

            // Show notification
            const notification = document.createElement('div');
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 217, 255, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
            notification.textContent = 'Plan deleted';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);

        } catch (error) {
            console.error('Error deleting plan:', error);

            // Show error notification
            const notification = document.createElement('div');
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(255, 100, 100, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000; max-width: 400px;';
            notification.textContent = error.message;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 5000);
        }
    },

    /**
     * Handle Start Execution button click
     */
    handleStartExecution() {
        console.log('Starting execution...');

        // Store the plan ID if we have a loaded plan
        if (this.currentLoadedPlan && this.currentLoadedPlan.id) {
            // Store in AppState for execution view to use
            if (window.AppState) {
                AppState.execution.activePlanId = this.currentLoadedPlan.id;
                AppState.execution.activePlanName = this.currentLoadedPlan.name;
                AppState.save();
            }
        }

        // Switch to execution context
        if (window.AppContext) {
            AppContext.switchContext('execution');

            // Expand Execution workflow section
            const executionSection = document.getElementById('execution-section');
            if (executionSection && executionSection.classList.contains('collapsed')) {
                AppContext.toggleWorkflowSection('execution');
            }
        }
    },

    /**
     * Handle Save Custom Plan button click
     */
    async handleSaveCustomPlan() {
        console.log('Save custom plan clicked');

        // Get selected targets
        const selectedTargets = window.AppState?.discovery?.selectedTargets || [];
        if (selectedTargets.length === 0) {
            alert('Please select at least one target');
            return;
        }

        // Prompt for plan name and description
        const planName = prompt('Enter a name for this plan:');
        if (!planName || planName.trim() === '') {
            return; // User cancelled
        }

        const planDescription = prompt('Enter a description (optional):');

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

            if (!latitude || !longitude || !date || !startTime || !endTime) {
                alert('Please fill in all required location and time fields');
                return;
            }

            // Get target IDs (filter out any without id)
            const targetIds = selectedTargets.map(t => t.id).filter(id => id);
            if (targetIds.length === 0) {
                alert('Selected targets must have valid IDs. Try re-selecting from catalog.');
                return;
            }

            // Call generate API to create optimized plan
            const generateResponse = await fetch('/api/plans/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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

            if (!generateResponse.ok) {
                const error = await generateResponse.json();
                throw new Error(error.detail || 'Failed to generate plan');
            }

            const planData = await generateResponse.json();

            // Save the generated plan
            const saveResponse = await fetch('/api/plans/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: planName.trim(),
                    description: planDescription?.trim() || null,
                    plan: planData
                })
            });

            if (!saveResponse.ok) {
                const error = await saveResponse.json();
                throw new Error(error.detail || 'Failed to save plan');
            }

            const savedPlan = await saveResponse.json();
            console.log('Plan saved:', savedPlan);

            // Reload saved plans list
            await this.loadSavedPlans();

            // Show success notification
            const notification = document.createElement('div');
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 217, 255, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
            notification.textContent = `Plan "${planName}" saved successfully`;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);

        } catch (error) {
            console.error('Error saving plan:', error);
            alert('Error saving plan: ' + error.message);
        }
    },

    /**
     * Handle Schedule & Optimize button click
     */
    async handleSchedulePlan() {
        console.log('Schedule & optimize clicked');

        // Get selected targets
        const selectedTargets = window.AppState?.discovery?.selectedTargets || [];
        if (selectedTargets.length === 0) {
            alert('Please select at least one target');
            return;
        }

        try {
            // Gather plan parameters (same as generate)
            const latitude = parseFloat(document.getElementById('plan-latitude')?.value);
            const longitude = parseFloat(document.getElementById('plan-longitude')?.value);
            const elevation = parseFloat(document.getElementById('plan-elevation')?.value) || 0;
            const date = document.getElementById('plan-date')?.value;
            const startTime = document.getElementById('plan-start-time')?.value;
            const endTime = document.getElementById('plan-end-time')?.value;
            const minAltitude = parseInt(document.getElementById('min-altitude')?.value) || 30;
            const maxMoonPhase = parseInt(document.getElementById('max-moon-phase')?.value) || 50;
            const deviceId = parseInt(document.getElementById('plan-device')?.value);

            if (!latitude || !longitude || !date || !startTime || !endTime) {
                alert('Please fill in all required location and time fields');
                return;
            }

            // Get target IDs
            const targetIds = selectedTargets.map(t => t.id).filter(id => id);
            if (targetIds.length === 0) {
                alert('Selected targets must have valid IDs. Try re-selecting from catalog.');
                return;
            }

            // Show loading notification
            const loadingNotification = document.createElement('div');
            loadingNotification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 217, 255, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
            loadingNotification.textContent = 'Optimizing schedule...';
            document.body.appendChild(loadingNotification);

            // Call generate API
            const response = await fetch('/api/plans/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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

            loadingNotification.remove();

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to generate plan');
            }

            const planData = await response.json();
            console.log('Plan optimized:', planData);

            // Display the optimized plan
            this.displayGeneratedPlan(planData);

            // Show success notification
            const notification = document.createElement('div');
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 217, 255, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
            notification.textContent = `Schedule optimized - ${planData.scheduled_targets.length} targets`;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);

        } catch (error) {
            console.error('Error optimizing schedule:', error);
            alert('Error optimizing schedule: ' + error.message);
        }
    },

    /**
     * Display a generated/optimized plan
     */
    displayGeneratedPlan(planData) {
        // Store in state
        this.currentLoadedPlan = {
            name: 'Generated Plan',
            observing_date: planData.session.observing_date,
            plan: planData
        };

        // Hide custom plan targets
        const customPlanSection = document.getElementById('custom-plan-targets');
        if (customPlanSection) customPlanSection.style.display = 'none';

        // Show loaded plan summary
        const loadedPlanSummary = document.getElementById('loaded-plan-summary');
        const plannedTargets = document.getElementById('planned-targets');

        if (loadedPlanSummary) {
            loadedPlanSummary.style.display = 'block';
            document.getElementById('plan-summary-date').textContent = planData.session.observing_date;
            document.getElementById('plan-total-targets').textContent = planData.total_targets || 0;

            // Calculate duration
            const durationMinutes = planData.session.total_imaging_minutes || 0;
            const hours = Math.floor(durationMinutes / 60);
            const minutes = durationMinutes % 60;
            document.getElementById('plan-duration').textContent = `${hours}h ${minutes}m`;

            // Times
            document.getElementById('plan-start').textContent = this.formatTime(planData.session.imaging_start);
            document.getElementById('plan-end').textContent = this.formatTime(planData.session.imaging_end);
        }

        // Show scheduled targets
        if (plannedTargets && planData.scheduled_targets) {
            plannedTargets.style.display = 'block';
            const tbody = document.getElementById('planned-targets-body');
            if (tbody) {
                tbody.innerHTML = planData.scheduled_targets.map(schedTarget => `
                    <tr>
                        <td>${this.formatTime(schedTarget.start_time)}</td>
                        <td>${this.escapeHtml(schedTarget.target?.name || schedTarget.target_name || '--')}</td>
                        <td>${this.escapeHtml(schedTarget.target?.object_type || schedTarget.type || '--')}</td>
                        <td>${schedTarget.start_altitude ? schedTarget.start_altitude.toFixed(1) + '°' : '--'}</td>
                        <td>${schedTarget.duration_minutes ? schedTarget.duration_minutes + ' min' : '--'}</td>
                        <td>${schedTarget.score?.total_score ? schedTarget.score.total_score.toFixed(2) : '--'}</td>
                    </tr>
                `).join('');
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
