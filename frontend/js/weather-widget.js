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
                const localResponse = await fetch('http://192.168.2.111:7000/api/weather/latest', {
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
                AppState.weather.source = '7timer';
            }

            this.updateDisplay();
        } catch (error) {
            console.error('Failed to load weather:', error);
            this.showError();
        }
    },

    processLocalWeather(data) {
        // Process local weather station data from wx-tools
        // Convert Fahrenheit to Celsius
        const tempC = data.outdoor_temp_f ? (data.outdoor_temp_f - 32) * 5 / 9 : null;
        // Convert mph to km/h
        const windKmh = data.wind_speed_mph ? data.wind_speed_mph * 1.60934 : null;

        AppState.weather.conditions = {
            temperature: tempC,
            humidity: data.humidity_pct,
            cloud_cover: null, // Local station doesn't provide cloud cover
            wind_speed: windKmh
        };

        // Calculate observability from local data
        const observability = this.calculateLocalObservability(data);
        AppState.weather.observability = observability;
        AppState.weather.source = 'local';
    },

    calculateLocalObservability(data) {
        // Calculate based on local conditions
        // Without cloud cover data, use humidity and solar radiation as proxies
        const humidity = data.humidity_pct || 50;
        const solarRadiation = data.solar_radiation_wm2 || 0;

        // Nighttime (solar_radiation near 0) with low humidity is good for astronomy
        if (solarRadiation < 10) {
            if (humidity < 60) return 'good';
            if (humidity < 80) return 'fair';
            return 'poor';
        }

        // Daytime - can't observe
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
            const units = Units.getCurrentUnits();
            const temp = conditions.temperature ? Units.temperature.toDisplay(conditions.temperature, units) : '--';
            statusEl.textContent = `${temp} • ${observability.charAt(0).toUpperCase() + observability.slice(1)}`;
            statusEl.className = `weather-status observability-${observability}`;
        }

        // Update details
        if (detailsEl) {
            const units = Units.getCurrentUnits();
            const source = AppState.weather.source || '7timer';
            const sourceLabel = source === 'local' ? 'Local Station' : '7Timer';
            const sourceClass = source === 'local' ? 'weather-source-local' : 'weather-source-remote';
            const windSpeed = conditions.wind_speed ? Units.windSpeed.toDisplay(conditions.wind_speed, units) : '--';

            detailsEl.innerHTML = `
                <div class="weather-detail-row">
                    <span>Source:</span>
                    <span class="${sourceClass}">${sourceLabel}</span>
                </div>
                <div class="weather-detail-row">
                    <span>Humidity:</span>
                    <span>${conditions.humidity !== null ? conditions.humidity + '%' : '--'}</span>
                </div>
                <div class="weather-detail-row">
                    <span>Cloud Cover:</span>
                    <span>${conditions.cloud_cover !== null ? conditions.cloud_cover + '%' : '--'}</span>
                </div>
                <div class="weather-detail-row">
                    <span>Wind:</span>
                    <span>${windSpeed}</span>
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
