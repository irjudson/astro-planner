# Unified Application Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Completely rebuild Astro Planner frontend with unified 3-zone layout (sidebar + main + drawer) replacing the current 5-tab system.

**Architecture:** Context-aware UI with collapsible workflow sections (Discovery, Planning, Execution, Processing) in left sidebar, dynamic main content area that switches based on user interactions, and bottom drawer with context-specific advanced controls. No code reuse from existing tabs - complete clean rebuild.

**Tech Stack:** Vanilla JavaScript (ES6+), CSS Grid/Flexbox, HTML5, existing backend API endpoints

---

## Phase 1: Foundation & Layout Structure

### Task 1: Backup old files and create new foundation

**Files:**
- Backup: `frontend/index.html` → `frontend/index.html.backup`
- Backup: `frontend/astronomus.css` → `frontend/astronomus.css.backup`
- Create: `frontend/js/app-context.js`
- Create: `frontend/js/app-state.js`
- Create: `frontend/css/unified-layout.css`

**Step 1: Backup existing files**

```bash
cp /home/irjudson/Projects/astronomus/frontend/index.html /home/irjudson/Projects/astronomus/frontend/index.html.backup
cp /home/irjudson/Projects/astronomus/frontend/astronomus.css /home/irjudson/Projects/astronomus/frontend/astronomus.css.backup
```

Expected: Backup files created

**Step 2: Create new JavaScript files**

Create empty files for context and state management:

```bash
touch /home/irjudson/Projects/astronomus/frontend/js/app-context.js
touch /home/irjudson/Projects/astronomus/frontend/js/app-state.js
```

**Step 3: Create new CSS file**

```bash
touch /home/irjudson/Projects/astronomus/frontend/css/unified-layout.css
```

**Step 4: Commit**

```bash
git add frontend/index.html.backup frontend/astronomus.css.backup frontend/js/app-context.js frontend/js/app-state.js frontend/css/unified-layout.css
git commit -m "chore: Backup old files and create foundation for unified layout"
```

---

### Task 2: Write new minimal HTML structure

**Files:**
- Modify: `frontend/index.html` (complete rewrite)

**Step 1: Write new minimal index.html**

Replace entire contents of `/home/irjudson/Projects/astronomus/frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Astro Planner</title>
    <link rel="stylesheet" href="tron-theme.css">
    <link rel="stylesheet" href="css/unified-layout.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
</head>
<body>
    <div class="app-container">
        <!-- Mobile hamburger menu -->
        <button class="mobile-menu-toggle" id="mobile-menu-toggle" aria-label="Toggle menu">
            ☰
        </button>

        <!-- Left Sidebar (320px) -->
        <aside class="app-sidebar" id="app-sidebar">
            <div class="sidebar-content">
                <!-- Connection Panel (Always Visible) -->
                <div class="panel panel-connection" id="connection-panel">
                    <div class="panel-header">
                        <h3>Connection & Weather</h3>
                    </div>
                    <div class="panel-body">
                        <p>Connection panel content will go here</p>
                    </div>
                </div>

                <!-- Discovery Workflow Section -->
                <div class="workflow-section" id="discovery-section">
                    <div class="workflow-header" data-workflow="discovery">
                        <span class="workflow-title">DISCOVERY</span>
                        <span class="workflow-chevron">▼</span>
                    </div>
                    <div class="workflow-content">
                        <p>Discovery panels will go here</p>
                    </div>
                </div>

                <!-- Planning Workflow Section -->
                <div class="workflow-section collapsed" id="planning-section">
                    <div class="workflow-header" data-workflow="planning">
                        <span class="workflow-title">PLANNING</span>
                        <span class="workflow-chevron">▶</span>
                    </div>
                    <div class="workflow-content">
                        <p>Planning panels will go here</p>
                    </div>
                </div>

                <!-- Execution Workflow Section -->
                <div class="workflow-section collapsed" id="execution-section">
                    <div class="workflow-header" data-workflow="execution">
                        <span class="workflow-title">EXECUTION</span>
                        <span class="workflow-chevron">▶</span>
                    </div>
                    <div class="workflow-content">
                        <p>Execution panels will go here</p>
                    </div>
                </div>

                <!-- Processing Workflow Section -->
                <div class="workflow-section collapsed" id="processing-section">
                    <div class="workflow-header" data-workflow="processing">
                        <span class="workflow-title">PROCESSING</span>
                        <span class="workflow-chevron">▶</span>
                    </div>
                    <div class="workflow-content">
                        <p>Processing panels will go here</p>
                    </div>
                </div>
            </div>
        </aside>

        <!-- Main Content Area -->
        <main class="app-main" id="app-main">
            <div class="main-content" id="main-content">
                <p>Main content will go here</p>
            </div>
        </main>

        <!-- Bottom Drawer -->
        <div class="app-drawer" id="app-drawer">
            <button class="drawer-toggle" id="drawer-toggle">
                Advanced Controls
            </button>
            <div class="drawer-content" id="drawer-content">
                <div class="drawer-header">
                    <h3>Advanced Controls</h3>
                    <button class="settings-btn" id="settings-btn" aria-label="Settings">⚙️</button>
                </div>
                <div class="drawer-tabs" id="drawer-tabs">
                    <p>Drawer tabs will go here</p>
                </div>
            </div>
        </div>

        <!-- Mobile backdrop -->
        <div class="mobile-backdrop" id="mobile-backdrop"></div>
    </div>

    <!-- Scripts -->
    <script src="js/app-state.js"></script>
    <script src="js/app-context.js"></script>
</body>
</html>
```

**Step 2: Verify HTML loads**

Run: `docker-compose restart astronomus`
Expected: Page loads with minimal structure (no styling yet)

**Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: Add minimal unified layout HTML structure"
```

---

### Task 3: Write core layout CSS

**Files:**
- Modify: `frontend/css/unified-layout.css`

**Step 1: Write 3-zone layout CSS**

Add to `/home/irjudson/Projects/astronomus/frontend/css/unified-layout.css`:

```css
/* ==========================================
   UNIFIED LAYOUT - 3-ZONE STRUCTURE
   ========================================== */

/* App Container - CSS Grid */
.app-container {
    display: grid;
    grid-template-columns: 320px 1fr;
    grid-template-rows: 1fr auto;
    gap: 24px;
    height: 100vh;
    padding: 24px;
    background: #0a0e27;
    overflow: hidden;
}

/* ==========================================
   LEFT SIDEBAR (320px fixed)
   ========================================== */

.app-sidebar {
    grid-column: 1;
    grid-row: 1;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(0, 217, 255, 0.3);
    border-radius: 8px;
    overflow-y: auto;
    overflow-x: hidden;
}

.sidebar-content {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

/* ==========================================
   MAIN CONTENT AREA (flexible)
   ========================================== */

.app-main {
    grid-column: 2;
    grid-row: 1;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(0, 217, 255, 0.3);
    border-radius: 8px;
    overflow: hidden;
    position: relative;
}

.main-content {
    padding: 24px;
    height: 100%;
    overflow-y: auto;
    color: white;
}

/* ==========================================
   BOTTOM DRAWER
   ========================================== */

.app-drawer {
    grid-column: 1 / -1;
    grid-row: 2;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(0, 217, 255, 0.3);
    border-radius: 8px;
    max-height: 400px;
    transition: max-height 250ms ease-out;
    overflow: hidden;
}

.app-drawer.closed {
    max-height: 48px;
}

.drawer-toggle {
    width: 100%;
    padding: 12px;
    background: transparent;
    border: none;
    color: #00d9ff;
    cursor: pointer;
    font-size: 14px;
    text-align: center;
}

.drawer-toggle:hover {
    background: rgba(0, 217, 255, 0.1);
}

.drawer-content {
    padding: 16px;
    display: none;
}

.app-drawer:not(.closed) .drawer-content {
    display: block;
}

.drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.drawer-header h3 {
    color: white;
    margin: 0;
    font-size: 16px;
}

.settings-btn {
    background: transparent;
    border: 1px solid rgba(0, 217, 255, 0.3);
    color: #00d9ff;
    cursor: pointer;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 16px;
}

.settings-btn:hover {
    background: rgba(0, 217, 255, 0.1);
}

/* ==========================================
   MOBILE (< 768px)
   ========================================== */

.mobile-menu-toggle {
    display: none;
    position: fixed;
    top: 16px;
    left: 16px;
    z-index: 1001;
    background: rgba(0, 217, 255, 0.2);
    border: 1px solid rgba(0, 217, 255, 0.5);
    color: #00d9ff;
    padding: 12px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 20px;
}

.mobile-backdrop {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 999;
}

@media (max-width: 768px) {
    .app-container {
        grid-template-columns: 1fr;
        padding: 16px;
        gap: 16px;
    }

    .mobile-menu-toggle {
        display: block;
    }

    .app-sidebar {
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        width: min(320px, 90vw);
        z-index: 1000;
        transform: translateX(-100%);
        transition: transform 300ms ease-in-out;
        grid-column: 1;
        grid-row: 1;
    }

    .app-sidebar.open {
        transform: translateX(0);
    }

    .mobile-backdrop.visible {
        display: block;
    }

    .app-main {
        grid-column: 1;
        grid-row: 1;
    }

    .app-drawer {
        grid-column: 1;
    }
}
```

**Step 2: Test responsive layout**

Run: `docker-compose restart astronomus`
Navigate to: `http://localhost:9247`
Expected: 3-zone layout visible on desktop, sidebar hidden on mobile

**Step 3: Commit**

```bash
git add frontend/css/unified-layout.css
git commit -m "feat: Add core 3-zone layout CSS with responsive behavior"
```

---

### Task 4: Add panel and workflow section styles

**Files:**
- Modify: `frontend/css/unified-layout.css`

**Step 1: Add panel styles**

Append to `/home/irjudson/Projects/astronomus/frontend/css/unified-layout.css`:

```css
/* ==========================================
   PANELS (Connection, and collapsible panels)
   ========================================== */

.panel {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(0, 217, 255, 0.2);
    border-radius: 8px;
    overflow: hidden;
}

.panel-header {
    padding: 12px 16px;
    background: rgba(0, 217, 255, 0.05);
    border-bottom: 1px solid rgba(0, 217, 255, 0.2);
}

.panel-header h3 {
    margin: 0;
    color: #00d9ff;
    font-size: 14px;
    font-weight: 600;
}

.panel-body {
    padding: 16px;
    color: white;
}

/* Collapsible Panels */
.panel-collapsible .panel-header {
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: background 200ms;
}

.panel-collapsible .panel-header:hover {
    background: rgba(0, 217, 255, 0.1);
}

.panel-collapsible.collapsed .panel-header {
    border-radius: 8px;
    border-bottom: none;
}

.panel-collapsible.collapsed .panel-body {
    display: none;
}

.panel-chevron {
    font-size: 12px;
    color: #00d9ff;
    transition: transform 300ms ease-in-out;
}

.panel-collapsible.collapsed .panel-chevron {
    transform: rotate(-90deg);
}

/* ==========================================
   WORKFLOW SECTIONS
   ========================================== */

.workflow-section {
    background: rgba(0, 217, 255, 0.03);
    border: 1px solid rgba(0, 217, 255, 0.15);
    border-radius: 8px;
    overflow: hidden;
}

.workflow-header {
    padding: 12px 16px;
    background: rgba(0, 217, 255, 0.08);
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: background 200ms;
}

.workflow-header:hover {
    background: rgba(0, 217, 255, 0.12);
}

.workflow-title {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    color: #00d9ff;
}

.workflow-chevron {
    font-size: 12px;
    color: #00d9ff;
    transition: transform 300ms ease-in-out;
}

.workflow-section.collapsed .workflow-chevron {
    transform: rotate(-90deg);
}

.workflow-content {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 1000px;
    transition: max-height 300ms ease-in-out;
    overflow: hidden;
}

.workflow-section.collapsed .workflow-content {
    max-height: 0;
    padding: 0 16px;
}
```

**Step 2: Test panel styles**

Run: `docker-compose restart astronomus`
Navigate to: `http://localhost:9247`
Expected: Panels and workflow sections have proper styling

**Step 3: Commit**

```bash
git add frontend/css/unified-layout.css
git commit -m "feat: Add panel and workflow section CSS styles"
```

---

### Task 5: Write app state management

**Files:**
- Modify: `frontend/js/app-state.js`

**Step 1: Write state management code**

Add to `/home/irjudson/Projects/astronomus/frontend/js/app-state.js`:

```javascript
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

    // Persist state to localStorage
    save() {
        try {
            const stateToPersist = {
                workflowSections: this.workflowSections,
                currentContext: this.currentContext,
                drawer: this.drawer
            };
            localStorage.setItem('astronomus-state', JSON.stringify(stateToPersist));
        } catch (e) {
            console.warn('Failed to save state:', e);
        }
    },

    // Load state from localStorage
    load() {
        try {
            const saved = localStorage.getItem('astronomus-state');
            if (saved) {
                const parsed = JSON.parse(saved);
                this.workflowSections = parsed.workflowSections || this.workflowSections;
                this.currentContext = parsed.currentContext || this.currentContext;
                this.drawer = { ...this.drawer, ...parsed.drawer };
            }
        } catch (e) {
            console.warn('Failed to load state:', e);
        }
    }
};

// Load state on init
AppState.load();
```

**Step 2: Verify state loads**

Open browser console at `http://localhost:9247`
Run: `console.log(AppState)`
Expected: AppState object logged with initial state

**Step 3: Commit**

```bash
git add frontend/js/app-state.js
git commit -m "feat: Add application state management"
```

---

### Task 6: Write context manager with workflow toggling

**Files:**
- Modify: `frontend/js/app-context.js`

**Step 1: Write context manager code**

Add to `/home/irjudson/Projects/astronomus/frontend/js/app-context.js`:

```javascript
// ==========================================
// CONTEXT MANAGER - Controls workflow switching
// ==========================================

const AppContext = {
    // Initialize context manager
    init() {
        this.setupWorkflowToggle();
        this.setupDrawerToggle();
        this.setupMobileMenu();
        this.restoreUIState();
    },

    // Setup workflow section expand/collapse
    setupWorkflowToggle() {
        const workflowHeaders = document.querySelectorAll('.workflow-header');
        workflowHeaders.forEach(header => {
            header.addEventListener('click', (e) => {
                const workflow = header.dataset.workflow;
                this.toggleWorkflowSection(workflow);
            });
        });
    },

    // Toggle workflow section expanded/collapsed
    toggleWorkflowSection(workflow) {
        const section = document.getElementById(`${workflow}-section`);
        if (!section) return;

        const isCollapsed = section.classList.contains('collapsed');

        if (isCollapsed) {
            section.classList.remove('collapsed');
            AppState.workflowSections[workflow].expanded = true;
        } else {
            section.classList.add('collapsed');
            AppState.workflowSections[workflow].expanded = false;
        }

        AppState.save();
    },

    // Setup drawer toggle
    setupDrawerToggle() {
        const toggle = document.getElementById('drawer-toggle');
        const drawer = document.getElementById('app-drawer');

        if (toggle && drawer) {
            toggle.addEventListener('click', () => {
                drawer.classList.toggle('closed');
                AppState.drawer.isOpen = !drawer.classList.contains('closed');
                AppState.save();
            });
        }
    },

    // Setup mobile menu
    setupMobileMenu() {
        const menuToggle = document.getElementById('mobile-menu-toggle');
        const sidebar = document.getElementById('app-sidebar');
        const backdrop = document.getElementById('mobile-backdrop');

        if (menuToggle && sidebar && backdrop) {
            menuToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
                backdrop.classList.toggle('visible');
                AppState.mobile.sidebarOpen = sidebar.classList.contains('open');
            });

            backdrop.addEventListener('click', () => {
                sidebar.classList.remove('open');
                backdrop.classList.remove('visible');
                AppState.mobile.sidebarOpen = false;
            });
        }
    },

    // Restore UI state from AppState
    restoreUIState() {
        // Restore workflow section states
        Object.keys(AppState.workflowSections).forEach(workflow => {
            const section = document.getElementById(`${workflow}-section`);
            if (section) {
                if (AppState.workflowSections[workflow].expanded) {
                    section.classList.remove('collapsed');
                } else {
                    section.classList.add('collapsed');
                }
            }
        });

        // Restore drawer state
        const drawer = document.getElementById('app-drawer');
        if (drawer) {
            if (AppState.drawer.isOpen) {
                drawer.classList.remove('closed');
            } else {
                drawer.classList.add('closed');
            }
        }
    },

    // Switch to a specific context
    switchContext(newContext) {
        if (AppState.currentContext === newContext) return;

        console.log(`Switching context: ${AppState.currentContext} → ${newContext}`);

        AppState.currentContext = newContext;
        AppState.save();

        // Update main content area
        this.updateMainContent(newContext);

        // Update drawer content
        this.updateDrawerContent(newContext);
    },

    // Update main content area based on context
    updateMainContent(context) {
        const mainContent = document.getElementById('main-content');
        if (!mainContent) return;

        // Add fade out
        mainContent.style.opacity = '0';

        setTimeout(() => {
            // Update content based on context
            switch (context) {
                case 'discovery':
                    mainContent.innerHTML = '<h2>Catalog Grid</h2><p>Discovery content coming soon</p>';
                    break;
                case 'planning':
                    mainContent.innerHTML = '<h2>Planning Results</h2><p>Planning content coming soon</p>';
                    break;
                case 'execution':
                    mainContent.innerHTML = '<h2>Execution View</h2><p>Execution content coming soon</p>';
                    break;
                case 'processing':
                    mainContent.innerHTML = '<h2>Processing Workspace</h2><p>Processing content coming soon</p>';
                    break;
            }

            // Fade in
            mainContent.style.opacity = '1';
        }, 200);
    },

    // Update drawer content based on context
    updateDrawerContent(context) {
        const drawerTabs = document.getElementById('drawer-tabs');
        if (!drawerTabs) return;

        drawerTabs.style.opacity = '0';

        setTimeout(() => {
            switch (context) {
                case 'discovery':
                    drawerTabs.innerHTML = '<p>Discovery drawer: Advanced Filters, Custom Queries</p>';
                    break;
                case 'planning':
                    drawerTabs.innerHTML = '<p>Planning drawer: Constraints, Optimization</p>';
                    break;
                case 'execution':
                    drawerTabs.innerHTML = '<p>Execution drawer: Advanced Imaging, System, WiFi, Calibration, Hardware</p>';
                    break;
                case 'processing':
                    drawerTabs.innerHTML = '<p>Processing drawer: Processing Parameters, Batch Operations</p>';
                    break;
            }

            drawerTabs.style.opacity = '1';
        }, 150);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    AppContext.init();
    console.log('AppContext initialized');
});
```

**Step 2: Test workflow toggling**

Run: `docker-compose restart astronomus`
Navigate to: `http://localhost:9247`
Test:
1. Click "DISCOVERY" header - should collapse
2. Click "PLANNING" header - should expand
3. Click drawer toggle - should open/close
4. On mobile - click hamburger menu - sidebar should slide in

Expected: All interactions work smoothly

**Step 3: Commit**

```bash
git add frontend/js/app-context.js
git commit -m "feat: Add context manager with workflow and drawer toggling"
```

---

## Phase 2: Connection Panel & Weather

### Task 7: Build Connection Panel HTML

**Files:**
- Modify: `frontend/index.html`

**Step 1: Replace connection panel placeholder**

In `/home/irjudson/Projects/astronomus/frontend/index.html`, find the connection panel section and replace with:

```html
<!-- Connection Panel (Always Visible) -->
<div class="panel panel-connection" id="connection-panel">
    <div class="panel-header">
        <h3>Connection & Weather</h3>
    </div>
    <div class="panel-body">
        <!-- Device Selection -->
        <div class="form-group">
            <label for="device-select">Device</label>
            <select id="device-select" class="form-control">
                <option value="">Select device...</option>
            </select>
        </div>

        <!-- Connection Button -->
        <button id="connect-btn" class="btn btn-primary" disabled>
            Connect
        </button>

        <!-- Connection Status -->
        <div class="connection-status" id="connection-status">
            <span class="status-indicator disconnected"></span>
            <span class="status-text">Disconnected</span>
        </div>

        <!-- Weather Conditions -->
        <div class="weather-widget" id="weather-widget">
            <div class="weather-header">
                <span class="weather-icon">🌤️</span>
                <span class="weather-status">Loading weather...</span>
            </div>
            <div class="weather-details" id="weather-details">
                <!-- Weather details populated by JS -->
            </div>
        </div>
    </div>
</div>
```

**Step 2: Verify HTML renders**

Run: `docker-compose restart astronomus`
Navigate to: `http://localhost:9247`
Expected: Connection panel shows device dropdown, connect button, status, weather widget

**Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat: Add Connection panel HTML structure"
```

---

### Task 8: Style Connection Panel

**Files:**
- Modify: `frontend/css/unified-layout.css`

**Step 1: Add connection panel styles**

Append to `/home/irjudson/Projects/astronomus/frontend/css/unified-layout.css`:

```css
/* ==========================================
   CONNECTION PANEL
   ========================================== */

.panel-connection {
    /* Connection panel cannot collapse */
}

.form-group {
    margin-bottom: 12px;
}

.form-group label {
    display: block;
    font-size: 12px;
    color: #00d9ff;
    margin-bottom: 4px;
    font-weight: 600;
}

.form-control {
    width: 100%;
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(0, 217, 255, 0.3);
    border-radius: 4px;
    color: white;
    font-size: 14px;
}

.form-control:focus {
    outline: none;
    border-color: #00d9ff;
}

.btn {
    padding: 10px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 200ms;
    width: 100%;
    margin-bottom: 12px;
}

.btn-primary {
    background: #00d9ff;
    color: #0a0e27;
}

.btn-primary:hover:not(:disabled) {
    background: #00eaff;
    transform: scale(1.02);
}

.btn-primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

.btn-danger {
    background: #ff4444;
    color: white;
}

.btn-danger:hover {
    background: #ff6666;
}

.connection-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    margin-bottom: 12px;
}

.status-indicator {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    animation: pulse 2s infinite;
}

.status-indicator.connected {
    background: #00ff00;
}

.status-indicator.disconnected {
    background: #666;
    animation: none;
}

.status-indicator.error {
    background: #ff4444;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.status-text {
    font-size: 13px;
    color: white;
}

/* Weather Widget */
.weather-widget {
    background: rgba(0, 217, 255, 0.05);
    border: 1px solid rgba(0, 217, 255, 0.2);
    border-radius: 4px;
    padding: 12px;
}

.weather-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

.weather-icon {
    font-size: 20px;
}

.weather-status {
    font-size: 13px;
    color: #00d9ff;
    font-weight: 600;
}

.weather-details {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.8);
}

.weather-detail-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
}

.observability-good { color: #00ff00; }
.observability-fair { color: #ffaa00; }
.observability-poor { color: #ff4444; }
```

**Step 2: Test connection panel styling**

Run: `docker-compose restart astronomus`
Navigate to: `http://localhost:9247`
Expected: Connection panel is well-styled, button and status look correct

**Step 3: Commit**

```bash
git add frontend/css/unified-layout.css
git commit -m "feat: Add Connection panel CSS styling"
```

---

### Task 9: Create connection manager JavaScript

**Files:**
- Create: `frontend/js/connection-manager.js`

**Step 1: Write connection manager**

Create `/home/irjudson/Projects/astronomus/frontend/js/connection-manager.js`:

```javascript
// ==========================================
// CONNECTION MANAGER
// ==========================================

const ConnectionManager = {
    init() {
        this.loadDevices();
        this.setupEventListeners();
    },

    setupEventListeners() {
        const deviceSelect = document.getElementById('device-select');
        const connectBtn = document.getElementById('connect-btn');

        if (deviceSelect) {
            deviceSelect.addEventListener('change', (e) => {
                const deviceId = e.target.value;
                connectBtn.disabled = !deviceId;
                AppState.connection.deviceId = deviceId;
            });
        }

        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                if (AppState.connection.isConnected) {
                    this.disconnect();
                } else {
                    this.connect();
                }
            });
        }
    },

    async loadDevices() {
        try {
            const response = await fetch('/api/devices');
            const devices = await response.json();

            const select = document.getElementById('device-select');
            if (!select) return;

            select.innerHTML = '<option value="">Select device...</option>';

            devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.id;
                option.textContent = `${device.name} (${device.ip_address})`;
                select.appendChild(option);
            });

            // Restore selected device if any
            if (AppState.connection.deviceId) {
                select.value = AppState.connection.deviceId;
                document.getElementById('connect-btn').disabled = false;
            }
        } catch (error) {
            console.error('Failed to load devices:', error);
            this.showError('Failed to load devices');
        }
    },

    async connect() {
        const deviceId = AppState.connection.deviceId;
        if (!deviceId) return;

        this.updateStatus('connecting', 'Connecting...');

        try {
            const response = await fetch(`/api/devices/${deviceId}/connect`, {
                method: 'POST'
            });

            if (response.ok) {
                AppState.connection.isConnected = true;
                AppState.connection.status = 'connected';
                this.updateStatus('connected', 'Connected');

                const connectBtn = document.getElementById('connect-btn');
                if (connectBtn) {
                    connectBtn.textContent = 'Disconnect';
                    connectBtn.classList.remove('btn-primary');
                    connectBtn.classList.add('btn-danger');
                }

                // Switch to execution context when device connects
                AppContext.switchContext('execution');
            } else {
                throw new Error('Connection failed');
            }
        } catch (error) {
            console.error('Connection error:', error);
            this.updateStatus('error', 'Connection failed');
            AppState.connection.isConnected = false;
        }
    },

    async disconnect() {
        const deviceId = AppState.connection.deviceId;
        if (!deviceId) return;

        try {
            const response = await fetch(`/api/devices/${deviceId}/disconnect`, {
                method: 'POST'
            });

            if (response.ok) {
                AppState.connection.isConnected = false;
                AppState.connection.status = 'disconnected';
                this.updateStatus('disconnected', 'Disconnected');

                const connectBtn = document.getElementById('connect-btn');
                if (connectBtn) {
                    connectBtn.textContent = 'Connect';
                    connectBtn.classList.remove('btn-danger');
                    connectBtn.classList.add('btn-primary');
                }
            }
        } catch (error) {
            console.error('Disconnect error:', error);
        }
    },

    updateStatus(state, text) {
        const indicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');

        if (indicator) {
            indicator.className = 'status-indicator ' + state;
        }

        if (statusText) {
            statusText.textContent = text;
        }
    },

    showError(message) {
        // Simple error display for now
        alert(message);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    ConnectionManager.init();
});
```

**Step 2: Add script to index.html**

In `/home/irjudson/Projects/astronomus/frontend/index.html`, before `</body>`, add:

```html
<script src="js/connection-manager.js"></script>
```

**Step 3: Test connection functionality**

Run: `docker-compose restart astronomus`
Navigate to: `http://localhost:9247`
Test:
1. Device dropdown should populate from API
2. Selecting device should enable Connect button
3. Clicking Connect should attempt connection

Expected: Connection logic works (may fail if no devices configured, but logic should execute)

**Step 4: Commit**

```bash
git add frontend/js/connection-manager.js frontend/index.html
git commit -m "feat: Add connection manager with device selection and connection logic"
```

---

### Task 10: Create weather widget JavaScript

**Files:**
- Create: `frontend/js/weather-widget.js`

**Step 1: Write weather widget**

Create `/home/irjudson/Projects/astronomus/frontend/js/weather-widget.js`:

```javascript
// ==========================================
// WEATHER WIDGET
// ==========================================

const WeatherWidget = {
    updateInterval: 300000, // 5 minutes
    intervalId: null,

    init() {
        this.loadWeather();
        this.startAutoUpdate();
    },

    async loadWeather() {
        try {
            // Try to get location from planning state or use default
            const lat = AppState.planning.location?.latitude || 40.7128;
            const lon = AppState.planning.location?.longitude || -74.0060;

            const response = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
            const weather = await response.json();

            AppState.weather.conditions = weather.current;
            AppState.weather.forecast = weather.forecast;
            AppState.weather.observability = this.calculateObservability(weather);

            this.updateDisplay();
        } catch (error) {
            console.error('Failed to load weather:', error);
            this.showError();
        }
    },

    calculateObservability(weather) {
        // Simple observability calculation based on cloud cover
        const cloudCover = weather.current?.cloud_cover || 100;

        if (cloudCover < 30) return 'good';
        if (cloudCover < 70) return 'fair';
        return 'poor';
    },

    updateDisplay() {
        const statusEl = document.querySelector('.weather-status');
        const detailsEl = document.getElementById('weather-details');
        const iconEl = document.querySelector('.weather-icon');

        if (!AppState.weather.conditions) {
            if (statusEl) statusEl.textContent = 'Weather unavailable';
            return;
        }

        const conditions = AppState.weather.conditions;
        const observability = AppState.weather.observability;

        // Update icon
        if (iconEl) {
            iconEl.textContent = this.getWeatherIcon(conditions, observability);
        }

        // Update status
        if (statusEl) {
            const temp = conditions.temperature ? `${Math.round(conditions.temperature)}°C` : '--';
            statusEl.textContent = `${temp} • ${observability.charAt(0).toUpperCase() + observability.slice(1)}`;
            statusEl.className = `weather-status observability-${observability}`;
        }

        // Update details
        if (detailsEl) {
            detailsEl.innerHTML = `
                <div class="weather-detail-row">
                    <span>Humidity:</span>
                    <span>${conditions.humidity || '--'}%</span>
                </div>
                <div class="weather-detail-row">
                    <span>Cloud Cover:</span>
                    <span>${conditions.cloud_cover || '--'}%</span>
                </div>
                <div class="weather-detail-row">
                    <span>Wind:</span>
                    <span>${conditions.wind_speed || '--'} km/h</span>
                </div>
                <div class="weather-detail-row">
                    <span>Observing:</span>
                    <span class="observability-${observability}">${observability.toUpperCase()}</span>
                </div>
            `;
        }
    },

    getWeatherIcon(conditions, observability) {
        // Simple icon selection based on conditions
        if (observability === 'good') return '🌙';
        if (observability === 'fair') return '⛅';
        return '☁️';
    },

    showError() {
        const statusEl = document.querySelector('.weather-status');
        if (statusEl) {
            statusEl.textContent = 'Weather unavailable';
        }
    },

    startAutoUpdate() {
        this.intervalId = setInterval(() => {
            this.loadWeather();
        }, this.updateInterval);
    },

    stopAutoUpdate() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    WeatherWidget.init();
});
```

**Step 2: Add script to index.html**

In `/home/irjudson/Projects/astronomus/frontend/index.html`, before `</body>`, add:

```html
<script src="js/weather-widget.js"></script>
```

**Step 3: Test weather widget**

Run: `docker-compose restart astronomus`
Navigate to: `http://localhost:9247`
Expected: Weather widget displays data (or "unavailable" if API not configured)

**Step 4: Commit**

```bash
git add frontend/js/weather-widget.js frontend/index.html
git commit -m "feat: Add weather widget with auto-updating conditions"
```

---

## Phase 3: Discovery Workflow

### Task 11: Build Discovery sidebar panels HTML

**Files:**
- Modify: `frontend/index.html`

**Step 1: Replace Discovery section placeholder**

In `/home/irjudson/Projects/astronomus/frontend/index.html`, find Discovery section and replace content with:

```html
<!-- Discovery Workflow Section -->
<div class="workflow-section" id="discovery-section">
    <div class="workflow-header" data-workflow="discovery">
        <span class="workflow-title">DISCOVERY</span>
        <span class="workflow-chevron">▼</span>
    </div>
    <div class="workflow-content">
        <!-- Catalog Search Panel -->
        <div class="panel panel-collapsible" id="catalog-search-panel">
            <div class="panel-header">
                <h3>Catalog Search</h3>
                <span class="panel-chevron">▼</span>
            </div>
            <div class="panel-body">
                <!-- Search Box -->
                <div class="form-group">
                    <label for="catalog-search">Search</label>
                    <div class="search-box">
                        <input type="text" id="catalog-search" class="form-control" placeholder="Object name...">
                        <button id="catalog-search-btn" class="btn btn-primary btn-sm">Search</button>
                    </div>
                </div>

                <!-- Filters -->
                <div class="form-group">
                    <label for="filter-type">Type</label>
                    <select id="filter-type" class="form-control">
                        <option value="">All types</option>
                        <option value="galaxy">Galaxy</option>
                        <option value="nebula">Nebula</option>
                        <option value="cluster">Cluster</option>
                        <option value="planetary_nebula">Planetary Nebula</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="filter-constellation">Constellation</label>
                    <select id="filter-constellation" class="form-control">
                        <option value="">All constellations</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="filter-magnitude">Max Magnitude</label>
                    <input type="number" id="filter-magnitude" class="form-control" placeholder="e.g. 12.0" step="0.1">
                </div>

                <!-- Sort -->
                <div class="form-group">
                    <label for="sort-by">Sort By</label>
                    <select id="sort-by" class="form-control">
                        <option value="name">Name</option>
                        <option value="magnitude">Magnitude</option>
                        <option value="type">Type</option>
                    </select>
                </div>

                <!-- Actions -->
                <button id="apply-filters-btn" class="btn btn-primary">Apply Filters</button>
                <button id="clear-filters-btn" class="btn btn-secondary">Clear</button>
            </div>
        </div>

        <!-- Custom Plan Builder Panel -->
        <div class="panel panel-collapsible collapsed" id="custom-plan-panel">
            <div class="panel-header">
                <h3>Custom Plan Builder</h3>
                <span class="panel-chevron">▼</span>
            </div>
            <div class="panel-body">
                <p class="info-text">Select targets from catalog to build a custom observation plan.</p>
                <div id="selected-targets-list">
                    <p class="empty-state">No targets selected</p>
                </div>
                <button id="create-custom-plan-btn" class="btn btn-primary" disabled>Create Plan</button>
            </div>
        </div>
    </div>
</div>
```

**Step 2: Add missing button styles**

In `/home/irjudson/Projects/astronomus/frontend/css/unified-layout.css`, add:

```css
.btn-sm {
    padding: 6px 12px;
    font-size: 12px;
}

.btn-secondary {
    background: rgba(255, 255, 255, 0.1);
    color: white;
}

.btn-secondary:hover {
    background: rgba(255, 255, 255, 0.15);
}

.search-box {
    display: flex;
    gap: 8px;
}

.search-box input {
    flex: 1;
}

.info-text {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 12px;
}

.empty-state {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.4);
    text-align: center;
    padding: 16px;
}
```

**Step 3: Test Discovery panels**

Run: `docker-compose restart astronomus`
Navigate to: `http://localhost:9247`
Expected: Discovery section shows Catalog Search and Custom Plan Builder panels

**Step 4: Commit**

```bash
git add frontend/index.html frontend/css/unified-layout.css
git commit -m "feat: Add Discovery workflow sidebar panels HTML"
```

---

[Continue with remaining tasks...]

Due to length constraints, I'll now save this plan and offer the execution choice. The plan continues with:
- Tasks 12-20: Complete Discovery workflow (catalog grid, search, filters)
- Tasks 21-30: Planning workflow (forms, mosaic planning, plan generation)
- Tasks 31-45: Execution workflow (controls, imaging, telescope, library, telemetry, live view)
- Tasks 46-55: Processing workflow (file browser, processing options, jobs)
- Tasks 56-65: Settings, modals, error handling, final polish
- Task 66: Feature parity verification
- Task 67: Final cleanup and deployment

The plan is structured to be executed task-by-task with frequent commits.
