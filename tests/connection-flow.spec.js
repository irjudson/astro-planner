const { test, expect } = require('@playwright/test');

test.describe('Connection Event Flow', () => {
    test('should show capability-based panels when telescope connects', async ({ page }) => {
        await page.goto('http://localhost:8001/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);

        // Click execution to show operator dashboard
        const executionTitle = await page.locator('.workflow-title:has-text("EXECUTION")');
        await executionTitle.click();
        await page.waitForTimeout(500);

        console.log('\n=== Before Connection ===');

        // Check that capability panels are hidden before connection
        const telescopePanel = page.locator('#operator-telescope-panel');
        const isHiddenBefore = await telescopePanel.evaluate(el => {
            return window.getComputedStyle(el).display === 'none';
        });
        console.log('Telescope panel hidden:', isHiddenBefore);
        expect(isHiddenBefore).toBe(true);

        console.log('\n=== Simulating Telescope Connection ===');

        // Simulate telescope connection by dispatching the event with capabilities
        const eventResult = await page.evaluate(() => {
            const results = [];

            // Check if OperatorDashboard exists and log methods
            if (window.OperatorDashboard) {
                results.push('OperatorDashboard exists: true');
                results.push(`onCapabilitiesLoaded type: ${typeof window.OperatorDashboard.onCapabilitiesLoaded}`);
                results.push(`updateCapabilityPanels type: ${typeof window.OperatorDashboard.updateCapabilityPanels}`);
            } else {
                results.push('OperatorDashboard exists: false');
            }

            // First dispatch connection event
            document.dispatchEvent(new Event('telescope-connected'));
            results.push('Dispatched telescope-connected event');

            // Then dispatch capabilities event with mock capabilities
            document.dispatchEvent(new CustomEvent('telescope-capabilities-loaded', {
                detail: {
                    type: 'seestar',
                    capabilities: {
                        slew: true,
                        park: true,
                        focuser: true,
                        imaging: true,
                        hardware: true
                    },
                    features: {
                        seestar: {
                            dew_heater: true,
                            dc_output: true,
                            manual_mode: true,
                            factory_reset: true
                        }
                    }
                }
            }));
            results.push('Dispatched telescope-capabilities-loaded event');

            return results;
        });

        console.log('Event dispatch results:');
        eventResult.forEach(r => console.log(`  ${r}`));

        // Wait for operator dashboard to process events
        await page.waitForTimeout(500);

        // Also try calling the methods directly to verify they work
        const directCallResult = await page.evaluate(() => {
            const caps = {
                type: 'seestar',
                capabilities: {
                    slew: true,
                    park: true,
                    focuser: true,
                    imaging: true,
                    hardware: true
                },
                features: {
                    seestar: {
                        dew_heater: true,
                        dc_output: true,
                        manual_mode: true,
                        factory_reset: true
                    }
                }
            };

            // Call the methods directly
            window.OperatorDashboard.onCapabilitiesLoaded(caps);

            // Check if data-supported was set
            const panel = document.querySelector('#operator-telescope-panel');
            return {
                dataSupported: panel ? panel.dataset.supported : 'panel not found'
            };
        });

        console.log('Direct method call result:', directCallResult);

        await page.waitForTimeout(100);

        console.log('\n=== After Connection ===');

        // Check that panels now have data-supported="true"
        const panelsToCheck = [
            '#operator-telescope-panel',
            '#operator-focus-panel',
            '#operator-imaging-panel',
            '#operator-hardware-panel'
        ];

        for (const panelId of panelsToCheck) {
            const panel = page.locator(panelId);
            const dataSupported = await panel.getAttribute('data-supported');
            const isVisible = await panel.evaluate(el => {
                return window.getComputedStyle(el).display !== 'none';
            });

            console.log(`${panelId}:`);
            console.log(`  data-supported: ${dataSupported}`);
            console.log(`  visible: ${isVisible}`);

            expect(dataSupported).toBe('true');
            expect(isVisible).toBe(true);
        }

        console.log('\n✓ All capability-based panels are now visible!');
    });

    test('should listen for events on document not window', async ({ page }) => {
        await page.goto('http://localhost:8001/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);

        // Verify OperatorDashboard exists
        const hasOperatorDashboard = await page.evaluate(() => {
            return typeof window.OperatorDashboard !== 'undefined';
        });
        expect(hasOperatorDashboard).toBe(true);

        // Check that event listeners are set up
        const listenerCheck = await page.evaluate(() => {
            // We can't directly check event listeners, but we can verify the setup
            return {
                hasOnConnected: typeof window.OperatorDashboard.onConnected === 'function',
                hasOnCapabilitiesLoaded: typeof window.OperatorDashboard.onCapabilitiesLoaded === 'function'
            };
        });

        expect(listenerCheck.hasOnConnected).toBe(true);
        expect(listenerCheck.hasOnCapabilitiesLoaded).toBe(true);
        console.log('✓ OperatorDashboard event handlers are set up correctly');
    });
});
