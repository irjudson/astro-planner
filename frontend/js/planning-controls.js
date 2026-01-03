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
    },

    /**
     * Load devices for planning device dropdown
     */
    async loadDevicesForPlanning() {
        try {
            const response = await fetch('/api/devices');
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
     * Set default date/time to tonight
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
    },

    /**
     * Handle Generate Plan button click
     */
    async handleGeneratePlan() {
        console.log('Generating plan...');

        // TODO: Implement actual plan generation API call
        // For now, show mock plan summary
        this.showPlanSummary({
            total_targets: 5,
            duration: '6h 30m',
            start_time: '20:00',
            end_time: '02:30',
            date: document.getElementById('plan-date')?.value || new Date().toISOString().split('T')[0]
        });
    },

    /**
     * Show plan summary
     */
    showPlanSummary(planData) {
        const planSummary = document.getElementById('plan-summary');
        const planDate = document.getElementById('plan-summary-date');
        const totalTargets = document.getElementById('plan-total-targets');
        const duration = document.getElementById('plan-duration');
        const startTime = document.getElementById('plan-start');
        const endTime = document.getElementById('plan-end');

        if (planDate) planDate.textContent = planData.date;
        if (totalTargets) totalTargets.textContent = planData.total_targets;
        if (duration) duration.textContent = planData.duration;
        if (startTime) startTime.textContent = planData.start_time;
        if (endTime) endTime.textContent = planData.end_time;

        if (planSummary) {
            planSummary.style.display = 'block';
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
