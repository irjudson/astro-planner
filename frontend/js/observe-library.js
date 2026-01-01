/**
 * Observe View Library Tab
 *
 * Manages the capture library display with search, filter, and sort.
 */

// API base URL
const API_BASE = '';

/**
 * Load capture library from backend
 */
async function loadCaptureLibrary() {
  updateState('library', { loading: true });

  try {
    const response = await fetch(`${API_BASE}/api/captures`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const targets = data.captures || [];

    updateState('library', {
      targets: targets,
      filteredTargets: targets,
      loading: false
    });

    applyLibraryFilters();
  } catch (error) {
    console.error('Failed to load capture library:', error);
    updateState('library', {
      targets: [],
      filteredTargets: [],
      loading: false
    });

    // Show error in grid
    const grid = document.getElementById('library-grid');
    if (grid) {
      grid.innerHTML = '<p class="text-secondary">Failed to load capture history</p>';
    }
  }
}

/**
 * Apply search, filter, and sort to library
 */
function applyLibraryFilters() {
  const { targets, filters } = observeState.library;
  let filtered = [...targets];

  // Apply search
  if (filters.search) {
    const searchLower = filters.search.toLowerCase();
    filtered = filtered.filter(target => {
      const name = target.catalog_id?.toLowerCase() || '';
      const common = target.common_name?.toLowerCase() || '';
      return name.includes(searchLower) || common.includes(searchLower);
    });
  }

  // Apply status filter
  if (filters.status !== 'all') {
    filtered = filtered.filter(target => target.status === filters.status);
  }

  // Apply sort
  switch (filters.sortBy) {
    case 'recent':
      filtered.sort((a, b) => new Date(b.last_updated) - new Date(a.last_updated));
      break;
    case 'name':
      filtered.sort((a, b) => {
        const nameA = a.catalog_id || '';
        const nameB = b.catalog_id || '';
        return nameA.localeCompare(nameB);
      });
      break;
    case 'exposure':
      filtered.sort((a, b) => (b.total_exposure_seconds || 0) - (a.total_exposure_seconds || 0));
      break;
    case 'quality':
      filtered.sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
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
  if (!grid) return;

  const { filteredTargets, loading } = observeState.library;

  if (loading) {
    grid.innerHTML = '<p class="text-secondary">Loading...</p>';
    return;
  }

  if (filteredTargets.length === 0) {
    grid.innerHTML = '<p class="text-secondary">No targets found</p>';
    return;
  }

  // Render target cards
  grid.innerHTML = filteredTargets.map(target => `
    <div class="panel target-card" onclick="viewTargetDetails('${target.catalog_id}')">
      <h4>${target.catalog_id}</h4>
      ${target.common_name ? `<p class="text-sm text-secondary mb-sm">${target.common_name}</p>` : ''}
      <div class="mb-sm">
        <span class="status-badge status-${target.status}">
          ${getStatusIcon(target.status)} ${formatStatus(target.status)}
        </span>
      </div>
      <p class="text-sm text-secondary">
        ${target.frames_completed || 0} frames &bull; ${formatExposureTime(target.total_exposure_seconds || 0)}
      </p>
      ${target.quality_score ? `<p class="text-sm text-secondary">Quality: ${Math.round(target.quality_score)}/100</p>` : ''}
      <p class="text-xs text-tertiary">${formatDate(target.last_updated)}</p>
    </div>
  `).join('');
}

/**
 * Get status icon emoji
 * @param {string} status - Status value
 * @returns {string} Emoji
 */
function getStatusIcon(status) {
  switch (status) {
    case 'complete':
      return '✓';
    case 'needs_more':
      return '⚠';
    case 'new':
      return '○';
    default:
      return '';
  }
}

/**
 * Format status text
 * @param {string} status - Status value
 * @returns {string} Formatted text
 */
function formatStatus(status) {
  switch (status) {
    case 'complete':
      return 'Complete';
    case 'needs_more':
      return 'Needs More';
    case 'new':
      return 'New';
    default:
      return status;
  }
}

/**
 * Format exposure time in seconds to "Xh Ym"
 * @param {number} seconds - Total seconds
 * @returns {string} Formatted time
 */
function formatExposureTime(seconds) {
  if (!seconds) return '0m';

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else {
    return `${minutes}m`;
  }
}

/**
 * Format date string to human-readable
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateStr) {
  if (!dateStr) return 'Unknown';

  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return 'Today';
  } else if (diffDays === 1) {
    return 'Yesterday';
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  } else {
    return date.toLocaleDateString();
  }
}

/**
 * View target details (placeholder)
 * @param {string} catalogId - Target catalog ID
 */
function viewTargetDetails(catalogId) {
  const target = observeState.library.targets.find(t => t.catalog_id === catalogId);
  if (!target) return;

  // TODO: Show modal with full details
  alert(`Target: ${target.catalog_id}\n` +
        `Status: ${formatStatus(target.status)}\n` +
        `Frames: ${target.frames_completed || 0}\n` +
        `Exposure: ${formatExposureTime(target.total_exposure_seconds || 0)}\n` +
        `Quality: ${target.quality_score ? Math.round(target.quality_score) : 'N/A'}`);
}

/**
 * Handle file transfer from Seestar
 */
async function handleTransferFiles() {
  if (observeState.library.transferStatus.inProgress) {
    alert('Transfer already in progress');
    return;
  }

  if (!confirm('Transfer all new files from Seestar to local storage?')) {
    return;
  }

  updateState('library', {
    transferStatus: {
      inProgress: true,
      currentFile: null,
      filesCompleted: 0,
      filesTotal: 0,
      lastSyncTime: null
    }
  });

  try {
    const response = await fetch(`${API_BASE}/api/captures/transfer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    updateState('library', {
      transferStatus: {
        inProgress: false,
        currentFile: null,
        filesCompleted: result.files_transferred || 0,
        filesTotal: result.files_transferred || 0,
        lastSyncTime: new Date().toISOString()
      }
    });

    alert(`Transfer complete: ${result.files_transferred || 0} files transferred`);

    // Reload library
    loadCaptureLibrary();
  } catch (error) {
    console.error('Transfer failed:', error);
    updateState('library', {
      transferStatus: {
        inProgress: false,
        currentFile: null,
        filesCompleted: 0,
        filesTotal: 0,
        lastSyncTime: null
      }
    });
    alert('Transfer failed: ' + error.message);
  }
}

/**
 * Initialize library event listeners
 */
document.addEventListener('DOMContentLoaded', () => {
  // Search input
  const searchInput = document.getElementById('library-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      updateState('library', {
        filters: {
          ...observeState.library.filters,
          search: e.target.value
        }
      });
      applyLibraryFilters();
    });
  }

  // Filter dropdown
  const filterSelect = document.getElementById('library-filter');
  if (filterSelect) {
    filterSelect.addEventListener('change', (e) => {
      updateState('library', {
        filters: {
          ...observeState.library.filters,
          status: e.target.value
        }
      });
      applyLibraryFilters();
    });
  }

  // Sort dropdown
  const sortSelect = document.getElementById('library-sort');
  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      updateState('library', {
        filters: {
          ...observeState.library.filters,
          sortBy: e.target.value
        }
      });
      applyLibraryFilters();
    });
  }
});
