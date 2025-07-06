/**
 * MapManager - Google Maps Manager
 * Responsible for map initialization, marker management and interaction handling
 */
class MapManager {
    constructor() {
        this.map = null;
        this.agentMarkers = new Map();
        this.propertyMarkers = new Map();
        this.infoWindows = new Map();
        this.isInitialized = false;
        this.eventListeners = new Map();
        
        // Marker position cache for overlap detection
        this.markerPositions = new Map(); // key: "lat,lng", value: count
        
        // Map configuration
        this.config = {
            center: { lat: 51.5074, lng: -0.1278 }, // London city center
            zoom: 13,
            styles: this.getMapStyles()
        };
        
        // Overlap detection configuration
        this.overlapConfig = {
            threshold: 0.0001, // About 10 meters threshold
            offsetDistance: 0.0002, // About 20 meters offset distance
            maxAttempts: 8 // Maximum 8 direction attempts
        };
    }

    /**
     * Initialize Google Maps
     */
    async initialize(containerId) {
        if (!window.google || !window.google.maps) {
            throw new Error('Google Maps API not loaded');
        }

        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`Container element not found: ${containerId}`);
        }

        this.map = new google.maps.Map(container, this.config);
        this.isInitialized = true;
        
        console.log('[MapManager] Google Maps initialization completed');
        this.emit('map:initialized', { map: this.map });
    }

    /**
     * Get Map Styles
     */
    getMapStyles() {
        return [
            {
                "featureType": "all",
                "elementType": "geometry",
                "stylers": [{ "color": "#f5f5f5" }]
            },
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{ "color": "#c9e6ff" }]
            },
            {
                "featureType": "road",
                "elementType": "geometry",
                "stylers": [{ "color": "#ffffff" }]
            },
            {
                "featureType": "poi.business",
                "stylers": [{ "visibility": "off" }]
            }
        ];
    }

    /**
     * Check if position overlaps with existing markers
     */
    isPositionOverlapped(position) {
        const positionKey = `${position.lat.toFixed(6)},${position.lng.toFixed(6)}`;
        
        // Check exact position
        if (this.markerPositions.has(positionKey)) {
            return true;
        }
        
        // Check nearby positions (within threshold)
        for (const [existingKey, count] of this.markerPositions) {
            if (count > 0) {
                const [latStr, lngStr] = existingKey.split(',');
                const existingLat = parseFloat(latStr);
                const existingLng = parseFloat(lngStr);
                
                const distance = Math.sqrt(
                    Math.pow(position.lat - existingLat, 2) + 
                    Math.pow(position.lng - existingLng, 2)
                );
                
                if (distance < this.overlapConfig.threshold) {
                    return true;
                }
            }
        }
        
        return false;
    }

    /**
     * Calculate non-overlapping position offset
     */
    calculateNonOverlappingPosition(originalPosition) {
        if (!this.isPositionOverlapped(originalPosition)) {
            return originalPosition;
        }

        // Try offsets in 8 directions
        const angles = [0, 45, 90, 135, 180, 225, 270, 315]; // degrees
        
        for (let attempt = 0; attempt < this.overlapConfig.maxAttempts; attempt++) {
            const angle = angles[attempt] * Math.PI / 180; // convert to radians
            const distance = this.overlapConfig.offsetDistance * (attempt + 1);
            
            const offsetPosition = {
                lat: originalPosition.lat + Math.cos(angle) * distance,
                lng: originalPosition.lng + Math.sin(angle) * distance
            };
            
            if (!this.isPositionOverlapped(offsetPosition)) {
                console.log(`[MapManager] Position offset: ${attempt + 1} attempts, angle: ${angles[attempt]}°`);
                return offsetPosition;
            }
        }
        
        // If all offsets overlap, use random offset
        const randomAngle = Math.random() * 2 * Math.PI;
        const randomDistance = this.overlapConfig.offsetDistance * (1 + Math.random());
        
        console.log('[MapManager] Using random position offset');
        return {
            lat: originalPosition.lat + Math.cos(randomAngle) * randomDistance,
            lng: originalPosition.lng + Math.sin(randomAngle) * randomDistance
        };
    }

    /**
     * Register marker position
     */
    registerMarkerPosition(position) {
        const positionKey = `${position.lat.toFixed(6)},${position.lng.toFixed(6)}`;
        const count = this.markerPositions.get(positionKey) || 0;
        this.markerPositions.set(positionKey, count + 1);
    }

    /**
     * Unregister marker position
     */
    unregisterMarkerPosition(position) {
        const positionKey = `${position.lat.toFixed(6)},${position.lng.toFixed(6)}`;
        const count = this.markerPositions.get(positionKey) || 0;
        if (count > 1) {
            this.markerPositions.set(positionKey, count - 1);
        } else {
            this.markerPositions.delete(positionKey);
        }
    }

    /**
     * Add agent marker
     */
    addAgentMarker(agentId, position, type, info = {}, avatarDataUri = null) {
        if (!this.isInitialized) {
            console.warn('[MapManager] Map not initialized');
            return null;
        }

        // Calculate non-overlapping position
        const finalPosition = this.calculateNonOverlappingPosition(position);
        
        // Get icon (which may now be a promise due to avatar processing)
        const iconOrPromise = this.getAgentIcon(type, info.status, avatarDataUri, info.name);
        
        // Create base marker configuration
        const markerConfig = {
            position: finalPosition,
            map: this.map,
            title: info.name || agentId,
            animation: google.maps.Animation.DROP
        };
        
        // Handle both synchronous icons and promise-based icons
        let marker;
        
        // Create the label text for the marker
        const displayName = info.name || agentId;
        const labelText = `[${type}]${displayName}`;
        
        // Configure label style
        const labelConfig = {
            text: labelText,
            color: '#FFFFFF',
            fontWeight: 'bold',
            fontSize: '12px',
            className: 'agent-marker-label'
        };
        
        if (iconOrPromise instanceof Promise) {
            // Create marker with temporary icon first, but with label
            marker = new google.maps.Marker({
                ...markerConfig,
                icon: this.getAgentIcon(type, info.status),  // Use default icon temporarily
                label: labelConfig
            });
            
            // Update icon when promise resolves, keeping the label
            iconOrPromise.then(icon => {
                marker.setIcon(icon);
            });
        } else {
            // Create marker with synchronous icon and label
            marker = new google.maps.Marker({
                ...markerConfig,
                icon: iconOrPromise,
                label: labelConfig
            });
        }

        // Register marker position
        this.registerMarkerPosition(finalPosition);

        // Create info window
        const infoWindow = new google.maps.InfoWindow({
            content: this.createAgentInfoContent(agentId, type, info)
        });

        // 点击事件
        marker.addListener('click', () => {
            this.closeAllInfoWindows();
            infoWindow.open(this.map, marker);
            this.emit('agent:clicked', { agentId, type, info });
        });

        this.agentMarkers.set(agentId, marker);
        this.infoWindows.set(agentId, infoWindow);

        console.log(`[MapManager] Added agent marker: ${agentId} (${type}) at`, finalPosition);
        return marker;
    }

    /**
     * 更新智能体位置
     */
    updateAgentPosition(agentId, newPosition) {
        const marker = this.agentMarkers.get(agentId);
        if (marker) {
            marker.setPosition(newPosition);
            marker.setAnimation(google.maps.Animation.BOUNCE);
            setTimeout(() => marker.setAnimation(null), 1500);
        }
    }

    /**
     * Update agent status
     */
    updateAgentStatus(agentId, status, info = {}, avatarDataUri = null) {
        const marker = this.agentMarkers.get(agentId);
        const infoWindow = this.infoWindows.get(agentId);
        
        if (marker) {
            const agentType = info.type || 'tenant';
            const iconOrPromise = this.getAgentIcon(agentType, status, avatarDataUri, info.name);
            
            // Create or update the label for the marker
            const displayName = info.name || agentId;
            const labelText = `[${agentType}]${displayName}`;
            
            // Update or set the label
            if (!marker.getLabel() || marker.getLabel().text !== labelText) {
                marker.setLabel({
                    text: labelText,
                    color: '#FFFFFF',
                    fontWeight: 'bold',
                    fontSize: '12px',
                    className: 'agent-marker-label'
                });
            }
            
            // Handle both synchronous icons and promise-based icons
            if (iconOrPromise instanceof Promise) {
                iconOrPromise.then(icon => {
                    marker.setIcon(icon);
                });
            } else {
                marker.setIcon(iconOrPromise);
            }
        }
        
        if (infoWindow) {
            infoWindow.setContent(this.createAgentInfoContent(agentId, info.type, { ...info, status }));
        }

        this.emit('agent:status_updated', { agentId, status, info });
    }

    /**
     * Show dialogue bubble above agent
     */
    showDialogueBubble(agentId, message, duration = 5000) {
        const marker = this.agentMarkers.get(agentId);
        if (!marker) return;

        // Create enhanced chat bubble content
        const bubbleContent = `
            <div class="dialogue-bubble">
                <div class="bubble-content">${message}</div>
                <div class="bubble-tail"></div>
            </div>
        `;

        const bubble = new google.maps.InfoWindow({
            content: bubbleContent,
            disableAutoPan: true,
            pixelOffset: new google.maps.Size(0, -50)
        });

        bubble.open(this.map, marker);
        
        // Auto-close after duration
        setTimeout(() => {
            bubble.close();
        }, duration);

        this.emit('dialogue:shown', { agentId, message });
    }

    /**
     * Add property marker
     */
    addPropertyMarker(propertyId, position, info = {}) {
        if (!this.isInitialized) return null;

        // Calculate non-overlapping position
        const finalPosition = this.calculateNonOverlappingPosition(position);

        const marker = new google.maps.Marker({
            position: finalPosition,
            map: this.map,
            title: info.title || `Property ${propertyId}`,
            icon: this.getPropertyIcon(info.status),
            animation: google.maps.Animation.DROP
        });

        // Register marker position
        this.registerMarkerPosition(finalPosition);

        const infoWindow = new google.maps.InfoWindow({
            content: this.createPropertyInfoContent(propertyId, info)
        });

        marker.addListener('click', () => {
            this.closeAllInfoWindows();
            infoWindow.open(this.map, marker);
            this.emit('property:clicked', { propertyId, info });
        });

        this.propertyMarkers.set(propertyId, marker);
        this.infoWindows.set(`property_${propertyId}`, infoWindow);

        console.log(`[MapManager] Added property marker: ${propertyId} at`, finalPosition);
        return marker;
    }

    /**
     * Get agent icon
     */
    getAgentIcon(type, status = 'idle', avatarDataUri = null, name = '') {
        // If we have an avatar and agent info, create a clean avatar icon
        if (avatarDataUri) {
            // Create a canvas for the avatar
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const avatarSize = 48;
            
            // Set canvas size for just the avatar (no label included in the image)
            canvas.width = avatarSize;
            canvas.height = avatarSize;
            
            // Create a new image element for the avatar
            const img = new Image();
            
            // Return a promise that resolves when the image is loaded and processed
            return new Promise((resolve) => {
                img.onload = () => {
                    // Clear canvas
                    ctx.fillStyle = 'transparent';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                    
                    // Draw avatar
                    ctx.drawImage(img, 0, 0, avatarSize, avatarSize);
                    
                    // Create the custom marker icon
                    // We'll add the label separately using Google Maps label feature
                    const displayName = name || type;
                    const labelText = `[${type}]${displayName}`;
                    
                    // Create icon object with just the avatar image
                    resolve({
                        url: canvas.toDataURL(),
                        scaledSize: new google.maps.Size(avatarSize, avatarSize),
                        origin: new google.maps.Point(0, 0),
                        anchor: new google.maps.Point(avatarSize/2, avatarSize), // Bottom center align
                        // Store the label text to use when creating the marker
                        labelText: labelText
                    });
                };
                
                // Set image source to the avatar data URI
                img.src = avatarDataUri;
            });
        }

        // Fallback: use original colored pins
        const baseUrl = 'https://maps.google.com/mapfiles/ms/icons/';
        const colors = {
            tenant: { idle: 'blue', active: 'green', thinking: 'yellow' },
            landlord: { idle: 'red', active: 'orange', thinking: 'purple' }
        };

        const color = colors[type]?.[status] || 'gray';
        
        return {
            url: `${baseUrl}${color}-dot.png`,
            scaledSize: new google.maps.Size(48, 48),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(24, 48)
        };
    }

    /**
     * Get property icon
     */
    getPropertyIcon(status = 'available') {
        const icons = {
            available: '🏠',
            negotiating: '🏡',
            rented: '🏘️'
        };
        
        return {
            url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
                    <text x="24" y="24" text-anchor="middle" dominant-baseline="central" font-size="32">
                        ${icons[status] || '🏠'}
                    </text>
                </svg>
            `)}`,
            scaledSize: new google.maps.Size(48, 48),
            anchor: new google.maps.Point(24, 48) // Bottom center align, consistent with avatars
        };
    }

    /**
     * Create agent info window content
     */
    createAgentInfoContent(agentId, type, info) {
        const typeNames = { tenant: 'Tenant', landlord: 'Landlord' };
        const statusNames = { 
            idle: 'Idle', 
            active: 'Active', 
            thinking: 'Thinking',
            negotiating: 'Negotiating'
        };

        if (type === 'tenant') {
            return `
                <div class="agent-info">
                    <h3>${info.name || agentId}</h3>
                    <p><strong>Type:</strong> ${typeNames[type] || type}</p>
                    <p><strong>Status:</strong> ${statusNames[info.status] || info.status || 'Unknown'}</p>
                    ${info.currentMessage ? `<p><strong>Current:</strong> ${info.currentMessage}</p>` : ''}
                    ${info.budget ? `<p><strong>Budget:</strong> £${info.budget}/month</p>` : ''}
                    ${info.income ? `<p><strong>Annual Income:</strong> £${Math.round(info.income)}</p>` : ''}
                    ${info.preferences ? `<p><strong>Preferences:</strong> ${info.preferences}</p>` : ''}
                    ${info.email ? `<p><strong>Email:</strong> ${info.email}</p>` : ''}
                    ${info.phone ? `<p><strong>Phone:</strong> ${info.phone}</p>` : ''}
                    ${info.hasGuarantor !== undefined ? `<p><strong>Guarantor:</strong> ${info.hasGuarantor ? 'Yes' : 'No'}</p>` : ''}
                    ${info.hasPets !== undefined ? `<p><strong>Pets:</strong> ${info.hasPets ? 'Yes' : 'No'}</p>` : ''}
                    ${info.isSmoker !== undefined ? `<p><strong>Smoker:</strong> ${info.isSmoker ? 'Yes' : 'No'}</p>` : ''}
                </div>
            `;
        } else if (type === 'landlord') {
            return `
                <div class="agent-info">
                    <h3>${info.name || agentId}</h3>
                    <p><strong>Type:</strong> ${typeNames[type] || type}</p>
                    <p><strong>Status:</strong> ${statusNames[info.status] || info.status || 'Unknown'}</p>
                    ${info.currentMessage ? `<p><strong>Current:</strong> ${info.currentMessage}</p>` : ''}
                    ${info.properties ? `<p><strong>Properties:</strong> ${info.properties}</p>` : ''}
                    ${info.propertyTypes ? `<p><strong>Property Types:</strong> ${info.propertyTypes}</p>` : ''}
                    ${info.branchName ? `<p><strong>Branch:</strong> ${info.branchName}</p>` : ''}
                    ${info.phone ? `<p><strong>Phone:</strong> ${info.phone}</p>` : ''}
                    ${info.petFriendly !== undefined ? `<p><strong>Pet Friendly:</strong> ${info.petFriendly ? 'Yes' : 'No'}</p>` : ''}
                    ${info.smokingAllowed !== undefined ? `<p><strong>Smoking Allowed:</strong> ${info.smokingAllowed ? 'Yes' : 'No'}</p>` : ''}
                    ${info.depositWeeks ? `<p><strong>Deposit:</strong> ${info.depositWeeks} weeks</p>` : ''}
                </div>
            `;
        }

        // Default format
        return `
            <div class="agent-info">
                <h3>${info.name || agentId}</h3>
                <p><strong>Type:</strong> ${typeNames[type] || type}</p>
                <p><strong>Status:</strong> ${statusNames[info.status] || info.status || 'Unknown'}</p>
                ${info.currentMessage ? `<p><strong>Current:</strong> ${info.currentMessage}</p>` : ''}
            </div>
        `;
    }

    /**
     * Create property info window content
     */
    createPropertyInfoContent(propertyId, info) {
        return `
            <div class="property-info">
                <h3>${info.title || info.address || `Property ${propertyId}`}</h3>
                <p><strong>Address:</strong> ${info.address || 'Unknown address'}</p>
                <p><strong>Rent:</strong> £${info.price || info.rent || 'Negotiable'}/month</p>
                <p><strong>Bedrooms:</strong> ${info.bedrooms || 'Unknown'}</p>
                <p><strong>Type:</strong> ${info.property_type || info.type || 'Unknown'}</p>
                <p><strong>Status:</strong> ${info.status || 'Available'}</p>
                ${info.landlord_id ? `<p><strong>Landlord ID:</strong> ${info.landlord_id}</p>` : ''}
            </div>
        `;
    }

    /**
     * Close all info windows
     */
    closeAllInfoWindows() {
        this.infoWindows.forEach(infoWindow => {
            infoWindow.close();
        });
    }

    /**
     * Remove agent marker
     */
    removeAgentMarker(agentId) {
        const marker = this.agentMarkers.get(agentId);
        const infoWindow = this.infoWindows.get(agentId);
        
        if (marker) {
            // Unregister position
            this.unregisterMarkerPosition(marker.getPosition().toJSON());
            marker.setMap(null);
            this.agentMarkers.delete(agentId);
        }
        
        if (infoWindow) {
            infoWindow.close();
            this.infoWindows.delete(agentId);
        }
    }

    /**
     * Remove property marker
     */
    removePropertyMarker(propertyId) {
        const marker = this.propertyMarkers.get(propertyId);
        const infoWindow = this.infoWindows.get(`property_${propertyId}`);
        
        if (marker) {
            // Unregister position
            this.unregisterMarkerPosition(marker.getPosition().toJSON());
            marker.setMap(null);
            this.propertyMarkers.delete(propertyId);
        }
        
        if (infoWindow) {
            infoWindow.close();
            this.infoWindows.delete(`property_${propertyId}`);
        }
    }

    /**
     * Clear all markers
     */
    clearAllMarkers() {
        // Clear agent markers
        this.agentMarkers.forEach(marker => {
            this.unregisterMarkerPosition(marker.getPosition().toJSON());
            marker.setMap(null);
        });
        
        // Clear property markers
        this.propertyMarkers.forEach(marker => {
            this.unregisterMarkerPosition(marker.getPosition().toJSON());
            marker.setMap(null);
        });
        
        this.closeAllInfoWindows();
        
        this.agentMarkers.clear();
        this.propertyMarkers.clear();
        this.infoWindows.clear();
        this.markerPositions.clear(); // Clear position cache
    }

    /**
     * Focus on specific position
     */
    focusOn(position, zoom = 15) {
        if (this.map) {
            this.map.setCenter(position);
            this.map.setZoom(zoom);
        }
    }

    /**
     * Event system
     */
    on(event, callback) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, []);
        }
        this.eventListeners.get(event).push(callback);
    }

    emit(event, data) {
        const listeners = this.eventListeners.get(event);
        if (listeners) {
            listeners.forEach(callback => callback(data));
        }
    }

    /**
     * Destroy
     */
    destroy() {
        this.clearAllMarkers();
        this.eventListeners.clear();
        this.map = null;
        this.isInitialized = false;
    }
}

export default MapManager;
