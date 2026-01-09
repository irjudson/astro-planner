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
 * @param {Event} event - Click event object
 */
function showMainTab(tabName, event) {
  // Update tab buttons
  document.querySelectorAll('.tab-container .tab').forEach(tab => {
    tab.classList.remove('active');
  });

  // Add active to clicked tab with fallback
  if (event && event.target) {
    event.target.classList.add('active');
  }

  // Update tab content
  document.querySelectorAll('.tab-content-main').forEach(content => {
    content.classList.add('hidden');
  });

  const tabContent = document.getElementById(`${tabName}-content`);
  if (tabContent) {
    tabContent.classList.remove('hidden');
  } else {
    console.error(`Tab content not found: ${tabName}-content`);
  }

  // Update state
  updateState('ui', { activeMainTab: tabName });

  // Load tab-specific data (with defensive checks)
  switch (tabName) {
    case 'library':
      if (typeof loadCaptureLibrary === 'function') {
        loadCaptureLibrary();
      }
      break;
    case 'telemetry':
      if (typeof updateTelemetryDisplay === 'function') {
        updateTelemetryDisplay();
      }
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

  // Early return if essential elements don't exist yet
  if (!statusIndicator || !statusText || !connectBtn) {
    return;  // Silently skip - elements will be added in later tasks
  }

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
      if (firmware && firmwareDiv && firmwareText) {
        firmwareText.textContent = firmware;
        firmwareDiv.classList.remove('hidden');
      }

      // Enable execution controls (with null checks)
      const parkBtn = document.getElementById('park-btn');
      if (parkBtn) parkBtn.disabled = false;
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

      if (firmwareDiv) {
        firmwareDiv.classList.add('hidden');
      }

      // Disable execution controls (with null checks)
      const executeBtn = document.getElementById('execute-btn');
      const parkBtn2 = document.getElementById('park-btn');
      if (executeBtn) executeBtn.disabled = true;
      if (parkBtn2) parkBtn2.disabled = true;
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
