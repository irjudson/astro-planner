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
            // Try local weather station first
            try {
                const localResponse = await fetch('http://localhost:7000/', {
                    signal: AbortSignal.timeout(2000) // 2 second timeout
                });

                if (localResponse.ok) {
                    const localData = await localResponse.json();
                    this.processLocalWeather(localData);
                    this.updateDisplay();
                    return;
                }
            } catch (localError) {
                console.log('Local weather station not available, using 7Timer...');
            }

            // Fallback to 7Timer astronomy weather
            const lat = AppState.planning.location?.latitude || 40.7128;
            const lon = AppState.planning.location?.longitude || -74.0060;

            const response = await fetch(`/api/weather/astronomy?lat=${lat}&lon=${lon}&hours=48`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Use the first forecast entry as "current" conditions
            const current = data.forecast && data.forecast.length > 0 ? data.forecast[0] : null;

            if (current) {
                AppState.weather.conditions = {
                    temperature: current.temperature_c,
                    humidity: null, // 7Timer doesn't provide humidity
                    cloud_cover: current.cloud_cover,
                    wind_speed: current.wind_speed_kmh
                };
                AppState.weather.forecast = data.forecast;
                AppState.weather.observability = this.calculateObservability(current);
            }

            this.updateDisplay();
        } catch (error) {
            console.error('Failed to load weather:', error);
            this.showError();
        }
    },

    processLocalWeather(data) {
        // Process local weather station data
        // Adjust this based on your weather station's data format
        AppState.weather.conditions = {
            temperature: data.temperature || data.temp || data.outTemp,
            humidity: data.humidity || data.outHumidity,
            cloud_cover: data.cloud_cover || data.cloudCover || null,
            wind_speed: data.wind_speed || data.windSpeed
        };

        // Calculate observability from local data
        const observability = this.calculateLocalObservability(data);
        AppState.weather.observability = observability;
        AppState.weather.source = 'local';
    },

    calculateLocalObservability(data) {
        // Calculate based on local conditions
        // This is a simple heuristic - adjust based on your station's capabilities
        const cloudCover = data.cloud_cover || data.cloudCover || 50;
        const humidity = data.humidity || data.outHumidity || 50;

        // Good: low clouds, low humidity
        if (cloudCover < 20 && humidity < 60) return 'good';
        // Fair: moderate conditions
        if (cloudCover < 50 && humidity < 80) return 'fair';
        // Poor: high clouds or humidity
        return 'poor';
    },

    calculateObservability(conditions) {
        // Calculate observability based on astronomy_score (0-1 scale)
        if (conditions.astronomy_score !== undefined) {
            if (conditions.astronomy_score >= 0.7) return 'good';
            if (conditions.astronomy_score >= 0.4) return 'fair';
            return 'poor';
        }

        // Fallback to cloud cover
        const cloudCover = conditions.cloud_cover || 100;
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
