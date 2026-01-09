const { test, expect } = require('@playwright/test');

test.describe('Operator Dashboard Panel Visibility', () => {
    test('should show all operator panels', async ({ page }) => {
        await page.goto('http://localhost:8001/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);

        // Click execution to show operator dashboard
        const executionTitle = await page.locator('.workflow-title:has-text("EXECUTION")');
        await executionTitle.click();
        await page.waitForTimeout(500);

        // Check all panels
        const panels = [
            { id: '#operator-connection-panel', name: 'Device Status' },
            { id: '#operator-telescope-panel', name: 'Telescope Control', hasCapability: true },
            { id: '#operator-focus-panel', name: 'Focus Control', hasCapability: true },
            { id: '#operator-imaging-panel', name: 'Imaging Settings', hasCapability: true },
            { id: '#operator-hardware-panel', name: 'Hardware Controls', hasCapability: true },
            { id: '#operator-execution-panel', name: 'Plan Execution' },
            { id: '#operator-telemetry-panel', name: 'Live Telemetry' },
            { id: '#operator-liveview-panel', name: 'Live Preview' }
        ];

        console.log('\n=== Panel Visibility Report ===');

        for (const panel of panels) {
            const element = await page.locator(panel.id);
            const exists = await element.count() > 0;

            if (exists) {
                const isVisible = await element.evaluate(el => {
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none';
                });

                const dataSupported = await element.getAttribute('data-supported');
                const hasCapability = await element.getAttribute('data-capability');

                console.log(`${panel.name} (${panel.id}):`);
                console.log(`  - Exists: ${exists}`);
                console.log(`  - Visible: ${isVisible}`);
                if (hasCapability) {
                    console.log(`  - Has capability: ${hasCapability}`);
                    console.log(`  - Data-supported: ${dataSupported}`);
                }
            } else {
                console.log(`${panel.name} (${panel.id}): NOT FOUND`);
            }
        }

        // Check grid scrollability
        const gridScrollHeight = await page.locator('.operator-dashboard-grid').evaluate(el => {
            return {
                scrollHeight: el.scrollHeight,
                clientHeight: el.clientHeight,
                canScroll: el.scrollHeight > el.clientHeight
            };
        });

        console.log('\n=== Grid Scroll Info ===');
        console.log(`Scroll Height: ${gridScrollHeight.scrollHeight}px`);
        console.log(`Client Height: ${gridScrollHeight.clientHeight}px`);
        console.log(`Can Scroll: ${gridScrollHeight.canScroll}`);

        // Take a screenshot showing the current state
        await page.screenshot({ path: 'test-results/panel-visibility.png', fullPage: true });
    });
});
