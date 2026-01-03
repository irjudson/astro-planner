// ==========================================
// CATALOG LAYOUT MANAGER
// ==========================================

const CatalogLayout = {
    init() {
        this.calculateGridHeight();
        window.addEventListener('resize', () => this.calculateGridHeight());
    },

    calculateGridHeight() {
        const catalogView = document.querySelector('.catalog-view');
        const statsEl = document.querySelector('.catalog-stats');
        const gridEl = document.querySelector('.catalog-grid');
        const paginationEl = document.querySelector('.catalog-pagination');

        if (!catalogView || !statsEl || !gridEl || !paginationEl) return;

        // Get the total available height
        const viewHeight = catalogView.clientHeight;

        // Get the height of fixed elements
        const statsHeight = statsEl.offsetHeight;
        const statsMargin = parseInt(getComputedStyle(statsEl).marginBottom);

        // Calculate space for pagination (always reserve space for consistent layout)
        const paginationHeight = paginationEl.offsetHeight;

        // Calculate available height for grid
        const availableHeight = viewHeight - statsHeight - statsMargin - paginationHeight;

        // Set explicit max-height on grid
        gridEl.style.maxHeight = `${availableHeight}px`;
    },

    updatePaginationVisibility(totalItems, itemsPerPage) {
        const paginationEl = document.querySelector('.catalog-pagination');
        if (!paginationEl) return;

        // Show pagination only if there are more items than fit on one page
        if (totalItems <= itemsPerPage) {
            paginationEl.style.display = 'none';
            // Recalculate grid height since pagination is hidden
            this.calculateGridHeight();
        } else {
            paginationEl.style.display = 'flex';
            this.calculateGridHeight();
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    CatalogLayout.init();
});
