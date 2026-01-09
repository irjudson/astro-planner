// ==========================================
// PROCESSING CONTROLS
// Handles image processing workflow
// ==========================================

const ProcessingControls = {
    selectedFiles: [],
    availableFiles: [],
    jobs: [],

    init() {
        this.setupEventListeners();
        this.loadAvailableFiles();
    },

    setupEventListeners() {
        // Refresh files button
        const refreshBtn = document.getElementById('refresh-files-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadAvailableFiles();
            });
        }

        // Operation type selector
        const operationSelect = document.getElementById('operation-type');
        if (operationSelect) {
            operationSelect.addEventListener('change', () => {
                this.updateStartButtonState();
            });
        }

        // Start processing button
        const startBtn = document.getElementById('start-processing-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                this.startProcessing();
            });
        }
    },

    async loadAvailableFiles() {
        const fileList = document.getElementById('file-list');
        if (!fileList) return;

        fileList.innerHTML = '<p class="text-secondary">Loading...</p>';

        try {
            const response = await fetch('/api/processing/files');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const files = await response.json();
            this.availableFiles = files;
            this.renderFileList();
        } catch (error) {
            console.error('Failed to load files:', error);
            fileList.innerHTML = '<p class="text-secondary">Failed to load files</p>';
        }
    },

    renderFileList() {
        const fileList = document.getElementById('file-list');
        if (!fileList) return;

        if (this.availableFiles.length === 0) {
            fileList.innerHTML = '<p class="text-secondary">No files available</p>';
            return;
        }

        fileList.innerHTML = this.availableFiles.map(file => `
            <div class="file-item" data-filepath="${this.escapeHtml(file.path)}">
                <span class="file-name">${this.escapeHtml(file.name)}</span>
                <span class="file-size">${this.formatFileSize(file.size)}</span>
            </div>
        `).join('');

        // Add click handlers
        fileList.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', () => {
                this.toggleFileSelection(item.dataset.filepath);
            });
        });
    },

    toggleFileSelection(filepath) {
        const index = this.selectedFiles.indexOf(filepath);
        if (index > -1) {
            this.selectedFiles.splice(index, 1);
        } else {
            this.selectedFiles.push(filepath);
        }

        // Update UI
        const fileItems = document.querySelectorAll('.file-item');
        fileItems.forEach(item => {
            if (this.selectedFiles.includes(item.dataset.filepath)) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });

        this.renderSelectedFiles();
        this.updateStartButtonState();
    },

    renderSelectedFiles() {
        const selectedList = document.getElementById('selected-files-list');
        if (!selectedList) return;

        if (this.selectedFiles.length === 0) {
            selectedList.innerHTML = '<p class="text-secondary">No files selected</p>';
            return;
        }

        selectedList.innerHTML = this.selectedFiles.map(filepath => {
            const file = this.availableFiles.find(f => f.path === filepath);
            const filename = file ? file.name : filepath.split('/').pop();
            return `
                <div class="selected-file-item">
                    <span>${this.escapeHtml(filename)}</span>
                    <button class="remove-file-btn" data-filepath="${this.escapeHtml(filepath)}">×</button>
                </div>
            `;
        }).join('');

        // Add remove handlers
        selectedList.querySelectorAll('.remove-file-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.toggleFileSelection(btn.dataset.filepath);
            });
        });
    },

    updateStartButtonState() {
        const startBtn = document.getElementById('start-processing-btn');
        const operationSelect = document.getElementById('operation-type');

        if (startBtn && operationSelect) {
            const hasFiles = this.selectedFiles.length > 0;
            const hasOperation = operationSelect.value !== '';
            startBtn.disabled = !(hasFiles && hasOperation);
        }
    },

    async startProcessing() {
        const operationSelect = document.getElementById('operation-type');
        const outputFormat = document.getElementById('output-format');
        const outputFilename = document.getElementById('output-filename');

        if (!operationSelect || !outputFormat || !outputFilename) return;

        const job = {
            id: Date.now(),
            operation: operationSelect.value,
            files: [...this.selectedFiles],
            outputFormat: outputFormat.value,
            outputFilename: outputFilename.value || 'output',
            status: 'processing',
            progress: 0
        };

        this.jobs.push(job);
        AppState.processing.jobs = this.jobs;
        AppState.save();

        this.renderJobs();

        try {
            const response = await fetch('/api/processing/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    operation: job.operation,
                    files: job.files,
                    output_format: job.outputFormat,
                    output_filename: job.outputFilename
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            // Update job status
            const jobIndex = this.jobs.findIndex(j => j.id === job.id);
            if (jobIndex > -1) {
                this.jobs[jobIndex].status = 'completed';
                this.jobs[jobIndex].progress = 100;
                this.jobs[jobIndex].outputFile = result.output_file;
                this.renderJobs();
            }

            alert('Processing completed successfully!');

            // Clear selections
            this.selectedFiles = [];
            this.renderSelectedFiles();
            this.updateStartButtonState();

        } catch (error) {
            console.error('Processing failed:', error);

            // Update job status to failed
            const jobIndex = this.jobs.findIndex(j => j.id === job.id);
            if (jobIndex > -1) {
                this.jobs[jobIndex].status = 'failed';
                this.renderJobs();
            }

            alert('Processing failed: ' + error.message);
        }
    },

    renderJobs() {
        const jobsContainer = document.getElementById('processing-jobs');
        if (!jobsContainer) return;

        if (this.jobs.length === 0) {
            jobsContainer.innerHTML = '<p class="text-secondary">No active jobs</p>';
            return;
        }

        jobsContainer.innerHTML = this.jobs.map(job => `
            <div class="job-item">
                <div class="job-header">
                    <span class="job-name">${this.escapeHtml(job.outputFilename)}.${this.escapeHtml(job.outputFormat)}</span>
                    <span class="job-status ${job.status}">${this.formatStatus(job.status)}</span>
                </div>
                <div class="job-progress">
                    <div class="job-progress-fill" style="width: ${job.progress}%"></div>
                </div>
            </div>
        `).join('');
    },

    formatStatus(status) {
        switch (status) {
            case 'processing':
                return 'Processing...';
            case 'completed':
                return 'Completed';
            case 'failed':
                return 'Failed';
            default:
                return status;
        }
    },

    formatFileSize(bytes) {
        if (!bytes) return '--';

        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return `${size.toFixed(1)} ${units[unitIndex]}`;
    },

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    ProcessingControls.init();
});
