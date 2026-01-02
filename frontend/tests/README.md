# Observe View Frontend Tests

This directory contains browser-based integration tests for the Observe View redesign.

## Test Files

- **index.html** - Test runner dashboard with links to all test suites
- **observe-state.test.html** - Tests for state management (8 tests)
- **observe-errors.test.html** - Tests for error handling and security (10 tests)
- **observe-drawer.test.html** - Tests for drawer component (11 tests)

## Running Tests

### Option 1: Test Runner (Recommended)

1. Start the application server
2. Navigate to `http://localhost:8000/tests/` (or appropriate URL)
3. Click "Run All Tests" or individual test suite links

### Option 2: Individual Tests

Open any `.test.html` file directly in a browser:

```bash
# From the frontend directory
open tests/observe-state.test.html
open tests/observe-errors.test.html
open tests/observe-drawer.test.html
```

### Option 3: Via Docker

If running in Docker, the tests are available at:
```
http://localhost:8000/tests/
```

## Test Coverage

### State Management (observe-state.js)
- ✓ Initial state structure validation
- ✓ Shallow state updates
- ✓ Deep merge for nested objects
- ✓ State change listeners
- ✓ Listener data propagation
- ✓ Nested object preservation

### Error Handling (observe-errors.js)
- ✓ XSS prevention in error messages
- ✓ HTML escaping utilities
- ✓ Toast notification creation
- ✓ Toast message display
- ✓ Error banner creation
- ✓ Error banner XSS prevention (title)
- ✓ Error banner XSS prevention (message)
- ✓ Action button creation and execution
- ✓ Sleep utility functionality

### Drawer Component (observe-drawer.js)
- ✓ Drawer open/close toggling
- ✓ State synchronization
- ✓ Toggle text updates
- ✓ Tab switching with event parameter
- ✓ Tab content visibility
- ✓ Active tab state tracking
- ✓ Last tab text updates
- ✓ Active class management
- ✓ Event parameter validation
- ✓ Keyboard shortcut registration

## Test Format

Tests use a simple assertion framework:
- Green (✓) = Passing test
- Red (✗) = Failing test
- Summary shows pass/fail counts and success rate

## Security Tests

Special attention is given to XSS prevention:
- `escapeHtml()` utility validation
- Error banner HTML injection prevention
- Toast notification content sanitization
- Action button code execution safety

## Manual Testing Checklist

While these automated tests verify core functionality, the following should be manually tested in the full application:

- [ ] Telescope connection flow
- [ ] API communication
- [ ] Library filtering and sorting
- [ ] Telemetry display updates
- [ ] Responsive design on mobile
- [ ] Keyboard shortcuts (Ctrl+D for drawer)
- [ ] Error retry logic
- [ ] State persistence (localStorage)

## Adding New Tests

To add a new test suite:

1. Create a new `.test.html` file following the existing pattern
2. Include the module being tested
3. Write assertions using the `assert()` function
4. Add a link to the test in `index.html`

Example:
```html
<script src="../js/your-module.js"></script>
<script>
    function assert(condition, testName) {
        // ... assertion logic
    }

    function runTests() {
        assert(yourFunction !== undefined, 'Function exists');
        // More tests...
    }

    window.addEventListener('load', runTests);
</script>
```

## CI/CD Integration

These tests can be automated using headless browser testing:

```bash
# Example with Playwright or Puppeteer
npx playwright test tests/*.test.html
```

## Known Limitations

- Tests run in browser environment only
- No mocking framework (uses real DOM)
- API tests require running backend
- Some tests verify behavior, not implementation details
