/**
 * FallbackMapManager - 后备地图管理器
 * 当Google Maps不可用时使用的简单画布实现
 */
class FallbackMapManager {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.agents = new Map();
        this.properties = new Map();
        this.isInitialized = false;
        this.eventListeners = new Map();
        
        // 画布配置
        this.config = {
            width: 800,
            height: 500,
            backgroundColor: '#e3f2fd',
            gridColor: '#bbdefb'
        };
        
        // 北京市区坐标转换
        this.mapBounds = {
            north: 39.97,
            south: 39.85,
            east: 116.50,
            west: 116.30
        };
    }

    /**
     * 初始化画布地图
     */
    async initialize(containerId) {
        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`找不到容器元素: ${containerId}`);
        }

        // 创建画布
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.config.width;
        this.canvas.height = this.config.height;
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.border = '1px solid #ccc';
        this.canvas.style.borderRadius = '8px';
        
        container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');
        
        // 设置点击事件
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
        
        this.isInitialized = true;
        this.drawMap();
        
        console.log('[FallbackMapManager] 画布地图初始化完成');
        this.emit('map:initialized', { canvas: this.canvas });
    }

    /**
     * 绘制地图背景
     */
    drawMap() {
        if (!this.ctx) return;
        
        // 清除画布
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 绘制背景
        this.ctx.fillStyle = this.config.backgroundColor;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 绘制网格
        this.drawGrid();
        
        // 绘制地标
        this.drawLandmarks();
        
        // 绘制所有智能体和房产
        this.agents.forEach(agent => this.drawAgent(agent));
        this.properties.forEach(property => this.drawProperty(property));
    }

    /**
     * 绘制网格
     */
    drawGrid() {
        this.ctx.strokeStyle = this.config.gridColor;
        this.ctx.lineWidth = 1;
        
        // 垂直线
        for (let x = 0; x <= this.canvas.width; x += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }
        
        // 水平线
        for (let y = 0; y <= this.canvas.height; y += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();
        }
    }

    /**
     * 绘制地标
     */
    drawLandmarks() {
        const landmarks = [
            { name: '天安门', x: 400, y: 250 },
            { name: '王府井', x: 450, y: 200 },
            { name: '西单', x: 350, y: 220 },
            { name: '鼓楼', x: 420, y: 150 }
        ];
        
        this.ctx.fillStyle = '#666';
        this.ctx.font = '12px Arial';
        
        landmarks.forEach(landmark => {
            // 绘制地标点
            this.ctx.fillStyle = '#ff5722';
            this.ctx.beginPath();
            this.ctx.arc(landmark.x, landmark.y, 4, 0, 2 * Math.PI);
            this.ctx.fill();
            
            // 绘制标签
            this.ctx.fillStyle = '#666';
            this.ctx.fillText(landmark.name, landmark.x + 8, landmark.y + 4);
        });
    }

    /**
     * 坐标转换：经纬度到画布坐标
     */
    latLngToCanvasCoords(lat, lng) {
        const x = ((lng - this.mapBounds.west) / (this.mapBounds.east - this.mapBounds.west)) * this.canvas.width;
        const y = ((this.mapBounds.north - lat) / (this.mapBounds.north - this.mapBounds.south)) * this.canvas.height;
        return { x: Math.max(20, Math.min(this.canvas.width - 20, x)), y: Math.max(20, Math.min(this.canvas.height - 20, y)) };
    }

    /**
     * 添加智能体标记
     */
    addAgentMarker(agentId, position, type, info = {}) {
        if (!this.isInitialized) return null;
        
        const canvasCoords = this.latLngToCanvasCoords(position.lat, position.lng);
        
        const agent = {
            id: agentId,
            type: type,
            x: canvasCoords.x,
            y: canvasCoords.y,
            info: info,
            status: 'idle'
        };
        
        this.agents.set(agentId, agent);
        this.drawMap();
        
        console.log(`[FallbackMapManager] 添加智能体: ${agentId} (${type})`);
        return agent;
    }

    /**
     * 绘制智能体
     */
    drawAgent(agent) {
        if (!this.ctx) return;
        
        const colors = {
            tenant: { idle: '#2196F3', active: '#4CAF50', thinking: '#FF9800' },
            landlord: { idle: '#f44336', active: '#FF5722', thinking: '#9C27B0' }
        };
        
        const color = colors[agent.type]?.[agent.status] || '#666';
        
        // 绘制智能体圆圈
        this.ctx.fillStyle = color;
        this.ctx.beginPath();
        this.ctx.arc(agent.x, agent.y, 12, 0, 2 * Math.PI);
        this.ctx.fill();
        
        // 绘制边框
        this.ctx.strokeStyle = '#fff';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        // 绘制类型标识
        this.ctx.fillStyle = '#fff';
        this.ctx.font = 'bold 10px Arial';
        this.ctx.textAlign = 'center';
        const symbol = agent.type === 'tenant' ? 'T' : 'L';
        this.ctx.fillText(symbol, agent.x, agent.y + 3);
        
        // 绘制名称
        this.ctx.fillStyle = '#333';
        this.ctx.font = '11px Arial';
        this.ctx.fillText(agent.info.name || agent.id, agent.x, agent.y - 20);
    }

    /**
     * 添加房产标记
     */
    addPropertyMarker(propertyId, position, info = {}) {
        if (!this.isInitialized) return null;
        
        const canvasCoords = this.latLngToCanvasCoords(position.lat, position.lng);
        
        const property = {
            id: propertyId,
            x: canvasCoords.x,
            y: canvasCoords.y,
            info: info,
            status: 'available'
        };
        
        this.properties.set(propertyId, property);
        this.drawMap();
        
        return property;
    }

    /**
     * 绘制房产
     */
    drawProperty(property) {
        if (!this.ctx) return;
        
        const colors = {
            available: '#4CAF50',
            negotiating: '#FF9800',
            rented: '#f44336'
        };
        
        const color = colors[property.status] || '#666';
        
        // 绘制房产方块
        this.ctx.fillStyle = color;
        this.ctx.fillRect(property.x - 8, property.y - 8, 16, 16);
        
        // 绘制边框
        this.ctx.strokeStyle = '#fff';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(property.x - 8, property.y - 8, 16, 16);
        
        // 绘制房屋符号
        this.ctx.fillStyle = '#fff';
        this.ctx.font = 'bold 12px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('🏠', property.x, property.y + 4);
    }

    /**
     * 更新智能体状态
     */
    updateAgentStatus(agentId, status, info = {}) {
        const agent = this.agents.get(agentId);
        if (agent) {
            agent.status = status;
            agent.info = { ...agent.info, ...info };
            this.drawMap();
        }
    }

    /**
     * 显示对话气泡
     */
    showDialogueBubble(agentId, message, duration = 5000) {
        const agent = this.agents.get(agentId);
        if (!agent) return;
        
        // 在画布上绘制简单的消息提示
        this.drawMessageBubble(agent.x, agent.y - 30, message);
        
        // 一段时间后清除
        setTimeout(() => {
            this.drawMap();
        }, duration);
    }

    /**
     * 绘制消息气泡
     */
    drawMessageBubble(x, y, message) {
        if (!this.ctx) return;
        
        const maxWidth = 150;
        const padding = 8;
        
        // 计算文本尺寸
        this.ctx.font = '11px Arial';
        const textMetrics = this.ctx.measureText(message);
        const textWidth = Math.min(textMetrics.width, maxWidth);
        const textHeight = 14;
        
        // 绘制气泡背景
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        this.ctx.strokeStyle = '#ccc';
        this.ctx.lineWidth = 1;
        
        const bubbleX = x - textWidth / 2 - padding;
        const bubbleY = y - textHeight - padding;
        const bubbleWidth = textWidth + padding * 2;
        const bubbleHeight = textHeight + padding * 2;
        
        this.ctx.fillRect(bubbleX, bubbleY, bubbleWidth, bubbleHeight);
        this.ctx.strokeRect(bubbleX, bubbleY, bubbleWidth, bubbleHeight);
        
        // 绘制文本
        this.ctx.fillStyle = '#333';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(message, x, y - padding);
    }

    /**
     * 处理画布点击
     */
    handleCanvasClick(event) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (event.clientX - rect.left) * (this.canvas.width / rect.width);
        const y = (event.clientY - rect.top) * (this.canvas.height / rect.height);
        
        // 检查是否点击了智能体
        for (const [agentId, agent] of this.agents) {
            const distance = Math.sqrt((x - agent.x) ** 2 + (y - agent.y) ** 2);
            if (distance <= 15) {
                this.emit('agent:clicked', { agentId, type: agent.type, info: agent.info });
                return;
            }
        }
        
        // 检查是否点击了房产
        for (const [propertyId, property] of this.properties) {
            if (x >= property.x - 10 && x <= property.x + 10 && 
                y >= property.y - 10 && y <= property.y + 10) {
                this.emit('property:clicked', { propertyId, info: property.info });
                return;
            }
        }
    }

    /**
     * 清除所有标记
     */
    clearAllMarkers() {
        this.agents.clear();
        this.properties.clear();
        this.drawMap();
    }

    /**
     * 聚焦到特定位置
     */
    focusOn(position, zoom = 15) {
        // 在简单实现中，只是重新绘制地图
        this.drawMap();
        console.log(`[FallbackMapManager] 聚焦到: ${position.lat}, ${position.lng}`);
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
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
        this.agents.clear();
        this.properties.clear();
        this.eventListeners.clear();
        this.isInitialized = false;
    }
}

export default FallbackMapManager;
