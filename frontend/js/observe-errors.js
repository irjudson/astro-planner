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
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Show error banner
 * @param {object} options - Banner options
 */
function showErrorBanner(options) {
  const { title, message, code, actions = [] } = options;

  const banner = document.createElement('div');
  banner.className = 'error-banner';

  // Create content div
  const contentDiv = document.createElement('div');

  const titleStrong = document.createElement('strong');
  titleStrong.textContent = title;
  contentDiv.appendChild(titleStrong);

  const messageDiv = document.createElement('div');
  messageDiv.className = 'text-sm';
  messageDiv.textContent = message;
  contentDiv.appendChild(messageDiv);

  if (code) {
    const codeDiv = document.createElement('div');
    codeDiv.className = 'text-xs';
    codeDiv.textContent = `Code: ${code}`;
    contentDiv.appendChild(codeDiv);
  }

  banner.appendChild(contentDiv);

  // Create actions div
  const actionsDiv = document.createElement('div');
  actions.forEach(action => {
    const button = document.createElement('button');
    button.textContent = action.label;
    button.onclick = new Function(action.action);
    actionsDiv.appendChild(button);
  });
  banner.appendChild(actionsDiv);

  const main = document.querySelector('.observe-main');
  if (main) {
    main.insertBefore(banner, main.firstChild);
  }
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
