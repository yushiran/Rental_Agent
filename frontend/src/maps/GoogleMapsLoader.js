/**
 * GoogleMapsLoader - Google Maps API Loader
 * Dynamically loads the Google Maps JavaScript API
 */
class GoogleMapsLoader {
    constructor(apiKey = '') {
        this.apiKey = apiKey;
        this.isLoaded = false;
        this.loadPromise = null;
        this.libraries = ['geometry', 'places'];
    }

    /**
     * Load Google Maps API
     */
    async load() {
        if (this.isLoaded) {
            return Promise.resolve();
        }

        if (this.loadPromise) {
            return this.loadPromise;
        }

        this.loadPromise = new Promise((resolve, reject) => {
            // Check if already loaded
            if (window.google && window.google.maps) {
                this.isLoaded = true;
                resolve();
                return;
            }

            // Create global callback
            const callbackName = 'googleMapsInitCallback';
            window[callbackName] = () => {
                this.isLoaded = true;
                delete window[callbackName];
                console.log('[GoogleMapsLoader] Google Maps API loading completed');
                resolve();
            };

            // Create script tag
            const script = document.createElement('script');
            script.async = true;
            script.defer = true;
            
            // Build API URL - Remove API Key requirement, use development mode
            const params = new URLSearchParams({
                callback: callbackName,
                libraries: this.libraries.join(','),
                v: 'weekly'
            });

            // Only add API Key if provided, otherwise use free quota
            if (this.apiKey && this.apiKey.trim() !== '') {
                params.set('key', this.apiKey);
            }

            script.src = `https://maps.googleapis.com/maps/api/js?${params.toString()}`;
            
            // Error handling
            script.onerror = () => {
                delete window[callbackName];
                console.warn('[GoogleMapsLoader] Google Maps API loading failed, API Key may be required');
                // Don't completely reject, try to continue
                resolve();
            };

            // Add to page
            document.head.appendChild(script);
        });

        return this.loadPromise;
    }

    /**
     * Set API Key
     */
    setApiKey(apiKey) {
        if (this.isLoaded) {
            console.warn('[GoogleMapsLoader] API already loaded, cannot modify API Key');
            return;
        }
        this.apiKey = apiKey;
    }

    /**
     * Add Library
     */
    addLibrary(library) {
        if (this.isLoaded) {
            console.warn('[GoogleMapsLoader] API already loaded, cannot add new library');
            return;
        }
        if (!this.libraries.includes(library)) {
            this.libraries.push(library);
        }
    }

    /**
     * Check if API is loaded
     */
    isApiLoaded() {
        return this.isLoaded && window.google && window.google.maps;
    }
}

// Create singleton instance
const googleMapsLoader = new GoogleMapsLoader();

export default googleMapsLoader;
