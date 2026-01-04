// ==========================================
// APPLICATION STATE MANAGEMENT
// ==========================================

const AppState = {
    // Current active workflow context
    currentContext: 'discovery', // discovery | planning | execution | processing

    // Sidebar workflow section states
    workflowSections: {
        discovery: { expanded: true },
        planning: { expanded: false },
        execution: { expanded: false },
        processing: { expanded: false }
    },

    // Connection state
    connection: {
        deviceId: null,
        isConnected: false,
        status: 'disconnected'
    },

    // Weather state
    weather: {
        conditions: null,
        forecast: null,
        observability: 'unknown' // good | fair | poor | unknown
    },

    // Discovery state
    discovery: {
        searchQuery: '',
        filters: {},
        sortBy: 'name',
        currentPage: 1,
        catalogData: [],
        selectedTargets: []
    },

    // Planning state
    planning: {
        location: null,
        device: null,
        preferences: {},
        mosaicConfig: null,
        generatedPlan: null
    },

    // Execution state
    execution: {
        activeTab: 'execution', // execution | library | telemetry | liveview
        currentTarget: null,
        exposureTime: 10,
        gain: 80,
        frameCount: 50,
        ditheringEnabled: false,
        queue: [],
        sessionData: {},
        library: []
    },

    // Processing state
    processing: {
        selectedFile: null,
        jobs: [],
        outputFiles: []
    },

    // Drawer state
    drawer: {
        isOpen: false,
        activeTab: null
    },

    // Mobile state
    mobile: {
        sidebarOpen: false
    },

    // User preferences
    preferences: {
        units: 'metric', // 'metric' (SI) or 'imperial' (US)
        latitude: null,
        longitude: null,
        elevation: null,
        defaultDeviceId: null
    },

    // Persist state to localStorage
    save() {
        try {
            const stateToPersist = {
                workflowSections: this.workflowSections,
                currentContext: this.currentContext,
                drawer: this.drawer,
                preferences: this.preferences
            };
            localStorage.setItem('astro-planner-state', JSON.stringify(stateToPersist));
        } catch (e) {
            console.warn('Failed to save state:', e);
        }
    },

    // Load state from localStorage
    load() {
        try {
            const saved = localStorage.getItem('astro-planner-state');
            if (saved) {
                const parsed = JSON.parse(saved);
                this.workflowSections = parsed.workflowSections || this.workflowSections;
                this.currentContext = parsed.currentContext || this.currentContext;
                this.drawer = { ...this.drawer, ...parsed.drawer };
                this.preferences = { ...this.preferences, ...parsed.preferences };
            }
        } catch (e) {
            console.warn('Failed to load state:', e);
        }
    }
};

// Load state on init
AppState.load();
