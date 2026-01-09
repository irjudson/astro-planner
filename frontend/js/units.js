// ==========================================
// UNIT CONVERSION UTILITIES
// ==========================================

const Units = {
    // Temperature conversions
    temperature: {
        toDisplay(celsius, units = 'metric') {
            if (units === 'imperial') {
                const fahrenheit = (celsius * 9/5) + 32;
                return `${Math.round(fahrenheit)}°F`;
            }
            return `${Math.round(celsius)}°C`;
        },

        toCelsius(value, fromUnits = 'metric') {
            if (fromUnits === 'imperial') {
                return (value - 32) * 5/9;
            }
            return value;
        },

        toFahrenheit(celsius) {
            return (celsius * 9/5) + 32;
        }
    },

    // Wind speed conversions
    windSpeed: {
        toDisplay(kmh, units = 'metric') {
            if (units === 'imperial') {
                const mph = kmh / 1.60934;
                return `${Math.round(mph * 10) / 10} mph`;
            }
            return `${Math.round(kmh * 10) / 10} km/h`;
        },

        toKmh(value, fromUnits = 'metric') {
            if (fromUnits === 'imperial') {
                return value * 1.60934;
            }
            return value;
        },

        toMph(kmh) {
            return kmh / 1.60934;
        }
    },

    // Pressure conversions
    pressure: {
        toDisplay(inhg, units = 'metric') {
            if (units === 'imperial') {
                return `${Math.round(inhg * 100) / 100} inHg`;
            }
            const mb = inhg * 33.8639;
            return `${Math.round(mb * 10) / 10} mb`;
        },

        toMillibars(inhg) {
            return inhg * 33.8639;
        },

        toInHg(mb) {
            return mb / 33.8639;
        }
    },

    // Distance conversions
    distance: {
        toDisplay(meters, units = 'metric') {
            if (units === 'imperial') {
                const feet = meters * 3.28084;
                if (feet > 5280) {
                    const miles = feet / 5280;
                    return `${Math.round(miles * 10) / 10} mi`;
                }
                return `${Math.round(feet)} ft`;
            }
            if (meters > 1000) {
                return `${Math.round(meters / 100) / 10} km`;
            }
            return `${Math.round(meters)} m`;
        }
    },

    // Get current units preference
    getCurrentUnits() {
        return AppState.preferences?.units || 'metric';
    }
};
