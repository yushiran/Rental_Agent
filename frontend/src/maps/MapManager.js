/**
 * MapManager - Google Maps 管理器
 * 负责地图初始化、标记管理和交互处理
 */
class MapManager {
    constructor() {
        this.map = null;
        this.agentMarkers = new Map();
        this.propertyMarkers = new Map();
        this.infoWindows = new Map();
        this.isInitialized = false;
        this.eventListeners = new Map();
        
        // 地图配置
        this.config = {
            center: { lat: 51.5074, lng: -0.1278 }, // London city center
            zoom: 13,
            styles: this.getMapStyles()
        };
    }

    /**
     * 初始化Google Maps
     */
    async initialize(containerId) {
        if (!window.google || !window.google.maps) {
            throw new Error('Google Maps API 未加载');
        }

        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`找不到容器元素: ${containerId}`);
        }

        this.map = new google.maps.Map(container, this.config);
        this.isInitialized = true;
        
        console.log('[MapManager] Google Maps 初始化完成');
        this.emit('map:initialized', { map: this.map });
    }

    /**
     * 获取地图样式
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
     * 添加智能体标记
     */
    addAgentMarker(agentId, position, type, info = {}, avatarDataUri = null) {
        if (!this.isInitialized) {
            console.warn('[MapManager] 地图未初始化');
            return null;
        }

        const marker = new google.maps.Marker({
            position: position,
            map: this.map,
            title: info.name || agentId,
            icon: this.getAgentIcon(type, info.status, avatarDataUri),
            animation: google.maps.Animation.DROP
        });

        // 创建信息窗口
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

        console.log(`[MapManager] 添加智能体标记: ${agentId} (${type})`);
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

        const marker = new google.maps.Marker({
            position: position,
            map: this.map,
            title: info.title || `房产 ${propertyId}`,
            icon: this.getPropertyIcon(info.status),
            animation: google.maps.Animation.DROP
        });

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
            scaledSize: new google.maps.Size(32, 32),
            origin: new google.maps.Point(0, 0),
            anchor: new google.maps.Point(16, 32)
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
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
                    <text x="12" y="12" text-anchor="middle" dominant-baseline="central" font-size="16">
                        ${icons[status] || '🏠'}
                    </text>
                </svg>
            `)}`,
            scaledSize: new google.maps.Size(24, 24),
            anchor: new google.maps.Point(12, 12)
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

        return `
            <div class="agent-info">
                <h3>${info.name || agentId}</h3>
                <p><strong>类型:</strong> ${typeNames[type] || type}</p>
                <p><strong>状态:</strong> ${statusNames[info.status] || info.status || '未知'}</p>
                ${info.currentMessage ? `<p><strong>当前:</strong> ${info.currentMessage}</p>` : ''}
                ${info.budget ? `<p><strong>预算:</strong> ¥${info.budget}</p>` : ''}
                ${info.preferences ? `<p><strong>偏好:</strong> ${info.preferences}</p>` : ''}
            </div>
        `;
    }

    /**
     * 创建房产信息内容
     */
    createPropertyInfoContent(propertyId, info) {
        return `
            <div class="property-info">
                <h3>${info.title || `房产 ${propertyId}`}</h3>
                <p><strong>地址:</strong> ${info.address || '未知地址'}</p>
                <p><strong>租金:</strong> ¥${info.rent || '面议'}/月</p>
                <p><strong>面积:</strong> ${info.area || '未知'}㎡</p>
                <p><strong>状态:</strong> ${info.status || '可租'}</p>
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
            marker.setMap(null);
            this.agentMarkers.delete(agentId);
        }
        
        if (infoWindow) {
            infoWindow.close();
            this.infoWindows.delete(agentId);
        }
    }

    /**
     * 清除所有标记
     */
    clearAllMarkers() {
        this.agentMarkers.forEach(marker => marker.setMap(null));
        this.propertyMarkers.forEach(marker => marker.setMap(null));
        this.closeAllInfoWindows();
        
        this.agentMarkers.clear();
        this.propertyMarkers.clear();
        this.infoWindows.clear();
    }

    /**
     * 聚焦到特定位置
     */
    focusOn(position, zoom = 15) {
        if (this.map) {
            this.map.setCenter(position);
            this.map.setZoom(zoom);
        }
    }

    /**
     * 事件系统
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
     * 销毁
     */
    destroy() {
        this.clearAllMarkers();
        this.eventListeners.clear();
        this.map = null;
        this.isInitialized = false;
    }
}

export default MapManager;
