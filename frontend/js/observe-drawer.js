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
function showDrawerTab(tabName, evt) {
  if (!evt || !evt.target) {
    console.error('Event object required for showDrawerTab');
    return;
  }

  // Update tab buttons
  document.querySelectorAll('#bottom-drawer .tab').forEach(tab => {
    tab.classList.remove('active');
  });
  evt.target.classList.add('active');

  // Update tab content
  document.querySelectorAll('.drawer-tab-content').forEach(content => {
    content.classList.add('hidden');
  });
  document.getElementById(`${tabName}-drawer-content`).classList.remove('hidden');

  // Update state
  updateState('ui', { drawerActiveTab: tabName });

  // Update last tab text
  document.getElementById('drawer-last-tab').textContent =
    `Last: ${evt.target.textContent.trim()}`;
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
