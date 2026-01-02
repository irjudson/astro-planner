# Observe View Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the three-zone Observe view redesign with full telescope control integration, capture history, and live telemetry.

**Architecture:** Three-zone split-view layout (left sidebar for controls, right main area with tabs, bottom drawer for advanced features). Global state management with polling for real-time updates. Vanilla JavaScript with modular organization.

**Tech Stack:** Vanilla JavaScript, CSS with CSS variables, FastAPI backend (existing), HTTP polling for real-time updates

---

## Task 1: Create CSS Framework with Variables

**Files:**
- Create: `frontend/css/observe.css`
- Modify: `frontend/index.html` (add CSS link)

**Step 1: Create observe.css with CSS variables**

Create `frontend/css/observe.css`:

```css
/* Observe View Styles */

:root {
  /* Primary Colors */
  --primary-blue: #667eea;
  --primary-purple: #764ba2;
  --success-green: #10b981;
  --warning-yellow: #f59e0b;
  --danger-red: #ef4444;
  --info-blue: #3b82f6;

  /* Status Colors */
  --status-complete: #10b981;
  --status-partial: #f59e0b;
  --status-new: #6b7280;
  --status-executing: #3b82f6;

  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-panel: #ffffff;
  --bg-hover: #f3f4f6;
  --bg-drawer: #f9fafb;

  /* Borders */
  --border-color: #e5e7eb;
  --border-radius: 8px;
  --border-radius-small: 4px;

  /* Shadows */
  --shadow-small: 0 1px 3px rgba(0,0,0,0.1);
  --shadow-medium: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-large: 0 10px 25px rgba(0,0,0,0.15);

  /* Text */
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --text-tertiary: #9ca3af;

  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
}

/* Layout */
.observe-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: var(--spacing-lg);
  min-height: 600px;
}

/* Sidebar */
.observe-sidebar {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-md);
  overflow-y: auto;
  max-height: calc(100vh - 200px);
}

/* Main Area */
.observe-main {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
}

/* Panels */
.panel {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
  transition: box-shadow 200ms ease;
}

.panel:hover {
  box-shadow: var(--shadow-small);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  user-select: none;
}

.panel-collapsible .panel-header:hover {
  background: var(--bg-hover);
  margin: calc(-1 * var(--spacing-sm));
  padding: var(--spacing-sm);
  border-radius: var(--border-radius-small);
}

.panel-body {
  max-height: 1000px;
  overflow: hidden;
  transition: max-height 300ms ease-in-out, opacity 200ms ease;
  opacity: 1;
}

.panel-body.collapsed {
  max-height: 0;
  opacity: 0;
}

/* Buttons */
.btn {
  padding: 10px 16px;
  border-radius: var(--border-radius-small);
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms ease;
  border: none;
  font-size: 0.95em;
  font-family: inherit;
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary-blue), var(--primary-purple));
  color: white;
  box-shadow: var(--shadow-small);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-medium);
  filter: brightness(110%);
}

.btn-primary:active {
  transform: translateY(0);
  filter: brightness(95%);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: transparent;
  border: 2px solid var(--border-color);
  color: var(--text-primary);
}

.btn-danger {
  background: var(--danger-red);
  color: white;
}

.btn-success {
  background: var(--success-green);
  color: white;
}

/* Status Indicators */
.status-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
}

.status-connected {
  background: var(--success-green);
  box-shadow: 0 0 8px var(--success-green);
  animation: pulse 2s ease-in-out infinite;
}

.status-connecting {
  background: var(--warning-yellow);
  box-shadow: 0 0 8px var(--warning-yellow);
  animation: pulse 1s ease-in-out infinite;
}

.status-disconnected {
  background: var(--text-tertiary);
}

.status-error {
  background: var(--danger-red);
  box-shadow: 0 0 8px var(--danger-red);
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Tabs */
.tab-container {
  display: flex;
  gap: var(--spacing-sm);
  border-bottom: 2px solid var(--border-color);
  margin-bottom: var(--spacing-lg);
}

.tab {
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  border-bottom: 3px solid transparent;
  color: var(--text-secondary);
  font-weight: 500;
  transition: all 200ms ease;
  user-select: none;
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
}

.tab:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.tab.active {
  color: var(--primary-blue);
  border-bottom-color: var(--primary-blue);
}

/* Input Fields */
input[type="text"],
input[type="number"],
select {
  padding: 8px 12px;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-small);
  font-size: 0.95em;
  transition: border-color 200ms ease;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: inherit;
}

input:focus,
select:focus {
  outline: none;
  border-color: var(--primary-blue);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

input:disabled {
  background: var(--bg-secondary);
  color: var(--text-tertiary);
  cursor: not-allowed;
}

/* Form Grid */
.form-row {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: var(--spacing-sm);
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.form-row label {
  font-size: 0.9em;
  color: var(--text-secondary);
}

/* Utility Classes */
.text-sm { font-size: 0.85em; }
.text-xs { font-size: 0.75em; }
.text-secondary { color: var(--text-secondary); }
.text-tertiary { color: var(--text-tertiary); }
.mb-sm { margin-bottom: var(--spacing-sm); }
.mb-md { margin-bottom: var(--spacing-md); }
.mb-lg { margin-bottom: var(--spacing-lg); }

/* Hidden */
.hidden {
  display: none !important;
}
```

**Step 2: Link CSS in index.html**

Open `frontend/index.html` and add before closing `</head>`:

```html
<link rel="stylesheet" href="css/observe.css">
```

**Step 3: Verify CSS loads**

Run: Open browser to `http://localhost:8000` (after starting server)
Expected: No console errors, CSS variables defined in browser dev tools

**Step 4: Commit**

```bash
git add frontend/css/observe.css frontend/index.html
git commit -m "feat: add observe view CSS framework with variables and base styles"
```

---

## Task 2: Create Global State Management Module

**Files:**
- Create: `frontend/js/observe-state.js`
- Modify: `frontend/index.html` (add script tag)

**Step 1: Create observe-state.js with global state object**

Create `frontend/js/observe-state.js`:

```javascript
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
```

**Step 2: Add script tag to index.html**

Open `frontend/index.html` and add before closing `</body>`:

```html
<script src="js/observe-state.js"></script>
```

**Step 3: Verify state object exists**

Run: Open browser console, type `observeState`
Expected: Object with connection, execution, library, telemetry, controls, ui properties

**Step 4: Test state update function**

Run in console:
```javascript
updateState('connection', { status: 'connected' });
console.log(observeState.connection.status);
```
Expected: Logs "connected"

**Step 5: Commit**

```bash
git add frontend/js/observe-state.js frontend/index.html
git commit -m "feat: add observe state management with listeners"
```

---

## Task 3: Create Three-Zone HTML Layout

**Files:**
- Modify: `frontend/index.html:1967-2166` (Observe tab section)

**Step 1: Replace Observe tab with new three-zone layout**

In `frontend/index.html`, replace the Observe tab section (approximately lines 1967-2166) with:

```html
<!-- Observe Tab -->
<div id="observe-tab" class="tab-content">
  <!-- Three-Zone Layout -->
  <div class="observe-layout">

    <!-- Left Sidebar -->
    <aside class="observe-sidebar">

      <!-- Connection Section -->
      <section class="panel panel-collapsible" id="connection-panel">
        <header class="panel-header" onclick="toggleSidebarSection('connection')">
          <h3>🔌 Connection</h3>
          <span class="collapse-icon">▼</span>
        </header>
        <div class="panel-body" id="connection-panel-body">
          <div class="form-row">
            <label for="telescope-host">IP Address</label>
            <input type="text" id="telescope-host" value="192.168.2.47" />
          </div>
          <div class="form-row">
            <label for="telescope-port">Port</label>
            <input type="number" id="telescope-port" value="4700" />
          </div>
          <button id="connect-btn" class="btn btn-primary" onclick="handleConnect()">
            Connect
          </button>
          <div id="connection-status" class="text-sm mb-sm">
            <span class="status-indicator status-disconnected"></span>
            <span id="connection-status-text">Disconnected</span>
          </div>
          <div id="firmware-version" class="text-xs text-secondary hidden">
            Firmware: <span id="firmware-text">--</span>
          </div>
        </div>
      </section>

      <!-- Execution Section -->
      <section class="panel panel-collapsible" id="execution-panel">
        <header class="panel-header" onclick="toggleSidebarSection('execution')">
          <h3>⚡ Execution</h3>
          <span class="collapse-icon">▼</span>
        </header>
        <div class="panel-body" id="execution-panel-body">
          <div id="current-plan-info" class="mb-md">
            <div class="text-sm text-secondary">Current Plan:</div>
            <div id="plan-name" class="text-sm">No plan loaded</div>
            <div id="plan-summary" class="text-xs text-tertiary">--</div>
          </div>
          <button id="execute-btn" class="btn btn-primary mb-sm" onclick="handleExecute()" disabled>
            ▶ Execute Plan
          </button>
          <button id="abort-btn" class="btn btn-danger mb-sm" onclick="handleAbort()" disabled>
            ⏹ Abort
          </button>
          <button id="park-btn" class="btn btn-secondary" onclick="handlePark()" disabled>
            🏠 Park
          </button>
          <div id="execution-status" class="text-xs text-secondary mb-sm">
            Status: <span id="execution-status-text">Ready</span>
          </div>
        </div>
      </section>

      <!-- Imaging Controls Section -->
      <section class="panel panel-collapsible" id="imaging-panel">
        <header class="panel-header" onclick="toggleSidebarSection('imaging')">
          <h3>📷 Imaging</h3>
          <span class="collapse-icon">▶</span>
        </header>
        <div class="panel-body collapsed" id="imaging-panel-body">
          <div class="mb-sm">
            <button class="btn btn-success" onclick="handleStartImaging()">▶ Start</button>
            <button class="btn btn-danger" onclick="handleStopImaging()">⏹ Stop</button>
          </div>
          <div class="form-row">
            <label for="stack-exposure">Stack (sec)</label>
            <input type="number" id="stack-exposure" value="10" min="1" max="600" />
          </div>
          <div class="form-row">
            <label for="preview-exposure">Preview (sec)</label>
            <input type="number" id="preview-exposure" value="0.5" min="0.1" max="10" step="0.1" />
          </div>
          <div class="form-row">
            <label>
              <input type="checkbox" id="dither-enabled" checked />
              Dither
            </label>
          </div>
          <div class="form-row">
            <label for="dither-pixels">Pixels</label>
            <input type="number" id="dither-pixels" value="50" min="10" max="200" />
          </div>
          <div class="form-row">
            <label for="dither-interval">Interval</label>
            <input type="number" id="dither-interval" value="10" min="1" max="100" />
          </div>
        </div>
      </section>

      <!-- Telescope Controls Section -->
      <section class="panel panel-collapsible" id="telescope-panel">
        <header class="panel-header" onclick="toggleSidebarSection('telescope')">
          <h3>🔭 Telescope</h3>
          <span class="collapse-icon">▶</span>
        </header>
        <div class="panel-body collapsed" id="telescope-panel-body">
          <div class="mb-md">
            <h4 class="text-sm mb-sm">Quick Actions</h4>
            <button class="btn btn-primary mb-sm" onclick="handleAutoFocus()">Auto Focus</button>
            <button class="btn btn-danger mb-sm" onclick="handleStopSlew()">Stop Slew</button>
            <button class="btn btn-danger" onclick="handleEmergencyStop()">Emergency Stop</button>
          </div>
          <div class="mb-md">
            <h4 class="text-sm mb-sm">Manual Goto</h4>
            <div class="form-row">
              <label for="goto-ra">RA (h)</label>
              <input type="number" id="goto-ra" value="0" min="0" max="24" step="0.1" />
            </div>
            <div class="form-row">
              <label for="goto-dec">Dec (°)</label>
              <input type="number" id="goto-dec" value="0" min="-90" max="90" step="0.1" />
            </div>
            <button class="btn btn-primary" onclick="handleGoto()">Slew</button>
          </div>
        </div>
      </section>

      <!-- Hardware Section -->
      <section class="panel panel-collapsible" id="hardware-panel">
        <header class="panel-header" onclick="toggleSidebarSection('hardware')">
          <h3>🔧 Hardware</h3>
          <span class="collapse-icon">▶</span>
        </header>
        <div class="panel-body collapsed" id="hardware-panel-body">
          <div class="mb-md">
            <h4 class="text-sm mb-sm">Dew Heater</h4>
            <div class="form-row">
              <label>
                <input type="checkbox" id="dew-heater-enabled" onchange="handleDewHeater()" />
                Enabled
              </label>
            </div>
            <div class="form-row">
              <label for="dew-heater-power">Power (%)</label>
              <input type="number" id="dew-heater-power" value="90" min="0" max="100" />
            </div>
          </div>
          <div class="mb-md">
            <h4 class="text-sm mb-sm">Focuser</h4>
            <div id="focus-position" class="text-xs text-secondary mb-sm">
              Position: <span id="focus-pos-text">0</span> / 2600
            </div>
            <button class="btn btn-secondary" onclick="handleFocusMove(-100)">-100</button>
            <button class="btn btn-secondary" onclick="handleFocusMove(-10)">-10</button>
            <button class="btn btn-secondary" onclick="handleFocusMove(10)">+10</button>
            <button class="btn btn-secondary" onclick="handleFocusMove(100)">+100</button>
          </div>
        </div>
      </section>

      <!-- Quick Info Section -->
      <section class="panel panel-collapsible" id="info-panel">
        <header class="panel-header" onclick="toggleSidebarSection('info')">
          <h3>ℹ️ Info</h3>
          <span class="collapse-icon">▶</span>
        </header>
        <div class="panel-body collapsed" id="info-panel-body">
          <div class="text-xs">
            <div class="mb-sm">
              <span class="text-secondary">Target:</span>
              <span id="info-target">--</span>
            </div>
            <div class="mb-sm">
              <span class="text-secondary">RA/Dec:</span>
              <span id="info-coords">-- / --</span>
            </div>
            <div class="mb-sm">
              <span class="text-secondary">Altitude:</span>
              <span id="info-altitude">--</span>
            </div>
            <div class="mb-sm">
              <span class="text-secondary">Frames:</span>
              <span id="info-frames">-- / --</span>
            </div>
          </div>
        </div>
      </section>

    </aside>

    <!-- Right Main Area -->
    <main class="observe-main">

      <!-- Tab Navigation -->
      <nav class="tab-container">
        <button class="tab active" onclick="showMainTab('execution')">Execution</button>
        <button class="tab" onclick="showMainTab('library')">Library</button>
        <button class="tab" onclick="showMainTab('telemetry')">Telemetry</button>
        <button class="tab" onclick="showMainTab('live')">Live View</button>
      </nav>

      <!-- Execution Tab Content -->
      <div id="execution-content" class="tab-content-main">
        <div id="execution-banner" class="hidden">
          <h2>🔭 EXECUTING PLAN</h2>
          <p id="execution-current-target">Current: --</p>
          <p id="execution-progress-text">Progress: 0%</p>
        </div>
        <div id="execution-timeline" class="hidden">
          <h3>Timeline</h3>
          <div id="timeline-content">--</div>
        </div>
        <div id="execution-details">
          <h3>Current Target Details</h3>
          <div id="target-details-content">
            <p class="text-secondary">No active execution</p>
          </div>
        </div>
      </div>

      <!-- Library Tab Content -->
      <div id="library-content" class="tab-content-main hidden">
        <div id="library-toolbar" class="mb-md">
          <input type="text" id="library-search" placeholder="Search targets..." />
          <select id="library-filter">
            <option value="all">All</option>
            <option value="complete">Complete</option>
            <option value="needs_more">Needs More Data</option>
            <option value="new">New</option>
          </select>
          <select id="library-sort">
            <option value="recent">Most Recent</option>
            <option value="name">Name</option>
            <option value="exposure">Total Exposure</option>
            <option value="quality">Quality</option>
          </select>
          <button class="btn btn-primary" onclick="handleTransferFiles()">Transfer from Seestar</button>
        </div>
        <div id="library-grid">
          <p class="text-secondary">No capture history available</p>
        </div>
      </div>

      <!-- Telemetry Tab Content -->
      <div id="telemetry-content" class="tab-content-main hidden">
        <h3>Current Position</h3>
        <div id="telemetry-position">
          <p>RA: <span id="telem-ra">--</span></p>
          <p>Dec: <span id="telem-dec">--</span></p>
          <p>Alt: <span id="telem-alt">--</span></p>
          <p>Az: <span id="telem-az">--</span></p>
        </div>
        <h3>Device Status</h3>
        <div id="telemetry-device">
          <p class="text-secondary">Not connected</p>
        </div>
      </div>

      <!-- Live View Tab Content -->
      <div id="live-content" class="tab-content-main hidden">
        <h3>Live View</h3>
        <p class="text-secondary">Live view integration coming soon</p>
      </div>

    </main>

  </div>
</div>
```

**Step 2: Verify HTML structure**

Run: Open browser to Observe tab
Expected: Three-zone layout visible with sidebar panels and main area tabs

**Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: create three-zone Observe view layout structure"
```

---

## Task 4: Implement Sidebar Panel Collapse Functionality

**Files:**
- Create: `frontend/js/observe-ui.js`
- Modify: `frontend/index.html` (add script tag)

**Step 1: Create observe-ui.js with panel collapse functions**

Create `frontend/js/observe-ui.js`:

```javascript
/**
 * Observe View UI Functions
 *
 * Handles UI interactions and updates.
 */

/**
 * Toggle sidebar panel expansion
 * @param {string} sectionName - Name of section to toggle
 */
function toggleSidebarSection(sectionName) {
  const body = document.getElementById(`${sectionName}-panel-body`);
  const panel = document.getElementById(`${sectionName}-panel`);
  const icon = panel.querySelector('.collapse-icon');

  if (!body) {
    console.error(`Panel body not found: ${sectionName}-panel-body`);
    return;
  }

  const isCollapsed = body.classList.contains('collapsed');

  // Toggle collapse
  body.classList.toggle('collapsed');

  // Update icon
  if (icon) {
    icon.textContent = isCollapsed ? '▼' : '▶';
  }

  // Update state
  updateState('ui', {
    activeSidebarSection: {
      ...observeState.ui.activeSidebarSection,
      [sectionName]: isCollapsed
    }
  });
}

/**
 * Show main tab
 * @param {string} tabName - Name of tab to show (execution, library, telemetry, live)
 */
function showMainTab(tabName) {
  // Update tab buttons
  document.querySelectorAll('.tab-container .tab').forEach(tab => {
    tab.classList.remove('active');
  });
  event.target.classList.add('active');

  // Update tab content
  document.querySelectorAll('.tab-content-main').forEach(content => {
    content.classList.add('hidden');
  });
  document.getElementById(`${tabName}-content`).classList.remove('hidden');

  // Update state
  updateState('ui', { activeMainTab: tabName });

  // Load tab-specific data
  switch (tabName) {
    case 'library':
      loadCaptureLibrary();
      break;
    case 'telemetry':
      updateTelemetryDisplay();
      break;
  }
}

/**
 * Update connection UI based on state
 */
function updateConnectionUI() {
  const statusIndicator = document.querySelector('#connection-status .status-indicator');
  const statusText = document.getElementById('connection-status-text');
  const connectBtn = document.getElementById('connect-btn');
  const firmwareDiv = document.getElementById('firmware-version');
  const firmwareText = document.getElementById('firmware-text');

  const { status, firmware, error } = observeState.connection;

  // Update status indicator
  statusIndicator.className = 'status-indicator';
  switch (status) {
    case 'connected':
      statusIndicator.classList.add('status-connected');
      statusText.textContent = 'Connected';
      connectBtn.textContent = 'Disconnect';
      connectBtn.classList.remove('btn-primary');
      connectBtn.classList.add('btn-secondary');

      // Show firmware
      if (firmware) {
        firmwareText.textContent = firmware;
        firmwareDiv.classList.remove('hidden');
      }

      // Enable execution controls
      document.getElementById('park-btn').disabled = false;
      break;

    case 'connecting':
      statusIndicator.classList.add('status-connecting');
      statusText.textContent = 'Connecting...';
      connectBtn.disabled = true;
      break;

    case 'disconnected':
      statusIndicator.classList.add('status-disconnected');
      statusText.textContent = 'Disconnected';
      connectBtn.textContent = 'Connect';
      connectBtn.classList.add('btn-primary');
      connectBtn.classList.remove('btn-secondary');
      connectBtn.disabled = false;
      firmwareDiv.classList.add('hidden');

      // Disable execution controls
      document.getElementById('execute-btn').disabled = true;
      document.getElementById('park-btn').disabled = true;
      break;

    case 'error':
      statusIndicator.classList.add('status-error');
      statusText.textContent = `Error: ${error || 'Unknown'}`;
      connectBtn.textContent = 'Retry';
      connectBtn.disabled = false;
      break;
  }
}

// Subscribe to connection state changes
onStateChange('connection', updateConnectionUI);
```

**Step 2: Add script tag to index.html**

Open `frontend/index.html` and add before closing `</body>` (after observe-state.js):

```html
<script src="js/observe-ui.js"></script>
```

**Step 3: Verify panel collapse works**

Run: Open browser, click on panel headers
Expected: Panels expand/collapse with smooth animation, icon changes

**Step 4: Verify tab switching works**

Run: Click on Library, Telemetry, Live View tabs
Expected: Tab content switches, active tab highlighted

**Step 5: Commit**

```bash
git add frontend/js/observe-ui.js frontend/index.html
git commit -m "feat: add sidebar panel collapse and tab switching"
```

---

## Task 5: Implement Connection Management

**Files:**
- Create: `frontend/js/observe-connection.js`
- Modify: `frontend/index.html` (add script tag)

**Step 1: Create observe-connection.js with API functions**

Create `frontend/js/observe-connection.js`:

```javascript
/**
 * Observe View Connection Management
 *
 * Handles telescope connection and API communication.
 */

const API_BASE = '';  // Same origin

/**
 * Connect to telescope
 */
async function handleConnect() {
  const { status } = observeState.connection;

  // If already connected, disconnect
  if (status === 'connected') {
    await disconnectTelescope();
    return;
  }

  // Connect
  await connectTelescope();
}

/**
 * Connect to telescope
 */
async function connectTelescope() {
  const host = document.getElementById('telescope-host').value;
  const port = parseInt(document.getElementById('telescope-port').value);

  // Update state to connecting
  updateState('connection', {
    status: 'connecting',
    host,
    port,
    error: null
  });

  try {
    const response = await fetch(`${API_BASE}/api/telescope/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, port })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Update state to connected
    updateState('connection', {
      status: 'connected',
      firmware: data.firmware || 'Unknown',
      lastUpdate: Date.now()
    });

    // Start telemetry polling
    startTelemetryPolling();

  } catch (error) {
    console.error('Connection failed:', error);
    updateState('connection', {
      status: 'error',
      error: error.message
    });
  }
}

/**
 * Disconnect from telescope
 */
async function disconnectTelescope() {
  try {
    await fetch(`${API_BASE}/api/telescope/disconnect`, {
      method: 'POST'
    });

    // Stop polling
    stopTelemetryPolling();

    // Update state
    updateState('connection', {
      status: 'disconnected',
      firmware: null,
      lastUpdate: null
    });

  } catch (error) {
    console.error('Disconnect failed:', error);
  }
}

/**
 * Telemetry polling
 */
let telemetryPollInterval = null;

function startTelemetryPolling() {
  if (telemetryPollInterval) {
    clearInterval(telemetryPollInterval);
  }

  telemetryPollInterval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/telescope/status`);
      if (response.ok) {
        const data = await response.json();
        updateState('telemetry', {
          deviceState: data,
          lastUpdate: Date.now()
        });
      }
    } catch (error) {
      console.error('Telemetry update failed:', error);
    }
  }, 1000);  // Poll every 1 second
}

function stopTelemetryPolling() {
  if (telemetryPollInterval) {
    clearInterval(telemetryPollInterval);
    telemetryPollInterval = null;
  }
}

/**
 * Send telescope command
 * @param {string} command - Command name
 * @param {object} params - Command parameters
 * @returns {Promise<any>} Command response
 */
async function sendTelescopeCommand(command, params = {}) {
  const response = await fetch(`${API_BASE}/api/telescope/command/${command}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });

  if (!response.ok) {
    throw new Error(`Command failed: ${response.statusText}`);
  }

  return response.json();
}
```

**Step 2: Add script tag to index.html**

Open `frontend/index.html` and add before closing `</body>` (after observe-ui.js):

```html
<script src="js/observe-connection.js"></script>
```

**Step 3: Verify connection works**

Run: Start backend server, open browser, enter telescope IP, click Connect
Expected: Status changes to "Connecting..." then "Connected", firmware displays

**Step 4: Verify disconnect works**

Run: Click "Disconnect" button
Expected: Status changes to "Disconnected", button text changes to "Connect"

**Step 5: Commit**

```bash
git add frontend/js/observe-connection.js frontend/index.html
git commit -m "feat: add telescope connection management with polling"
```

---

## Task 6: Implement Basic Telescope Controls

**Files:**
- Create: `frontend/js/observe-controls.js`
- Modify: `frontend/index.html` (add script tag)

**Step 1: Create observe-controls.js with control handlers**

Create `frontend/js/observe-controls.js`:

```javascript
/**
 * Observe View Telescope Controls
 *
 * Handlers for telescope control actions.
 */

/**
 * Execute current plan
 */
async function handleExecute() {
  if (!observeState.execution.currentPlan) {
    alert('No plan loaded');
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/api/telescope/execute`, {
      method: 'POST'
    });

    if (response.ok) {
      updateState('execution', { isExecuting: true, startTime: Date.now() });
      startExecutionPolling();
    } else {
      throw new Error('Execution failed');
    }
  } catch (error) {
    alert(`Failed to execute: ${error.message}`);
  }
}

/**
 * Abort current execution
 */
async function handleAbort() {
  if (!confirm('Abort current execution?')) {
    return;
  }

  try {
    await fetch(`${API_BASE}/api/telescope/abort`, { method: 'POST' });
    updateState('execution', { isExecuting: false });
    stopExecutionPolling();
  } catch (error) {
    alert(`Failed to abort: ${error.message}`);
  }
}

/**
 * Park telescope
 */
async function handlePark() {
  try {
    await sendTelescopeCommand('park');
    alert('Telescope parked');
  } catch (error) {
    alert(`Failed to park: ${error.message}`);
  }
}

/**
 * Start imaging
 */
async function handleStartImaging() {
  const stackExposure = parseInt(document.getElementById('stack-exposure').value) * 1000;
  const previewExposure = parseFloat(document.getElementById('preview-exposure').value) * 1000;

  try {
    await sendTelescopeCommand('start_imaging', {
      restart: true
    });

    await sendTelescopeCommand('set_exposure', {
      stack_exposure_ms: stackExposure,
      continuous_exposure_ms: previewExposure
    });

    alert('Imaging started');
  } catch (error) {
    alert(`Failed to start imaging: ${error.message}`);
  }
}

/**
 * Stop imaging
 */
async function handleStopImaging() {
  try {
    await sendTelescopeCommand('stop_imaging');
    alert('Imaging stopped');
  } catch (error) {
    alert(`Failed to stop imaging: ${error.message}`);
  }
}

/**
 * Auto focus
 */
async function handleAutoFocus() {
  try {
    await sendTelescopeCommand('auto_focus');
    alert('Auto focus started');
  } catch (error) {
    alert(`Failed to start auto focus: ${error.message}`);
  }
}

/**
 * Stop slewing
 */
async function handleStopSlew() {
  try {
    await sendTelescopeCommand('stop_slew');
    alert('Slew stopped');
  } catch (error) {
    alert(`Failed to stop slew: ${error.message}`);
  }
}

/**
 * Emergency stop
 */
async function handleEmergencyStop() {
  if (!confirm('Emergency stop all telescope movement?')) {
    return;
  }

  try {
    await sendTelescopeCommand('stop_telescope_movement');
    alert('Telescope stopped');
  } catch (error) {
    alert(`Failed to stop telescope: ${error.message}`);
  }
}

/**
 * Goto coordinates
 */
async function handleGoto() {
  const ra = parseFloat(document.getElementById('goto-ra').value);
  const dec = parseFloat(document.getElementById('goto-dec').value);

  if (isNaN(ra) || isNaN(dec)) {
    alert('Invalid coordinates');
    return;
  }

  try {
    await sendTelescopeCommand('slew_to_coordinates', {
      ra_hours: ra,
      dec_degrees: dec
    });
    alert(`Slewing to RA ${ra}h, Dec ${dec}°`);
  } catch (error) {
    alert(`Failed to slew: ${error.message}`);
  }
}

/**
 * Move focuser
 * @param {number} offset - Relative offset to move
 */
async function handleFocusMove(offset) {
  try {
    await sendTelescopeCommand('move_focuser_relative', {
      offset
    });

    // Update position display (will be updated by telemetry)
    const currentPos = observeState.controls.focus.position;
    const newPos = Math.max(0, Math.min(2600, currentPos + offset));
    updateState('controls', {
      focus: { ...observeState.controls.focus, position: newPos }
    });
  } catch (error) {
    alert(`Failed to move focuser: ${error.message}`);
  }
}

/**
 * Toggle dew heater
 */
async function handleDewHeater() {
  const enabled = document.getElementById('dew-heater-enabled').checked;
  const power = parseInt(document.getElementById('dew-heater-power').value);

  try {
    await sendTelescopeCommand('set_dew_heater', {
      enabled,
      power_level: power
    });

    updateState('controls', {
      dewHeater: { enabled, power }
    });
  } catch (error) {
    alert(`Failed to set dew heater: ${error.message}`);
  }
}

/**
 * Execution polling
 */
let executionPollInterval = null;

function startExecutionPolling() {
  if (executionPollInterval) {
    clearInterval(executionPollInterval);
  }

  executionPollInterval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/telescope/progress`);
      if (response.ok) {
        const data = await response.json();

        updateState('execution', {
          currentTarget: data.current_target,
          currentPhase: data.phase,
          progress: data.progress_percent,
          framesCurrent: data.frames_current || 0,
          framesTotal: data.frames_total || 0,
          estimatedRemainingSeconds: data.estimated_remaining || 0
        });

        updateExecutionDisplay();
      }
    } catch (error) {
      console.error('Failed to fetch execution progress:', error);
    }
  }, 2000);  // Poll every 2 seconds
}

function stopExecutionPolling() {
  if (executionPollInterval) {
    clearInterval(executionPollInterval);
    executionPollInterval = null;
  }
}

/**
 * Update execution display
 */
function updateExecutionDisplay() {
  const { isExecuting, currentTarget, progress, currentPhase } = observeState.execution;

  const banner = document.getElementById('execution-banner');
  const targetText = document.getElementById('execution-current-target');
  const progressText = document.getElementById('execution-progress-text');

  if (isExecuting) {
    banner.classList.remove('hidden');
    targetText.textContent = `Current: ${currentTarget || '--'}`;
    progressText.textContent = `Progress: ${progress}% (${currentPhase || '--'})`;
  } else {
    banner.classList.add('hidden');
  }

  // Update Info panel
  document.getElementById('info-target').textContent = currentTarget || '--';
  document.getElementById('info-frames').textContent =
    `${observeState.execution.framesCurrent} / ${observeState.execution.framesTotal}`;
}
```

**Step 2: Add script tag to index.html**

Open `frontend/index.html` and add before closing `</body>` (after observe-connection.js):

```html
<script src="js/observe-controls.js"></script>
```

**Step 3: Verify controls work**

Run: Connect to telescope, try clicking imaging controls
Expected: Commands sent to backend, appropriate responses

**Step 4: Verify focus controls work**

Run: Click +10, -10, +100, -100 buttons
Expected: Commands sent, position updates

**Step 5: Commit**

```bash
git add frontend/js/observe-controls.js frontend/index.html
git commit -m "feat: add telescope control handlers (imaging, focus, goto)"
```

---

## Task 7: Implement Capture Library Tab

**Files:**
- Create: `frontend/js/observe-library.js`
- Modify: `frontend/index.html` (add script tag)

**Step 1: Create observe-library.js with library functions**

Create `frontend/js/observe-library.js`:

```javascript
/**
 * Observe View Capture Library
 *
 * Handles capture history display and file transfers.
 */

/**
 * Load capture library from backend
 */
async function loadCaptureLibrary() {
  updateState('library', { loading: true });

  try {
    const response = await fetch(`${API_BASE}/api/captures`);

    if (!response.ok) {
      throw new Error(`Failed to load library: ${response.statusText}`);
    }

    const data = await response.json();

    updateState('library', {
      targets: data,
      loading: false
    });

    applyLibraryFilters();

  } catch (error) {
    console.error('Failed to load capture library:', error);
    updateState('library', { loading: false });
  }
}

/**
 * Apply search/filter/sort to library
 */
function applyLibraryFilters() {
  let filtered = [...observeState.library.targets];

  // Apply search
  const search = document.getElementById('library-search').value.toLowerCase();
  if (search) {
    filtered = filtered.filter(t =>
      t.catalog_id.toLowerCase().includes(search) ||
      (t.name && t.name.toLowerCase().includes(search))
    );
  }

  // Apply status filter
  const statusFilter = document.getElementById('library-filter').value;
  if (statusFilter !== 'all') {
    filtered = filtered.filter(t => t.status === statusFilter);
  }

  // Apply sort
  const sortBy = document.getElementById('library-sort').value;
  switch (sortBy) {
    case 'recent':
      filtered.sort((a, b) =>
        new Date(b.last_captured_at) - new Date(a.last_captured_at)
      );
      break;
    case 'name':
      filtered.sort((a, b) => a.catalog_id.localeCompare(b.catalog_id));
      break;
    case 'exposure':
      filtered.sort((a, b) =>
        b.total_exposure_seconds - a.total_exposure_seconds
      );
      break;
    case 'quality':
      filtered.sort((a, b) =>
        (a.best_fwhm || 999) - (b.best_fwhm || 999)
      );
      break;
  }

  updateState('library', { filteredTargets: filtered });
  renderLibraryGrid();
}

/**
 * Render library grid
 */
function renderLibraryGrid() {
  const grid = document.getElementById('library-grid');
  const { filteredTargets, loading } = observeState.library;

  if (loading) {
    grid.innerHTML = '<p class="text-secondary">Loading...</p>';
    return;
  }

  if (filteredTargets.length === 0) {
    grid.innerHTML = '<p class="text-secondary">No targets found</p>';
    return;
  }

  grid.innerHTML = filteredTargets.map(target => `
    <div class="target-card panel">
      <h4>${target.catalog_id}</h4>
      <div class="text-xs">
        <span class="status-badge status-${target.status || 'new'}">
          ${getStatusIcon(target.status)} ${formatStatus(target.status)}
        </span>
      </div>
      <div class="text-sm text-secondary mb-sm">
        ${formatExposureTime(target.total_exposure_seconds)} |
        ${target.total_frames} frames |
        ${target.total_sessions} sessions
      </div>
      ${target.best_fwhm ? `
        <div class="text-xs text-secondary mb-sm">
          FWHM: ${target.best_fwhm.toFixed(1)}" |
          Stars: ${target.best_star_count}
        </div>
      ` : ''}
      <div class="text-xs text-tertiary mb-md">
        Last: ${formatDate(target.last_captured_at)}
      </div>
      <div>
        <button class="btn btn-secondary text-xs" onclick="viewTargetDetails('${target.catalog_id}')">
          View Details
        </button>
      </div>
    </div>
  `).join('');
}

/**
 * Get status icon
 */
function getStatusIcon(status) {
  switch (status) {
    case 'complete': return '🟢';
    case 'needs_more': return '🟡';
    default: return '🔴';
  }
}

/**
 * Format status text
 */
function formatStatus(status) {
  switch (status) {
    case 'complete': return 'Complete';
    case 'needs_more': return 'Needs More Data';
    default: return 'New Target';
  }
}

/**
 * Format exposure time
 */
function formatExposureTime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

/**
 * Format date
 */
function formatDate(dateStr) {
  if (!dateStr) return '--';
  const date = new Date(dateStr);
  return date.toLocaleDateString();
}

/**
 * View target details
 */
async function viewTargetDetails(catalogId) {
  try {
    const response = await fetch(`${API_BASE}/api/captures/${catalogId}`);
    if (!response.ok) {
      throw new Error('Failed to load target details');
    }

    const data = await response.json();
    alert(`Target: ${data.catalog_id}\nExposure: ${formatExposureTime(data.total_exposure_seconds)}\nFrames: ${data.total_frames}\nSessions: ${data.total_sessions}`);
  } catch (error) {
    alert(`Failed to load details: ${error.message}`);
  }
}

/**
 * Trigger file transfer
 */
async function handleTransferFiles() {
  if (!confirm('Start file transfer from Seestar? This may take several minutes.')) {
    return;
  }

  updateState('library', {
    transferStatus: {
      inProgress: true,
      currentFile: null,
      filesCompleted: 0,
      filesTotal: 0
    }
  });

  try {
    const response = await fetch(`${API_BASE}/api/captures/transfer`, {
      method: 'POST'
    });

    if (!response.ok) {
      throw new Error('Transfer failed');
    }

    const result = await response.json();
    alert(`Transfer complete!\nTransferred: ${result.transferred}\nScanned: ${result.scanned}\nErrors: ${result.errors}`);

    // Reload library
    await loadCaptureLibrary();

  } catch (error) {
    alert(`Transfer failed: ${error.message}`);
  } finally {
    updateState('library', {
      transferStatus: {
        inProgress: false,
        currentFile: null,
        filesCompleted: 0,
        filesTotal: 0,
        lastSyncTime: Date.now()
      }
    });
  }
}

// Add event listeners for filters
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('library-search');
  const filterSelect = document.getElementById('library-filter');
  const sortSelect = document.getElementById('library-sort');

  if (searchInput) {
    searchInput.addEventListener('input', applyLibraryFilters);
  }

  if (filterSelect) {
    filterSelect.addEventListener('change', applyLibraryFilters);
  }

  if (sortSelect) {
    sortSelect.addEventListener('change', applyLibraryFilters);
  }
});
```

**Step 2: Add CSS for library grid**

Add to `frontend/css/observe.css`:

```css
/* Library Grid */
#library-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
  margin-top: var(--spacing-md);
}

.target-card {
  padding: var(--spacing-md);
}

.target-card h4 {
  margin: 0 0 var(--spacing-sm) 0;
  color: var(--text-primary);
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--border-radius-small);
  font-size: 0.75em;
  font-weight: 600;
}

.status-badge.status-complete {
  background: var(--success-green);
  color: white;
}

.status-badge.status-needs_more {
  background: var(--warning-yellow);
  color: white;
}

.status-badge.status-new {
  background: var(--text-tertiary);
  color: white;
}

/* Library Toolbar */
#library-toolbar {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  gap: var(--spacing-sm);
  align-items: center;
}
```

**Step 3: Add script tag to index.html**

Open `frontend/index.html` and add before closing `</body>` (after observe-controls.js):

```html
<script src="js/observe-library.js"></script>
```

**Step 4: Verify library loads**

Run: Open browser, switch to Library tab
Expected: Library grid displays with capture history cards

**Step 5: Verify search/filter/sort works**

Run: Type in search box, change filter dropdown, change sort dropdown
Expected: Grid updates accordingly

**Step 6: Commit**

```bash
git add frontend/js/observe-library.js frontend/css/observe.css frontend/index.html
git commit -m "feat: add capture library tab with search/filter/sort"
```

---

## Task 8: Implement Telemetry Tab

**Files:**
- Modify: `frontend/js/observe-connection.js` (enhance telemetry polling)
- Create: `frontend/js/observe-telemetry.js`
- Modify: `frontend/index.html` (add script tag)

**Step 1: Enhance telemetry polling in observe-connection.js**

Add to `frontend/js/observe-connection.js` after `startTelemetryPolling()`:

```javascript
/**
 * Update telemetry with position data
 */
async function updateTelemetryPosition() {
  try {
    const response = await sendTelescopeCommand('get_current_coordinates');

    updateState('telemetry', {
      position: {
        ra: response.ra || 0,
        dec: response.dec || 0,
        alt: response.alt || 0,
        az: response.az || 0
      }
    });
  } catch (error) {
    console.error('Failed to update position:', error);
  }
}
```

Modify `startTelemetryPolling()` to include position updates:

```javascript
function startTelemetryPolling() {
  if (telemetryPollInterval) {
    clearInterval(telemetryPollInterval);
  }

  telemetryPollInterval = setInterval(async () => {
    try {
      // Get device state
      const statusResponse = await fetch(`${API_BASE}/api/telescope/status`);
      if (statusResponse.ok) {
        const data = await statusResponse.json();
        updateState('telemetry', {
          deviceState: data,
          lastUpdate: Date.now()
        });
      }

      // Get position (if connected)
      if (observeState.connection.status === 'connected') {
        await updateTelemetryPosition();
      }
    } catch (error) {
      console.error('Telemetry update failed:', error);
    }
  }, 1000);  // Poll every 1 second
}
```

**Step 2: Create observe-telemetry.js**

Create `frontend/js/observe-telemetry.js`:

```javascript
/**
 * Observe View Telemetry Display
 *
 * Handles telemetry data display and updates.
 */

/**
 * Update telemetry display
 */
function updateTelemetryDisplay() {
  const { position, deviceState, lastUpdate } = observeState.telemetry;

  // Update position display
  document.getElementById('telem-ra').textContent = formatRA(position.ra);
  document.getElementById('telem-dec').textContent = formatDec(position.dec);
  document.getElementById('telem-alt').textContent = `${position.alt.toFixed(1)}°`;
  document.getElementById('telem-az').textContent = `${position.az.toFixed(1)}°`;

  // Update device status
  const deviceDiv = document.getElementById('telemetry-device');

  if (observeState.connection.status !== 'connected') {
    deviceDiv.innerHTML = '<p class="text-secondary">Not connected</p>';
    return;
  }

  if (Object.keys(deviceState).length === 0) {
    deviceDiv.innerHTML = '<p class="text-secondary">No data available</p>';
    return;
  }

  deviceDiv.innerHTML = `
    <div class="text-sm">
      <div class="mb-sm">
        <span class="text-secondary">Firmware:</span>
        <span>${deviceState.firmware || '--'}</span>
      </div>
      <div class="mb-sm">
        <span class="text-secondary">Temperature:</span>
        <span>${deviceState.temperature || '--'}°C</span>
      </div>
      <div class="mb-sm">
        <span class="text-secondary">WiFi:</span>
        <span>${deviceState.wifi_status || '--'}</span>
      </div>
      <div class="mb-sm">
        <span class="text-secondary">Last Update:</span>
        <span>${formatTimestamp(lastUpdate)}</span>
      </div>
    </div>
  `;
}

/**
 * Format RA (hours to HMS)
 */
function formatRA(hours) {
  const h = Math.floor(hours);
  const m = Math.floor((hours - h) * 60);
  const s = Math.floor(((hours - h) * 60 - m) * 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

/**
 * Format Dec (degrees to DMS)
 */
function formatDec(degrees) {
  const sign = degrees >= 0 ? '+' : '-';
  const absDeg = Math.abs(degrees);
  const d = Math.floor(absDeg);
  const m = Math.floor((absDeg - d) * 60);
  const s = Math.floor(((absDeg - d) * 60 - m) * 60);
  return `${sign}${d}°${m.toString().padStart(2, '0')}'${s.toString().padStart(2, '0')}"`;
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '--';
  const now = Date.now();
  const diff = Math.floor((now - timestamp) / 1000);

  if (diff < 5) return 'Just now';
  if (diff < 60) return `${diff}s ago`;

  const minutes = Math.floor(diff / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

// Subscribe to telemetry state changes
onStateChange('telemetry', updateTelemetryDisplay);
```

**Step 3: Add script tag to index.html**

Open `frontend/index.html` and add before closing `</body>` (after observe-library.js):

```html
<script src="js/observe-telemetry.js"></script>
```

**Step 4: Verify telemetry displays**

Run: Connect to telescope, switch to Telemetry tab
Expected: Position and device status display, update every 1 second

**Step 5: Verify RA/Dec formatting**

Run: Check RA/Dec display in Telemetry tab
Expected: HMS format for RA, DMS format for Dec

**Step 6: Commit**

```bash
git add frontend/js/observe-connection.js frontend/js/observe-telemetry.js frontend/index.html
git commit -m "feat: add telemetry tab with position and device status"
```

---

## Task 9: Initialize Observe View on Load

**Files:**
- Modify: `frontend/index.html` (add initialization script)

**Step 1: Add initialization script**

Open `frontend/index.html` and add before closing `</body>` (after all other observe scripts):

```html
<script>
  /**
   * Initialize Observe View
   */
  function initializeObserveView() {
    // Restore saved connection settings from localStorage
    const savedHost = localStorage.getItem('telescope_host');
    const savedPort = localStorage.getItem('telescope_port');

    if (savedHost) {
      document.getElementById('telescope-host').value = savedHost;
      updateState('connection', { host: savedHost });
    }

    if (savedPort) {
      document.getElementById('telescope-port').value = savedPort;
      updateState('connection', { port: parseInt(savedPort) });
    }

    // Initialize UI state
    updateConnectionUI();

    // Set up input persistence
    document.getElementById('telescope-host').addEventListener('change', (e) => {
      localStorage.setItem('telescope_host', e.target.value);
    });

    document.getElementById('telescope-port').addEventListener('change', (e) => {
      localStorage.setItem('telescope_port', e.target.value);
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeObserveView);
  } else {
    initializeObserveView();
  }
</script>
```

**Step 2: Verify initialization works**

Run: Refresh browser page
Expected: Connection settings restored from localStorage, UI initialized

**Step 3: Verify settings persist**

Run: Change IP address, refresh page
Expected: IP address retained

**Step 4: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add observe view initialization with settings persistence"
```

---

## Task 10: Add Responsive Design for Mobile

**Files:**
- Modify: `frontend/css/observe.css` (add responsive breakpoints)

**Step 1: Add responsive CSS**

Add to end of `frontend/css/observe.css`:

```css
/* Responsive Design */

/* Tablet */
@media (max-width: 1200px) {
  .observe-layout {
    grid-template-columns: 1fr;
  }

  .observe-sidebar {
    max-height: none;
  }

  #library-toolbar {
    grid-template-columns: 1fr;
  }

  #library-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }
}

/* Mobile */
@media (max-width: 768px) {
  .tab-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
  }

  .tab {
    white-space: nowrap;
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .panel {
    padding: var(--spacing-md);
  }

  .btn {
    width: 100%;
    margin-bottom: var(--spacing-sm);
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .form-row label {
    margin-bottom: var(--spacing-xs);
  }

  #library-grid {
    grid-template-columns: 1fr;
  }

  #library-toolbar {
    grid-template-columns: 1fr;
  }

  #library-toolbar input,
  #library-toolbar select,
  #library-toolbar button {
    width: 100%;
  }
}

/* Touch targets for mobile */
@media (max-width: 768px) {
  .btn,
  input,
  select {
    min-height: 44px;
  }
}
```

**Step 2: Verify responsive layout**

Run: Resize browser window to tablet size (< 1200px)
Expected: Sidebar and main area stack vertically

**Step 3: Verify mobile layout**

Run: Resize browser window to mobile size (< 768px)
Expected: Buttons full width, forms single column, library grid single column

**Step 4: Commit**

```bash
git add frontend/css/observe.css
git commit -m "feat: add responsive design for tablet and mobile"
```

---

## Task 11: Add Loading States and Error Handling

**Files:**
- Modify: `frontend/css/observe.css` (add spinner and error styles)
- Create: `frontend/js/observe-errors.js`
- Modify: `frontend/index.html` (add script tag)

**Step 1: Add spinner and error CSS**

Add to `frontend/css/observe.css`:

```css
/* Loading Spinner */
.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border-color);
  border-top-color: var(--primary-blue);
  border-radius: 50%;
  animation: spin 800ms linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Loading Skeleton */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-secondary) 25%,
    var(--bg-hover) 50%,
    var(--bg-secondary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--border-radius-small);
  height: 20px;
  margin-bottom: var(--spacing-sm);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Error Toast */
.error-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: var(--danger-red);
  color: white;
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-large);
  z-index: 9999;
  animation: slideInRight 300ms ease;
  max-width: 400px;
}

.success-toast {
  background: var(--success-green);
}

.info-toast {
  background: var(--info-blue);
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* Error Banner */
.error-banner {
  background: var(--danger-red);
  color: white;
  padding: var(--spacing-md);
  border-radius: var(--border-radius);
  margin-bottom: var(--spacing-md);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-banner button {
  background: white;
  color: var(--danger-red);
  border: none;
  padding: 4px 12px;
  border-radius: var(--border-radius-small);
  cursor: pointer;
  font-weight: 600;
}
```

**Step 2: Create observe-errors.js**

Create `frontend/js/observe-errors.js`:

```javascript
/**
 * Observe View Error Handling
 *
 * Centralized error handling and user notifications.
 */

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'error', 'success', 'info'
 * @param {number} duration - Duration in ms (default 5000)
 */
function showToast(message, type = 'info', duration = 5000) {
  const toast = document.createElement('div');
  toast.className = `${type}-toast`;
  toast.textContent = message;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * Show error banner
 * @param {object} options - Banner options
 */
function showErrorBanner(options) {
  const { title, message, code, actions = [] } = options;

  const banner = document.createElement('div');
  banner.className = 'error-banner';
  banner.innerHTML = `
    <div>
      <strong>${title}</strong>
      <div class="text-sm">${message}</div>
      ${code ? `<div class="text-xs">Code: ${code}</div>` : ''}
    </div>
    <div>
      ${actions.map(action => `
        <button onclick="${action.action}">${action.label}</button>
      `).join('')}
    </div>
  `;

  const main = document.querySelector('.observe-main');
  main.insertBefore(banner, main.firstChild);
}

/**
 * Handle connection error
 */
async function handleConnectionError(error) {
  showToast(`Connection Error: ${error.message}`, 'error');

  // Auto-retry with exponential backoff
  let retryCount = 0;
  const maxRetries = 3;

  while (retryCount < maxRetries && observeState.connection.status === 'error') {
    await sleep(Math.pow(2, retryCount) * 1000);

    try {
      await connectTelescope();
      showToast('Reconnected successfully', 'success');
      return;
    } catch (retryError) {
      retryCount++;
    }
  }

  // Final failure
  if (observeState.connection.status === 'error') {
    showErrorBanner({
      title: 'Connection Failed',
      message: 'Unable to connect after multiple attempts. Please check your network and telescope.',
      actions: [
        { label: 'Retry', action: 'connectTelescope()' },
        { label: 'Dismiss', action: 'this.parentElement.parentElement.remove()' }
      ]
    });
  }
}

/**
 * Handle API error
 */
function handleAPIError(endpoint, error, context = {}) {
  console.error(`API Error [${endpoint}]:`, error);

  showToast(`API Error: ${error.message}`, 'error');

  // Log to console for debugging
  console.group('API Error Details');
  console.log('Endpoint:', endpoint);
  console.log('Error:', error);
  console.log('Context:', context);
  console.groupEnd();
}

/**
 * Sleep utility
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

**Step 3: Add script tag to index.html**

Open `frontend/index.html` and add before closing `</body>` (after observe-telemetry.js):

```html
<script src="js/observe-errors.js"></script>
```

**Step 4: Update connection error handling**

Modify `connectTelescope()` in `observe-connection.js` to use error handler:

```javascript
} catch (error) {
  console.error('Connection failed:', error);
  updateState('connection', {
    status: 'error',
    error: error.message
  });
  handleConnectionError(error);  // Add this line
}
```

**Step 5: Verify error handling**

Run: Try connecting with invalid IP address
Expected: Error toast appears, retries automatically, error banner shows after max retries

**Step 6: Verify success toast**

Run: Successfully connect to telescope
Expected: Success toast appears briefly

**Step 7: Commit**

```bash
git add frontend/css/observe.css frontend/js/observe-errors.js frontend/index.html frontend/js/observe-connection.js
git commit -m "feat: add error handling with toasts and retry logic"
```

---

## Task 12: Add Bottom Drawer for Advanced Controls

**Files:**
- Modify: `frontend/index.html` (add drawer HTML)
- Modify: `frontend/css/observe.css` (add drawer styles)
- Create: `frontend/js/observe-drawer.js`
- Modify: `frontend/index.html` (add script tag)

**Step 1: Add drawer HTML to index.html**

Add before closing `</div>` of observe-tab:

```html
  </div> <!-- End observe-layout -->

  <!-- Bottom Drawer -->
  <aside id="bottom-drawer" class="bottom-drawer">
    <header class="drawer-header" onclick="toggleDrawer()">
      <span id="drawer-toggle-text">⬆ Advanced Controls</span>
      <span class="text-xs text-secondary" id="drawer-last-tab">
        Last: Advanced Stacking
      </span>
    </header>

    <div id="drawer-content" class="drawer-content hidden">

      <!-- Drawer Tabs -->
      <nav class="tab-container">
        <button class="tab active" onclick="showDrawerTab('stacking')">
          Advanced Stacking
        </button>
        <button class="tab" onclick="showDrawerTab('system')">
          System
        </button>
        <button class="tab" onclick="showDrawerTab('wifi')">
          WiFi
        </button>
        <button class="tab" onclick="showDrawerTab('calibration')">
          Calibration
        </button>
        <button class="tab" onclick="showDrawerTab('hardware')">
          Hardware
        </button>
      </nav>

      <!-- Stacking Tab -->
      <div id="stacking-drawer-content" class="drawer-tab-content">
        <h3>Advanced Stacking Settings</h3>
        <div class="form-row">
          <label>
            <input type="checkbox" id="adv-dbe" />
            Dark Background Extraction
          </label>
        </div>
        <div class="form-row">
          <label>
            <input type="checkbox" id="adv-star-correction" checked />
            Star Correction
          </label>
        </div>
        <div class="form-row">
          <label>
            <input type="checkbox" id="adv-airplane" />
            Airplane/Satellite Removal
          </label>
        </div>
        <div class="form-row">
          <label>
            <input type="checkbox" id="adv-drizzle" />
            Drizzle 2x
          </label>
        </div>
        <button class="btn btn-primary" onclick="applyAdvancedStacking()">
          Apply Settings
        </button>
      </div>

      <!-- System Tab -->
      <div id="system-drawer-content" class="drawer-tab-content hidden">
        <h3>System Management</h3>
        <div class="mb-md">
          <h4>Power Management</h4>
          <button class="btn btn-danger" onclick="handleShutdown()">
            🔌 Shutdown Telescope
          </button>
          <button class="btn btn-secondary" onclick="handleReboot()">
            🔄 Reboot Telescope
          </button>
          <p class="text-xs text-secondary">⚠️ Warning: Will interrupt any active imaging</p>
        </div>
      </div>

      <!-- WiFi Tab -->
      <div id="wifi-drawer-content" class="drawer-tab-content hidden">
        <h3>WiFi Management</h3>
        <p class="text-secondary">WiFi configuration coming soon</p>
      </div>

      <!-- Calibration Tab -->
      <div id="calibration-drawer-content" class="drawer-tab-content hidden">
        <h3>Calibration Tools</h3>
        <p class="text-secondary">Calibration tools coming soon</p>
      </div>

      <!-- Hardware Tab -->
      <div id="hardware-drawer-content" class="drawer-tab-content hidden">
        <h3>Hardware Configuration</h3>
        <p class="text-secondary">Hardware configuration coming soon</p>
      </div>

    </div>
  </aside>

</div> <!-- End observe-tab -->
```

**Step 2: Add drawer styles to observe.css**

Add to `frontend/css/observe.css`:

```css
/* Bottom Drawer */
.bottom-drawer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--bg-drawer);
  border-top: 2px solid var(--border-color);
  box-shadow: 0 -4px 12px rgba(0,0,0,0.1);
  z-index: 100;
  transition: transform 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-header {
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-color);
}

.drawer-header:hover {
  background: var(--bg-hover);
}

.drawer-content {
  max-height: 400px;
  overflow-y: auto;
  padding: var(--spacing-lg);
  transition: max-height 300ms ease-in-out, opacity 200ms ease;
  opacity: 1;
}

.drawer-content.hidden {
  max-height: 0;
  opacity: 0;
  padding: 0;
  overflow: hidden;
}

.drawer-tab-content {
  transition: opacity 200ms ease;
  opacity: 1;
}

.drawer-tab-content.hidden {
  display: none;
  opacity: 0;
}

.drawer-tab-content h3 {
  margin-top: 0;
  margin-bottom: var(--spacing-md);
}

.drawer-tab-content h4 {
  margin-bottom: var(--spacing-sm);
  color: var(--text-secondary);
  font-size: 0.9em;
}
```

**Step 3: Create observe-drawer.js**

Create `frontend/js/observe-drawer.js`:

```javascript
/**
 * Observe View Bottom Drawer
 *
 * Handles bottom drawer advanced controls.
 */

/**
 * Toggle drawer open/closed
 */
function toggleDrawer() {
  const content = document.getElementById('drawer-content');
  const toggleText = document.getElementById('drawer-toggle-text');
  const isOpen = !content.classList.contains('hidden');

  if (isOpen) {
    content.classList.add('hidden');
    toggleText.textContent = '⬆ Advanced Controls';
    updateState('ui', { drawerOpen: false });
  } else {
    content.classList.remove('hidden');
    toggleText.textContent = '⬇ Advanced Controls';
    updateState('ui', { drawerOpen: true });
  }
}

/**
 * Show drawer tab
 */
function showDrawerTab(tabName) {
  // Update tab buttons
  document.querySelectorAll('#bottom-drawer .tab').forEach(tab => {
    tab.classList.remove('active');
  });
  event.target.classList.add('active');

  // Update tab content
  document.querySelectorAll('.drawer-tab-content').forEach(content => {
    content.classList.add('hidden');
  });
  document.getElementById(`${tabName}-drawer-content`).classList.remove('hidden');

  // Update state
  updateState('ui', { drawerActiveTab: tabName });

  // Update last tab text
  document.getElementById('drawer-last-tab').textContent =
    `Last: ${event.target.textContent.trim()}`;
}

/**
 * Apply advanced stacking settings
 */
async function applyAdvancedStacking() {
  const dbe = document.getElementById('adv-dbe').checked;
  const starCorrection = document.getElementById('adv-star-correction').checked;
  const airplane = document.getElementById('adv-airplane').checked;
  const drizzle = document.getElementById('adv-drizzle').checked;

  try {
    await sendTelescopeCommand('configure_advanced_stacking', {
      dark_background_extraction: dbe,
      star_correction: starCorrection,
      airplane_removal: airplane,
      drizzle_2x: drizzle
    });

    updateState('controls', {
      advancedStacking: {
        dbe,
        starCorrection,
        airplaneRemoval: airplane,
        drizzle
      }
    });

    showToast('Advanced stacking settings applied', 'success');
  } catch (error) {
    showToast(`Failed to apply settings: ${error.message}`, 'error');
  }
}

/**
 * Handle telescope shutdown
 */
async function handleShutdown() {
  if (!confirm('Shutdown telescope? This will interrupt any active imaging and power off the device.')) {
    return;
  }

  try {
    await sendTelescopeCommand('shutdown_telescope');
    showToast('Telescope shutting down...', 'info');

    // Disconnect after delay
    setTimeout(() => {
      disconnectTelescope();
    }, 2000);
  } catch (error) {
    showToast(`Failed to shutdown: ${error.message}`, 'error');
  }
}

/**
 * Handle telescope reboot
 */
async function handleReboot() {
  if (!confirm('Reboot telescope? This will interrupt any active imaging and restart the device.')) {
    return;
  }

  try {
    await sendTelescopeCommand('reboot_telescope');
    showToast('Telescope rebooting...', 'info');

    // Disconnect after delay
    setTimeout(() => {
      disconnectTelescope();
    }, 2000);
  } catch (error) {
    showToast(`Failed to reboot: ${error.message}`, 'error');
  }
}

// Keyboard shortcut: Ctrl+D to toggle drawer
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'd') {
    e.preventDefault();
    toggleDrawer();
  }
});
```

**Step 4: Add script tag to index.html**

Open `frontend/index.html` and add before closing `</body>` (after observe-errors.js):

```html
<script src="js/observe-drawer.js"></script>
```

**Step 5: Verify drawer opens/closes**

Run: Click on drawer header
Expected: Drawer slides up/down smoothly

**Step 6: Verify drawer tabs work**

Run: Open drawer, click on System, WiFi, etc. tabs
Expected: Tab content switches

**Step 7: Verify keyboard shortcut**

Run: Press Ctrl+D
Expected: Drawer toggles open/closed

**Step 8: Commit**

```bash
git add frontend/index.html frontend/css/observe.css frontend/js/observe-drawer.js
git commit -m "feat: add bottom drawer for advanced controls"
```

---

## Execution Handoff

Plan complete and saved to `docs/plans/2025-01-01-observe-view-implementation.md`.

Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
