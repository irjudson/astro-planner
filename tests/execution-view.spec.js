const { test, expect } = require('@playwright/test');

test.describe('Execution View', () => {
    test.beforeEach(async ({ page }) => {
        // Start on the discovery page
        await page.goto('http://localhost:8001/');

        // Wait for the page to load
        await page.waitForLoadState('networkidle');
    });

    test('should show execution view when clicking EXECUTION workflow title', async ({ page }) => {
        // Wait for app to initialize
        await page.waitForTimeout(1000);

        // Log initial state
        const initialContext = await page.evaluate(() => window.AppState.currentContext);
        console.log('Initial context:', initialContext);

        // Check if execution view is initially hidden
        const executionViewBefore = await page.locator('#execution-view');
        const isHiddenBefore = await executionViewBefore.evaluate(el => {
            const style = window.getComputedStyle(el);
            return style.display === 'none';
        });
        console.log('Execution view hidden before click:', isHiddenBefore);
        expect(isHiddenBefore).toBe(true);

        // Find and click the EXECUTION workflow title
        const executionTitle = await page.locator('.workflow-title:has-text("EXECUTION")');
        await expect(executionTitle).toBeVisible();

        console.log('Clicking EXECUTION title...');
        await executionTitle.click();

        // Wait for context switch animation
        await page.waitForTimeout(500);

        // Check if context switched
        const newContext = await page.evaluate(() => window.AppState.currentContext);
        console.log('New context:', newContext);
        expect(newContext).toBe('execution');

        // Check if execution view is now visible
        const executionViewAfter = await page.locator('#execution-view');
        const isVisibleAfter = await executionViewAfter.evaluate(el => {
            const style = window.getComputedStyle(el);
            return style.display !== 'none';
        });
        console.log('Execution view visible after click:', isVisibleAfter);
        expect(isVisibleAfter).toBe(true);

        // Verify operator dashboard elements are present
        await expect(page.locator('.operator-dashboard-grid')).toBeVisible();
        await expect(page.locator('#operator-connection-panel')).toBeVisible();
        await expect(page.locator('#operator-telemetry-panel')).toBeVisible();

        console.log('✓ Execution view successfully displayed');
    });

    test('should initialize operator dashboard scripts', async ({ page }) => {
        // Check if operator dashboard is loaded
        const operatorDashboard = await page.evaluate(() => window.OperatorDashboard);
        expect(operatorDashboard).toBeDefined();
        console.log('OperatorDashboard loaded:', !!operatorDashboard);

        // Check if operator panels is loaded
        const operatorPanels = await page.evaluate(() => window.OperatorPanels);
        expect(operatorPanels).toBeDefined();
        console.log('OperatorPanels loaded:', !!operatorPanels);
    });

    test('should check for JavaScript errors in console', async ({ page }) => {
        const consoleErrors = [];

        page.on('console', msg => {
            if (msg.type() === 'error') {
                consoleErrors.push(msg.text());
            }
        });

        // Navigate and wait
        await page.goto('http://localhost:8001/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000);

        // Click execution
        const executionTitle = await page.locator('.workflow-title:has-text("EXECUTION")');
        await executionTitle.click();
        await page.waitForTimeout(1000);

        // Check for errors
        console.log('Console errors:', consoleErrors);
        expect(consoleErrors).toHaveLength(0);
    });
});
