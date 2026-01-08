/**
 * Catalog Search Module
 * Handles catalog data loading, filtering, and grid population
 */

const CatalogSearch = {
    currentPage: 1,
    pageSize: 20, // Will be calculated dynamically
    totalItems: 0,
    prefetchCache: new Map(), // Cache for prefetched pages
    isCalculating: false, // Prevent recalculation loops
    masonryInstance: null, // Masonry layout instance

    /**
     * Initialize catalog search functionality
     */
    init() {
        this.attachEventListeners();

        // Calculate page size after DOM is ready and layout has settled
        setTimeout(() => {
            this.isCalculating = true;
            this.calculatePageSize();
            this.isCalculating = false;
            this.loadCatalogData(); // Load initial data
        }, 300); // Give layout time to settle

        this.updateSelectedTargetsList(); // Initialize selected targets list

        // Use ResizeObserver to watch main-content for size changes (window resize, drawer expand/collapse, etc.)
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            let resizeTimeout;
            const resizeObserver = new ResizeObserver(() => {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => {
                    if (this.isCalculating) return; // Prevent loops

                    this.isCalculating = true;
                    const oldPageSize = this.pageSize;
                    const newPageSize = this.calculatePageSize();
                    this.isCalculating = false;

                    if (newPageSize !== oldPageSize) {
                        console.log(`Container resized: page size ${oldPageSize} → ${newPageSize}, reloading...`);
                        this.currentPage = 1;
                        this.prefetchCache.clear(); // Clear cache on resize
                        this.loadCatalogData();
                    }
                }, 250);
            });
            resizeObserver.observe(mainContent);
        }
    },

    /**
     * Calculate optimal page size to fit viewport without scrolling
     */
    calculatePageSize() {
        const mainContent = document.getElementById('main-content');
        const catalogGrid = document.getElementById('catalog-grid');
        const catalogPagination = document.getElementById('catalog-pagination');

        if (!mainContent || !catalogGrid) {
            this.pageSize = 20;
            return 20;
        }

        // Measure the main-content height (the actual available viewport)
        const mainHeight = mainContent.clientHeight;
        const paginationHeight = catalogPagination ? catalogPagination.offsetHeight : 50;

        // Available height for grid (subtract pagination and main-content padding)
        const mainPadding = 48; // 24px top + 24px bottom from .main-content padding
        const availableHeight = mainHeight - paginationHeight - mainPadding;

        // Use ACTUAL grid width, not window width
        const gridWidth = catalogGrid.clientWidth;

        // Card dimensions from CSS minmax() - based on SCREEN width media query, not grid width
        const screenWidth = window.innerWidth;
        const cardMinWidth = screenWidth > 768 ? 260 : 220;
        const gap = 16;

        // Calculate how many cards per row (with smart rounding)
        const exactCardsPerRow = (gridWidth + gap) / (cardMinWidth + gap);
        // If we can fit >= 0.8 of another column, round up and let CSS grid shrink to fit
        const cardsPerRow = Math.max(1, exactCardsPerRow % 1 >= 0.8 ? Math.ceil(exactCardsPerRow) : Math.floor(exactCardsPerRow));

        // Card height: 310px min-height + 16px gap = 326px per row
        const rowHeight = 326;

        // Calculate rows that fit (with smart rounding)
        const exactRowsThatFit = availableHeight / rowHeight;
        // If we can fit >= 0.8 of another row, round up and let CSS grid shrink to fit
        const rowsThatFit = Math.max(1, exactRowsThatFit % 1 >= 0.8 ? Math.ceil(exactRowsThatFit) : Math.floor(exactRowsThatFit));
        const itemsThatFit = rowsThatFit * cardsPerRow;

        // Use a minimum of 1 row and maximum of 50 items
        this.pageSize = Math.max(cardsPerRow, Math.min(50, itemsThatFit));

        console.log(`📊 Page size: ${this.pageSize} items (${rowsThatFit} rows × ${cardsPerRow} per row)`);
        console.log(`   Grid: ${gridWidth}px wide, ${availableHeight}px available height`);
        return this.pageSize;
    },

    /**
     * Attach event listeners to search and filter controls
     */
    attachEventListeners() {
        // Search button
        const searchBtn = document.getElementById('catalog-search-btn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.handleSearch());
        }

        // Search on Enter key
        const searchInput = document.getElementById('catalog-search');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.handleSearch();
                }
            });
        }

        // Apply Filters button
        const applyBtn = document.getElementById('apply-filters-btn');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.handleSearch());
        }

        // Clear Filters button
        const clearBtn = document.getElementById('clear-filters-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.handleClearFilters());
        }

        // Pagination buttons
        const prevBtn = document.getElementById('prev-page-btn');
        const nextBtn = document.getElementById('next-page-btn');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.handlePrevPage());
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.handleNextPage());
        }
    },

    /**
     * Get current filter values from form
     */
    getFilters() {
        const searchInput = document.getElementById('catalog-search');
        const typeFilter = document.getElementById('filter-type');
        const constellationFilter = document.getElementById('filter-constellation');
        const magnitudeFilter = document.getElementById('filter-magnitude');
        const sortBy = document.getElementById('sort-by');

        return {
            search: searchInput?.value || '',
            type: typeFilter?.value || '',
            constellation: constellationFilter?.value || '',
            max_magnitude: magnitudeFilter?.value || '',
            sort_by: sortBy?.value || 'name',
            page: this.currentPage,
            page_size: this.pageSize
        };
    },

    /**
     * Handle search button click
     */
    handleSearch() {
        this.currentPage = 1; // Reset to first page
        this.loadCatalogData();
    },

    /**
     * Handle clear filters button click
     */
    handleClearFilters() {
        console.log('Clearing filters...');

        // Clear all filter inputs
        const searchInput = document.getElementById('catalog-search');
        const typeFilter = document.getElementById('filter-type');
        const constellationFilter = document.getElementById('filter-constellation');
        const magnitudeFilter = document.getElementById('filter-magnitude');
        const sortBy = document.getElementById('sort-by');

        if (searchInput) {
            searchInput.value = '';
            console.log('Cleared search input');
        }
        if (typeFilter) {
            typeFilter.value = '';
            typeFilter.selectedIndex = 0; // Ensure first option is selected
            console.log('Cleared type filter');
        }
        if (constellationFilter) {
            constellationFilter.value = '';
            constellationFilter.selectedIndex = 0; // Ensure first option is selected
            console.log('Cleared constellation filter');
        }
        if (magnitudeFilter) {
            magnitudeFilter.value = '';
            console.log('Cleared magnitude filter');
        }
        if (sortBy) {
            sortBy.value = 'name';
            console.log('Reset sort to name');
        }

        this.currentPage = 1;
        console.log('Reloading catalog data...');
        this.loadCatalogData();
    },

    /**
     * Handle previous page button click
     */
    handlePrevPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadCatalogData();
        }
    },

    /**
     * Handle next page button click
     */
    handleNextPage() {
        const totalPages = Math.ceil(this.totalItems / this.pageSize);
        if (this.currentPage < totalPages) {
            this.currentPage++;
            this.loadCatalogData();
        }
    },

    /**
     * Load catalog data from API
     */
    async loadCatalogData() {
        try {
            const filters = this.getFilters();
            const cacheKey = JSON.stringify(filters);

            // Check cache first
            if (this.prefetchCache.has(cacheKey)) {
                const cached = this.prefetchCache.get(cacheKey);
                console.log(`Using cached data for page ${this.currentPage}`);
                this.totalItems = cached.total || 0;
                this.renderCatalogGrid(cached.items || []);
                this.updateStats(cached.total || 0, filters);
                this.updatePagination();

                // Still prefetch next page in background
                this.prefetchNextPage(filters);
                return;
            }

            const queryParams = new URLSearchParams();

            // Only add non-empty params
            Object.entries(filters).forEach(([key, value]) => {
                if (value !== '') {
                    queryParams.append(key, value);
                }
            });

            const response = await fetch(`/api/catalog/search?${queryParams.toString()}`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Cache the result
            this.prefetchCache.set(cacheKey, data);

            this.totalItems = data.total || 0;
            this.renderCatalogGrid(data.items || []);
            this.updateStats(data.total || 0, filters);
            this.updatePagination();

            // Update app state
            if (window.AppState) {
                AppState.discovery.catalogData = data.items || [];
                AppState.discovery.currentPage = this.currentPage;
                AppState.save();
            }

            // Prefetch next page in background
            this.prefetchNextPage(filters);

        } catch (error) {
            console.error('Error loading catalog data:', error);
            this.showError('Failed to load catalog data. Please try again.');
        }
    },

    /**
     * Prefetch the next page in the background
     */
    async prefetchNextPage(currentFilters) {
        const totalPages = Math.ceil(this.totalItems / this.pageSize);
        const nextPage = this.currentPage + 1;

        if (nextPage > totalPages) {
            return; // No next page
        }

        const nextFilters = { ...currentFilters, page: nextPage };
        const cacheKey = JSON.stringify(nextFilters);

        // Don't prefetch if already cached
        if (this.prefetchCache.has(cacheKey)) {
            return;
        }

        try {
            const queryParams = new URLSearchParams();
            Object.entries(nextFilters).forEach(([key, value]) => {
                if (value !== '') {
                    queryParams.append(key, value);
                }
            });

            console.log(`Prefetching page ${nextPage}...`);
            const response = await fetch(`/api/catalog/search?${queryParams.toString()}`);

            if (response.ok) {
                const data = await response.json();
                this.prefetchCache.set(cacheKey, data);
                console.log(`Prefetched page ${nextPage} (${data.items.length} items)`);

                // Limit cache size to 5 pages to avoid memory issues
                if (this.prefetchCache.size > 5) {
                    const firstKey = this.prefetchCache.keys().next().value;
                    this.prefetchCache.delete(firstKey);
                }
            }
        } catch (error) {
            console.warn('Prefetch failed:', error);
            // Silent failure - prefetch is non-critical
        }
    },

    /**
     * Render catalog grid with items
     */
    renderCatalogGrid(items) {
        const grid = document.getElementById('catalog-grid');
        const emptyState = document.getElementById('catalog-empty-state');

        if (!grid) return;

        // Destroy existing masonry instance
        if (this.masonryInstance) {
            this.masonryInstance.destroy();
            this.masonryInstance = null;
        }

        // Clear existing cards (except empty state)
        const cards = grid.querySelectorAll('.catalog-card');
        cards.forEach(card => card.remove());

        if (items.length === 0) {
            // Show empty state
            if (emptyState) {
                emptyState.classList.remove('hidden');
            }
            return;
        }

        // Hide empty state
        if (emptyState) {
            emptyState.classList.add('hidden');
        }

        // Create and append cards
        items.forEach(item => {
            const card = this.createCatalogCard(item);
            grid.appendChild(card);
        });

        // Initialize Masonry layout
        if (typeof Masonry !== 'undefined') {
            // Use setTimeout to ensure DOM has updated
            setTimeout(() => {
                this.masonryInstance = new Masonry(grid, {
                    itemSelector: '.catalog-card',
                    columnWidth: '.catalog-card',
                    gutter: 16,
                    fitWidth: false,
                    percentPosition: false
                });
                console.log('Masonry layout initialized');
            }, 0);
        }
    },

    /**
     * Create a single catalog card element
     */
    createCatalogCard(item) {
        const card = document.createElement('div');
        card.className = 'catalog-card';
        card.dataset.itemId = item.id || item.name;

        // Build title with catalog ID and common name
        let title = item.id || item.name || 'Unknown';
        if (item.common_name && item.common_name !== item.id) {
            // Show both catalog ID and common name
            title = `${this.escapeHtml(item.id)} - ${this.escapeHtml(item.common_name)}`;
        }

        // Image URL
        const imageUrl = item.image_url || `/api/images/targets/${encodeURIComponent(item.id || item.name)}`;

        card.innerHTML = `
            <div class="catalog-card-image">
                <img src="${imageUrl}" alt="${this.escapeHtml(item.name)}" loading="lazy" onerror="this.parentElement.style.display='none'">
            </div>
            <div class="catalog-card-content">
                <div class="catalog-card-header">
                    <h4 class="catalog-card-title">${title}</h4>
                    <span class="catalog-card-type">${this.escapeHtml(item.type || 'unknown')}</span>
                </div>
            <div class="catalog-card-body">
                <div class="catalog-card-detail">
                    <span class="catalog-card-label">Constellation:</span>
                    <span class="catalog-card-value">${this.formatConstellation(item)}</span>
                </div>
                <div class="catalog-card-detail">
                    <span class="catalog-card-label">Magnitude:</span>
                    <span class="catalog-card-value">${item.magnitude !== null && item.magnitude !== undefined ? item.magnitude.toFixed(1) : 'N/A'}</span>
                </div>
                <div class="catalog-card-detail">
                    <span class="catalog-card-label">RA/Dec:</span>
                    <span class="catalog-card-value">${this.formatCoordinates(item.ra, item.dec)}</span>
                </div>
                ${item.size ? `
                <div class="catalog-card-detail">
                    <span class="catalog-card-label">Size:</span>
                    <span class="catalog-card-value">${this.escapeHtml(item.size)}</span>
                </div>
                ` : ''}
            </div>
            <div class="catalog-card-actions">
                <button class="btn btn-primary btn-sm" data-action="add-to-plan">Add to Plan</button>
                <button class="btn btn-secondary btn-sm" data-action="view-details">Details</button>
            </div>
            </div>
        `;

        // Attach card event listeners
        const addToPlanBtn = card.querySelector('[data-action="add-to-plan"]');
        const viewDetailsBtn = card.querySelector('[data-action="view-details"]');

        if (addToPlanBtn) {
            addToPlanBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleAddToPlan(item);
            });
        }

        if (viewDetailsBtn) {
            viewDetailsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleViewDetails(item);
            });
        }

        return card;
    },

    /**
     * Format RA/Dec coordinates
     */
    formatCoordinates(ra, dec) {
        if (ra === null || ra === undefined || dec === null || dec === undefined) {
            return 'N/A';
        }
        return `${this.formatRA(ra)} / ${this.formatDec(dec)}`;
    },

    /**
     * Format constellation with full name and common name
     */
    formatConstellation(item) {
        if (!item.constellation_full) {
            return item.constellation || 'N/A';
        }

        if (item.constellation_common) {
            return `<div style="text-align: right;">${this.escapeHtml(item.constellation_full)}<br><span style="font-size: 0.9em; color: rgba(255, 255, 255, 0.6);">(${this.escapeHtml(item.constellation_common)})</span></div>`;
        }

        return this.escapeHtml(item.constellation_full);
    },

    /**
     * Format RA in hours:minutes:seconds
     */
    formatRA(ra) {
        // Convert degrees to hours (360° = 24h)
        const hours = ra / 15.0;
        const h = Math.floor(hours);
        const m = Math.floor((hours - h) * 60);
        const s = Math.floor(((hours - h) * 60 - m) * 60);
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    },

    /**
     * Format Dec in degrees:arcminutes:arcseconds
     */
    formatDec(dec) {
        const sign = dec >= 0 ? '+' : '-';
        const absDec = Math.abs(dec);
        const d = Math.floor(absDec);
        const m = Math.floor((absDec - d) * 60);
        const s = Math.floor(((absDec - d) * 60 - m) * 60);
        return `${sign}${d.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    },

    /**
     * Update stats banner
     */
    updateStats(total, filters) {
        const statsCount = document.querySelector('.stats-count');
        const statsFilters = document.getElementById('stats-filters');

        if (statsCount) {
            statsCount.textContent = `${total} object${total !== 1 ? 's' : ''}`;
        }

        if (statsFilters) {
            const activeFilters = [];

            if (filters.search) activeFilters.push(`Search: "${filters.search}"`);
            if (filters.type) activeFilters.push(`Type: ${filters.type}`);
            if (filters.constellation) activeFilters.push(`Constellation: ${filters.constellation}`);
            if (filters.max_magnitude) activeFilters.push(`Max Mag: ${filters.max_magnitude}`);

            statsFilters.textContent = activeFilters.length > 0
                ? activeFilters.join(' • ')
                : '';
        }
    },

    /**
     * Update pagination controls
     */
    updatePagination() {
        const prevBtn = document.getElementById('prev-page-btn');
        const nextBtn = document.getElementById('next-page-btn');
        const pageInfo = document.getElementById('page-info');

        const totalPages = Math.ceil(this.totalItems / this.pageSize);

        if (prevBtn) {
            prevBtn.disabled = this.currentPage <= 1;
        }

        if (nextBtn) {
            nextBtn.disabled = this.currentPage >= totalPages;
        }

        if (pageInfo) {
            pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
        }

        // Update pagination visibility based on total items
        if (window.CatalogLayout) {
            CatalogLayout.updatePaginationVisibility(this.totalItems, this.pageSize);
        }
    },

    /**
     * Handle "Add to Plan" button click
     */
    handleAddToPlan(item) {
        console.log('Adding to plan:', item);

        // Update AppState
        if (!window.AppState) {
            console.error('AppState not found!');
            alert('Error: Application state not initialized');
            return;
        }

        console.log('Current selected targets:', AppState.discovery.selectedTargets);

        const exists = AppState.discovery.selectedTargets.find(t => t.name === item.name);
        if (exists) {
            console.log('Target already exists in plan');
            // Show notification instead of alert
            const notification = document.createElement('div');
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(255, 165, 0, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
            notification.textContent = `${item.name} is already in your plan`;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);
            return;
        }

        AppState.discovery.selectedTargets.push(item);
        AppState.save();

        console.log('Target added. Total selected:', AppState.discovery.selectedTargets.length);

        // Update Custom Plan Builder panel
        this.updateSelectedTargetsList();
        console.log('updateSelectedTargetsList() called');

        // Show confirmation
        const notification = document.createElement('div');
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: rgba(0, 217, 255, 0.9); color: white; padding: 12px 20px; border-radius: 4px; z-index: 10000;';
        notification.textContent = `Added ${item.name} to plan`;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 2000);
    },

    /**
     * Handle "View Details" button click
     */
    handleViewDetails(item) {
        console.log('Viewing details:', item);

        // Create modal content
        const modalHtml = `
            <div class="modal" id="target-details-modal" style="display: flex;">
                <div class="modal-content modal-dark" style="max-width: 600px;">
                    <div class="modal-header">
                        <h2>${this.escapeHtml(item.name || 'Unknown Target')}</h2>
                        <button class="modal-close" id="target-details-close">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="target-details">
                            <div class="detail-row">
                                <span class="detail-label">Type:</span>
                                <span class="detail-value">${this.escapeHtml(item.type || 'Unknown')}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Constellation:</span>
                                <span class="detail-value">${this.formatConstellation(item)}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Magnitude:</span>
                                <span class="detail-value">${item.magnitude !== null && item.magnitude !== undefined ? item.magnitude.toFixed(1) : 'N/A'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Right Ascension:</span>
                                <span class="detail-value">${item.ra !== null && item.ra !== undefined ? item.ra.toFixed(4) + '°' : 'N/A'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Declination:</span>
                                <span class="detail-value">${item.dec !== null && item.dec !== undefined ? item.dec.toFixed(4) + '°' : 'N/A'}</span>
                            </div>
                            ${item.size ? `
                            <div class="detail-row">
                                <span class="detail-label">Size:</span>
                                <span class="detail-value">${this.escapeHtml(item.size)}</span>
                            </div>
                            ` : ''}
                            ${item.common_name ? `
                            <div class="detail-row">
                                <span class="detail-label">Common Name:</span>
                                <span class="detail-value">${this.escapeHtml(item.common_name)}</span>
                            </div>
                            ` : ''}
                            ${item.description ? `
                            <div class="detail-row" style="flex-direction: column; align-items: flex-start;">
                                <span class="detail-label">Description:</span>
                                <p class="detail-value" style="margin-top: 8px; line-height: 1.6;">${this.escapeHtml(item.description)}</p>
                            </div>
                            ` : ''}
                        </div>
                        <div style="margin-top: 20px; display: flex; gap: 12px;">
                            <button class="btn btn-primary" id="add-from-details-btn" style="flex: 1;">Add to Plan</button>
                            <button class="btn btn-secondary" id="close-details-btn" style="flex: 1;">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('target-details-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Add event listeners
        const modal = document.getElementById('target-details-modal');
        const closeBtn = document.getElementById('target-details-close');
        const closeDetailsBtn = document.getElementById('close-details-btn');
        const addFromDetailsBtn = document.getElementById('add-from-details-btn');

        const closeModal = () => {
            if (modal) modal.remove();
        };

        if (closeBtn) closeBtn.addEventListener('click', closeModal);
        if (closeDetailsBtn) closeDetailsBtn.addEventListener('click', closeModal);
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) closeModal();
            });
        }

        if (addFromDetailsBtn) {
            addFromDetailsBtn.addEventListener('click', () => {
                this.handleAddToPlan(item);
                closeModal();
            });
        }
    },

    /**
     * Update selected targets list in Custom Plan Builder panel
     */
    updateSelectedTargetsList() {
        const targetsList = document.getElementById('selected-targets-list');
        const createBtn = document.getElementById('create-custom-plan-btn');

        console.log('updateSelectedTargetsList: targetsList element found?', !!targetsList);
        console.log('updateSelectedTargetsList: AppState exists?', !!window.AppState);

        if (!targetsList) {
            console.error('selected-targets-list element not found!');
            return;
        }

        if (!window.AppState) {
            console.error('AppState not found!');
            return;
        }

        const selectedTargets = AppState.discovery.selectedTargets || [];
        console.log('updateSelectedTargetsList: selectedTargets count =', selectedTargets.length);

        if (selectedTargets.length === 0) {
            targetsList.innerHTML = '<p class="empty-state">No targets selected</p>';
            if (createBtn) createBtn.disabled = true;
            return;
        }

        targetsList.innerHTML = selectedTargets.map(target => `
            <div class="selected-target-item">
                <span class="target-name">${this.escapeHtml(target.name)}</span>
                <button class="btn-remove" data-target-name="${this.escapeHtml(target.name)}">&times;</button>
            </div>
        `).join('');

        console.log('updateSelectedTargetsList: Updated targetsList HTML');

        if (createBtn) createBtn.disabled = false;

        // Attach remove button listeners
        targetsList.querySelectorAll('.btn-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetName = e.target.dataset.targetName;
                this.removeSelectedTarget(targetName);
            });
        });
    },

    /**
     * Remove target from selected targets
     */
    removeSelectedTarget(targetName) {
        if (window.AppState) {
            AppState.discovery.selectedTargets = AppState.discovery.selectedTargets.filter(
                t => t.name !== targetName
            );
            AppState.save();
            this.updateSelectedTargetsList();
        }
    },

    /**
     * Show error message
     */
    showError(message) {
        // TODO: Implement toast notification or error banner
        console.error(message);
        alert(message);
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    CatalogSearch.init();
});
