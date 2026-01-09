const { test, expect } = require('@playwright/test');

test.describe('Real API Format Test', () => {
    test('should show all panels with actual API response format', async ({ page }) => {
        await page.goto('http://localhost:8001/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);

        // Click execution
        const executionTitle = await page.locator('.workflow-title:has-text("EXECUTION")');
        await executionTitle.click();
        await page.waitForTimeout(500);

        console.log('\n=== Before Connection ===');

        // Verify panels are hidden
        const telescopePanelBefore = await page.locator('#operator-telescope-panel').evaluate(el =>
            window.getComputedStyle(el).display === 'none'
        );
        console.log('Telescope panel hidden:', telescopePanelBefore);
        expect(telescopePanelBefore).toBe(true);

        console.log('\n=== Dispatching events with REAL API format ===');

        // Use the ACTUAL API response format from your backend
        await page.evaluate(() => {
            // Dispatch connection event
            document.dispatchEvent(new Event('telescope-connected'));

            // Dispatch capabilities with REAL API format
            document.dispatchEvent(new CustomEvent('telescope-capabilities-loaded', {
                detail: {
                    telescope_type: "seestar",
                    capabilities: {
                        goto: true,
                        tracking: true,
                        exposure: true,
                        park: true,
                        autofocus: true,
                        filter_wheel: false,
                        plate_solving: true,
                        guiding: false,
                        stacking: true,
                        dew_heater: true
                    },
                    features: {
                        imaging: {
                            manual_exposure: true,
                            auto_exposure: true,
                            dithering: true,
                            advanced_stacking: true
                        },
                        focuser: {
                            absolute_move: true,
                            relative_move: true,
                            autofocus: true,
                            stop_autofocus: true,
                            factory_reset: true
                        },
                        hardware: {
                            dew_heater: true,
                            dc_output: true,
                            temperature_sensor: false
                        }
                    }
                }
            }));
        });

        await page.waitForTimeout(500);

        console.log('\n=== After Connection ===');

        // Check all panels
        const panelStates = await page.evaluate(() => {
            const panels = [
                { id: '#operator-connection-panel', name: 'Connection' },
                { id: '#operator-telescope-panel', name: 'Telescope Control' },
                { id: '#operator-focus-panel', name: 'Focus Control' },
                { id: '#operator-imaging-panel', name: 'Imaging Settings' },
                { id: '#operator-hardware-panel', name: 'Hardware Controls' },
                { id: '#operator-execution-panel', name: 'Execution' },
                { id: '#operator-telemetry-panel', name: 'Telemetry' },
                { id: '#operator-liveview-panel', name: 'Live Preview' }
            ];

            return panels.map(({ id, name }) => {
                const el = document.querySelector(id);
                return {
                    name,
                    id,
                    exists: !!el,
                    visible: el ? window.getComputedStyle(el).display !== 'none' : false,
                    dataSupported: el ? el.getAttribute('data-supported') : null
                };
            });
        });

        console.log('\nPanel States:');
        panelStates.forEach(state => {
            const status = state.visible ? '✓ VISIBLE' : '✗ HIDDEN';
            console.log(`  ${status} - ${state.name} (data-supported: ${state.dataSupported})`);
        });

        // All 8 panels should be visible
        const visibleCount = panelStates.filter(p => p.visible).length;
        console.log(`\nVisible panels: ${visibleCount}/8`);

        expect(visibleCount).toBe(8);
    });
});
