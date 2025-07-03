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
     * 注册标记位置
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
        
        const marker = new google.maps.Marker({
            position: finalPosition,
            map: this.map,
            title: info.name || agentId,
            icon: this.getAgentIcon(type, info.status, avatarDataUri),
            animation: google.maps.Animation.DROP
        });

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

        console.log(`[MapManager] 添加智能体标记: ${agentId} (${type}) at`, finalPosition);
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
     * 更新智能体状态
     */
    updateAgentStatus(agentId, status, info = {}, avatarDataUri = null) {
        const marker = this.agentMarkers.get(agentId);
        const infoWindow = this.infoWindows.get(agentId);
        
        if (marker) {
            const agentType = info.type || 'tenant';
            marker.setIcon(this.getAgentIcon(agentType, status, avatarDataUri));
        }
        
        if (infoWindow) {
            infoWindow.setContent(this.createAgentInfoContent(agentId, info.type, { ...info, status }));
        }

        this.emit('agent:status_updated', { agentId, status, info });
    }

    /**
     * 显示对话气泡
     */
    showDialogueBubble(agentId, message, duration = 5000) {
        const marker = this.agentMarkers.get(agentId);
        if (!marker) return;

        const bubble = new google.maps.InfoWindow({
            content: `<div class="dialogue-bubble">${message}</div>`,
            disableAutoPan: true,
            pixelOffset: new google.maps.Size(0, -40)
        });

        bubble.open(this.map, marker);
        
        // 自动关闭
        setTimeout(() => {
            bubble.close();
        }, duration);

        this.emit('dialogue:shown', { agentId, message });
    }

    /**
     * 添加房产标记
     */
    addPropertyMarker(propertyId, position, info = {}) {
        if (!this.isInitialized) return null;

        // 计算避免重叠的位置
        const finalPosition = this.calculateNonOverlappingPosition(position);

        const marker = new google.maps.Marker({
            position: finalPosition,
            map: this.map,
            title: info.title || `房产 ${propertyId}`,
            icon: this.getPropertyIcon(info.status),
            animation: google.maps.Animation.DROP
        });

        // 注册标记位置
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

        console.log(`[MapManager] 添加房产标记: ${propertyId} at`, finalPosition);
        return marker;
    }

    /**
     * 获取智能体图标
     */
    getAgentIcon(type, status = 'idle', avatarDataUri = null) {
        // 如果有头像，使用头像
        if (avatarDataUri) {
            return {
                url: avatarDataUri,
                scaledSize: new google.maps.Size(48, 48),
                origin: new google.maps.Point(0, 0),
                anchor: new google.maps.Point(24, 48) // 底部中心对齐
            };
        }

        // 后备方案：使用原来的彩色图钉
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
     * 获取房产图标
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
            anchor: new google.maps.Point(24, 48) // 底部中心对齐，与头像一致
        };
    }

    /**
     * 创建智能体信息内容
     */
    createAgentInfoContent(agentId, type, info) {
        const typeNames = { tenant: '租客', landlord: '房东' };
        const statusNames = { 
            idle: '空闲', 
            active: '活跃', 
            thinking: '思考中',
            negotiating: '协商中'
        };

        if (type === 'tenant') {
            return `
                <div class="agent-info">
                    <h3>${info.name || agentId}</h3>
                    <p><strong>类型:</strong> ${typeNames[type] || type}</p>
                    <p><strong>状态:</strong> ${statusNames[info.status] || info.status || '未知'}</p>
                    ${info.currentMessage ? `<p><strong>当前:</strong> ${info.currentMessage}</p>` : ''}
                    ${info.budget ? `<p><strong>预算:</strong> £${info.budget}/月</p>` : ''}
                    ${info.income ? `<p><strong>年收入:</strong> £${Math.round(info.income)}</p>` : ''}
                    ${info.preferences ? `<p><strong>偏好:</strong> ${info.preferences}</p>` : ''}
                    ${info.email ? `<p><strong>邮箱:</strong> ${info.email}</p>` : ''}
                    ${info.phone ? `<p><strong>电话:</strong> ${info.phone}</p>` : ''}
                    ${info.hasGuarantor !== undefined ? `<p><strong>担保人:</strong> ${info.hasGuarantor ? '有' : '无'}</p>` : ''}
                    ${info.hasPets !== undefined ? `<p><strong>宠物:</strong> ${info.hasPets ? '有' : '无'}</p>` : ''}
                    ${info.isSmoker !== undefined ? `<p><strong>吸烟:</strong> ${info.isSmoker ? '是' : '否'}</p>` : ''}
                </div>
            `;
        } else if (type === 'landlord') {
            return `
                <div class="agent-info">
                    <h3>${info.name || agentId}</h3>
                    <p><strong>类型:</strong> ${typeNames[type] || type}</p>
                    <p><strong>状态:</strong> ${statusNames[info.status] || info.status || '未知'}</p>
                    ${info.currentMessage ? `<p><strong>当前:</strong> ${info.currentMessage}</p>` : ''}
                    ${info.properties ? `<p><strong>房产:</strong> ${info.properties}</p>` : ''}
                    ${info.propertyTypes ? `<p><strong>房产类型:</strong> ${info.propertyTypes}</p>` : ''}
                    ${info.branchName ? `<p><strong>分支:</strong> ${info.branchName}</p>` : ''}
                    ${info.phone ? `<p><strong>电话:</strong> ${info.phone}</p>` : ''}
                    ${info.petFriendly !== undefined ? `<p><strong>允许宠物:</strong> ${info.petFriendly ? '是' : '否'}</p>` : ''}
                    ${info.smokingAllowed !== undefined ? `<p><strong>允许吸烟:</strong> ${info.smokingAllowed ? '是' : '否'}</p>` : ''}
                    ${info.depositWeeks ? `<p><strong>押金:</strong> ${info.depositWeeks}周</p>` : ''}
                </div>
            `;
        }

        // 默认格式
        return `
            <div class="agent-info">
                <h3>${info.name || agentId}</h3>
                <p><strong>类型:</strong> ${typeNames[type] || type}</p>
                <p><strong>状态:</strong> ${statusNames[info.status] || info.status || '未知'}</p>
                ${info.currentMessage ? `<p><strong>当前:</strong> ${info.currentMessage}</p>` : ''}
            </div>
        `;
    }

    /**
     * 创建房产信息内容
     */
    createPropertyInfoContent(propertyId, info) {
        return `
            <div class="property-info">
                <h3>${info.title || info.address || `房产 ${propertyId}`}</h3>
                <p><strong>地址:</strong> ${info.address || '未知地址'}</p>
                <p><strong>租金:</strong> £${info.price || info.rent || '面议'}/月</p>
                <p><strong>卧室:</strong> ${info.bedrooms || '未知'}间</p>
                <p><strong>类型:</strong> ${info.property_type || info.type || '未知'}</p>
                <p><strong>状态:</strong> ${info.status || '可租'}</p>
                ${info.landlord_id ? `<p><strong>房东ID:</strong> ${info.landlord_id}</p>` : ''}
            </div>
        `;
    }

    /**
     * 关闭所有信息窗口
     */
    closeAllInfoWindows() {
        this.infoWindows.forEach(infoWindow => {
            infoWindow.close();
        });
    }

    /**
     * 移除智能体标记
     */
    removeAgentMarker(agentId) {
        const marker = this.agentMarkers.get(agentId);
        const infoWindow = this.infoWindows.get(agentId);
        
        if (marker) {
            // 取消注册位置
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
