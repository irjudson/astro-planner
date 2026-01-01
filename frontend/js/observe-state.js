/**
 * Observe View State Management
 *
 * Global state object for the Observe tab.
 * All components read from and write to this state.
 */

const observeState = {
  connection: {
    status: 'disconnected',  // disconnected | connecting | connected | error
    host: '192.168.2.47',
    port: 4700,
    firmware: null,
    lastUpdate: null,
    signalStrength: null,
    error: null
  },

  execution: {
    isExecuting: false,
    currentPlan: null,
    currentTarget: null,
    currentTargetIndex: 0,
    totalTargets: 0,
    currentPhase: null,     // slewing | focusing | stacking | complete
    progress: 0,            // 0-100
    startTime: null,
    elapsedSeconds: 0,
    estimatedRemainingSeconds: 0,
    framesCurrent: 0,
    framesTotal: 0,
    errors: []
  },

  library: {
    targets: [],            // Array of capture history objects
    filteredTargets: [],    // After search/filter applied
    filters: {
      search: '',
      status: 'all',        // all | complete | needs_more | new
      sortBy: 'recent'      // recent | name | exposure | quality
    },
    loading: false,
    transferStatus: {
      inProgress: false,
      currentFile: null,
      filesCompleted: 0,
      filesTotal: 0,
      lastSyncTime: null
    }
  },

  telemetry: {
    position: {
      ra: 0,              // Hours
      dec: 0,             // Degrees
      alt: 0,             // Degrees
      az: 0               // Degrees
    },
    deviceState: {},      // Full device state object
    plateSolve: null,     // Plate solve result
    annotations: [],      // Field annotations
    lastUpdate: null
  },

  controls: {
    imaging: {
      stackExposure: 10,
      previewExposure: 0.5,
      gain: 100,
      gainAuto: true,
      filter: 'clear',    // clear | lp
      dither: {
        enabled: true,
        pixels: 50,
        interval: 10
      }
    },
    dewHeater: {
      enabled: false,
      power: 90
    },
    focus: {
      position: 0,
      max: 2600
    },
    advancedStacking: {
      dbe: false,
      dbeSmooth: 50,
      starCorrection: true,
      starAggressiveness: 75,
      airplaneRemoval: false,
      drizzle: false,
      denoise: false
    }
  },

  ui: {
    activeMainTab: 'execution',  // execution | library | telemetry | live
    drawerOpen: false,
    drawerActiveTab: 'stacking', // stacking | system | wifi | calibration | hardware
    sidebarCollapsed: false,
    activeSidebarSection: {
      connection: true,
      execution: true,
      imaging: false,
      telescope: false,
      hardware: false,
      info: false
    }
  }
};

/**
 * State change listeners
 */
const stateListeners = {
  connection: [],
  execution: [],
  library: [],
  telemetry: [],
  controls: [],
  ui: []
};

/**
 * Subscribe to state changes
 * @param {string} section - State section to listen to
 * @param {function} callback - Function to call on change
 * @returns {function} Unsubscribe function
 */
function onStateChange(section, callback) {
  if (!stateListeners[section]) {
    console.error(`Unknown state section: ${section}`);
    return () => {};
  }

  stateListeners[section].push(callback);

  // Return unsubscribe function
  return () => {
    const index = stateListeners[section].indexOf(callback);
    if (index > -1) {
      stateListeners[section].splice(index, 1);
    }
  };
}

/**
 * Notify listeners of state change
 * @param {string} section - State section that changed
 */
function notifyStateChange(section) {
  if (stateListeners[section]) {
    stateListeners[section].forEach(callback => callback(observeState[section]));
  }
}

/**
 * Update state and notify listeners
 * @param {string} section - State section to update
 * @param {object} updates - Object with updates to merge
 */
function updateState(section, updates) {
  if (!observeState[section]) {
    console.error(`Unknown state section: ${section}`);
    return;
  }

  // Deep merge updates
  Object.assign(observeState[section], updates);

  // Notify listeners
  notifyStateChange(section);
}
