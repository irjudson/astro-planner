// ==========================================
// WEATHER WIDGET
// ==========================================

const WeatherWidget = {
    updateInterval: 300000, // 5 minutes
    intervalId: null,

    init() {
        this.loadWeather();
        this.startAutoUpdate();
    },

    async loadWeather() {
        try {
            // Try to get location from planning state or use default
            const lat = AppState.planning.location?.latitude || 40.7128;
            const lon = AppState.planning.location?.longitude || -74.0060;

            const response = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
            const weather = await response.json();

            AppState.weather.conditions = weather.current;
            AppState.weather.forecast = weather.forecast;
            AppState.weather.observability = this.calculateObservability(weather);

            this.updateDisplay();
        } catch (error) {
            console.error('Failed to load weather:', error);
            this.showError();
        }
    },

    calculateObservability(weather) {
        // Simple observability calculation based on cloud cover
        const cloudCover = weather.current?.cloud_cover || 100;

        if (cloudCover < 30) return 'good';
        if (cloudCover < 70) return 'fair';
        return 'poor';
    },

    updateDisplay() {
        const statusEl = document.querySelector('.weather-status');
        const detailsEl = document.getElementById('weather-details');
        const iconEl = document.querySelector('.weather-icon');

        if (!AppState.weather.conditions) {
            if (statusEl) statusEl.textContent = 'Weather unavailable';
            return;
        }

        const conditions = AppState.weather.conditions;
        const observability = AppState.weather.observability;

        // Update icon
        if (iconEl) {
            iconEl.textContent = this.getWeatherIcon(conditions, observability);
        }

        // Update status
        if (statusEl) {
            const temp = conditions.temperature ? `${Math.round(conditions.temperature)}°C` : '--';
            statusEl.textContent = `${temp} • ${observability.charAt(0).toUpperCase() + observability.slice(1)}`;
            statusEl.className = `weather-status observability-${observability}`;
        }

        // Update details
        if (detailsEl) {
            detailsEl.innerHTML = `
                <div class="weather-detail-row">
                    <span>Humidity:</span>
                    <span>${conditions.humidity || '--'}%</span>
                </div>
                <div class="weather-detail-row">
                    <span>Cloud Cover:</span>
                    <span>${conditions.cloud_cover || '--'}%</span>
                </div>
                <div class="weather-detail-row">
                    <span>Wind:</span>
                    <span>${conditions.wind_speed || '--'} km/h</span>
                </div>
                <div class="weather-detail-row">
                    <span>Observing:</span>
                    <span class="observability-${observability}">${observability.toUpperCase()}</span>
                </div>
            `;
        }
    },

    getWeatherIcon(conditions, observability) {
        // Simple icon selection based on conditions
        if (observability === 'good') return '🌙';
        if (observability === 'fair') return '⛅';
        return '☁️';
    },

    showError() {
        const statusEl = document.querySelector('.weather-status');
        if (statusEl) {
            statusEl.textContent = 'Weather unavailable';
        }
    },

    startAutoUpdate() {
        this.intervalId = setInterval(() => {
            this.loadWeather();
        }, this.updateInterval);
    },

    stopAutoUpdate() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    WeatherWidget.init();
});
