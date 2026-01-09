const { test, expect } = require('@playwright/test');

test.describe('Full Connection Flow', () => {
    test('should trigger TelescopeCapabilities when connection event fires', async ({ page }) => {
        const consoleLogs = [];

        page.on('console', msg => {
            const text = msg.text();
            consoleLogs.push(text);
        });

        await page.goto('http://localhost:8001/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);

        // Click execution
        const executionTitle = await page.locator('.workflow-title:has-text("EXECUTION")');
        await executionTitle.click();
        await page.waitForTimeout(500);

        console.log('\n=== Dispatching connection event ===');

        // Dispatch connection event (simulating what ConnectionManager does)
        await page.evaluate(() => {
            document.dispatchEvent(new Event('telescope-connected'));
        });

        // Wait for async fetch to potentially happen
        await page.waitForTimeout(1000);

        // Check if TelescopeCapabilities tried to fetch
        const relevantLogs = consoleLogs.filter(log =>
            log.includes('Telescope capabilities') ||
            log.includes('Failed to load telescope capabilities') ||
            log.includes('OperatorDashboard: Capabilities')
        );

        console.log('\n=== Relevant Console Logs ===');
        relevantLogs.forEach(log => console.log(log));

        // We expect to see EITHER:
        // 1. "Telescope capabilities loaded" (if API returns data)
        // 2. "Failed to load telescope capabilities" (if API 404s but fetch was attempted)
        const fetchWasAttempted = relevantLogs.some(log =>
            log.includes('Telescope capabilities') || log.includes('Failed to load telescope capabilities')
        );

        console.log(`\nFetch was attempted: ${fetchWasAttempted}`);
        expect(fetchWasAttempted).toBe(true);
    });
});
