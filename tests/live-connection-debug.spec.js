const { test, expect } = require('@playwright/test');

test.describe('Live Connection Debugging', () => {
    test('should capture console logs during real connection', async ({ page }) => {
        const consoleLogs = [];

        page.on('console', msg => {
            const text = msg.text();
            // Only capture OperatorDashboard logs
            if (text.includes('OperatorDashboard') || text.includes('telescope-') || text.includes('Capabilities')) {
                consoleLogs.push(text);
            }
        });

        await page.goto('http://localhost:8001/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);

        // Click execution
        const executionTitle = await page.locator('.workflow-title:has-text("EXECUTION")');
        await executionTitle.click();
        await page.waitForTimeout(1000);

        console.log('\n=== Console Logs ===');
        consoleLogs.forEach(log => console.log(log));

        // Check current state of panels
        const panelStates = await page.evaluate(() => {
            const panels = [
                '#operator-connection-panel',
                '#operator-telescope-panel',
                '#operator-focus-panel',
                '#operator-imaging-panel',
                '#operator-hardware-panel'
            ];

            return panels.map(id => {
                const el = document.querySelector(id);
                if (!el) return { id, exists: false };

                return {
                    id,
                    exists: true,
                    visible: window.getComputedStyle(el).display !== 'none',
                    dataCapability: el.getAttribute('data-capability'),
                    dataSupported: el.getAttribute('data-supported'),
                    dataFeature: el.getAttribute('data-feature')
                };
            });
        });

        console.log('\n=== Panel States ===');
        panelStates.forEach(state => {
            console.log(JSON.stringify(state, null, 2));
        });

        // Check if ConnectionManager is connected
        const connectionState = await page.evaluate(() => {
            return {
                hasConnectionManager: typeof window.ConnectionManager !== 'undefined',
                isConnected: window.ConnectionManager?.isConnected,
                currentDevice: window.ConnectionManager?.currentDevice
            };
        });

        console.log('\n=== Connection State ===');
        console.log(JSON.stringify(connectionState, null, 2));

        // Check if TelescopeCapabilities has data
        const capabilitiesState = await page.evaluate(() => {
            return {
                hasTelescopeCapabilities: typeof window.TelescopeCapabilities !== 'undefined',
                telescopeType: window.TelescopeCapabilities?.telescopeType,
                capabilities: window.TelescopeCapabilities?.capabilities,
                features: window.TelescopeCapabilities?.features
            };
        });

        console.log('\n=== Capabilities State ===');
        console.log(JSON.stringify(capabilitiesState, null, 2));

        // Check OperatorDashboard state
        const operatorState = await page.evaluate(() => {
            return {
                hasOperatorDashboard: typeof window.OperatorDashboard !== 'undefined',
                isConnected: window.OperatorDashboard?.isConnected,
                currentCapabilities: window.OperatorDashboard?.currentCapabilities
            };
        });

        console.log('\n=== OperatorDashboard State ===');
        console.log(JSON.stringify(operatorState, null, 2));
    });
});
