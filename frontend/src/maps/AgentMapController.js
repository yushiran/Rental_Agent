import MapManager from './MapManager.js';
import googleMapsLoader from './GoogleMapsLoader.js';
import AvatarGenerator from '../utils/AvatarGenerator.js';

/**
 * AgentMapController - 智能体地图控制器
 * 专门处理智能体在地图上的可视化和交互
 */
class AgentMapController {
    constructor() {
        this.mapManager = null;
        this.avatarGenerator = new AvatarGenerator();
        this.agents = new Map();
        this.properties = new Map();
        this.negotiationSessions = new Map();
        this.isInitialized = false;
        // 预设位置 (Central London)
        this.agentPositions = [
            { lat: 51.5074, lng: -0.1278 }, // Trafalgar Square
            { lat: 51.5101, lng: -0.1344 }, // Piccadilly Circus
            { lat: 51.5117, lng: -0.1275 }, // Covent Garden
            { lat: 51.5107, lng: -0.1302 }, // Leicester Square
            { lat: 51.5152, lng: -0.1415 }, // Oxford Street
            { lat: 51.5007, lng: -0.1246 }, // Westminster
            { lat: 51.5137, lng: -0.1341 }, // Soho
            { lat: 51.5079, lng: -0.0877 }, // London Bridge
        ];

        this.propertyPositions = [
            { lat: 51.5051, lng: -0.1977, info: { title: 'Kensington Flat', rent: 2500, area: 70 } },
            { lat: 51.5007, lng: -0.1337, info: { title: 'Westminster Apartment', rent: 3200, area: 85 } },
            { lat: 51.5383, lng: -0.1484, info: { title: 'Camden Duplex', rent: 2800, area: 95 } },
            { lat: 51.5137, lng: -0.1341, info: { title: 'Soho Studio', rent: 2200, area: 55 } },
            { lat: 51.5101, lng: -0.1440, info: { title: 'Mayfair Luxury Flat', rent: 4500, area: 110 } },
        ];
    }

    /**
     * 初始化地图控制器
     */
    async initialize(apiKey = '', containerId = 'map') {
        try {
            console.log('[AgentMapController] 尝试加载 Google Maps...');
            
            // 加载 Google Maps API
            if (apiKey) {
                googleMapsLoader.setApiKey(apiKey);
            }
            await googleMapsLoader.load();

            // 检查 Google Maps 是否真正可用
            if (window.google && window.google.maps) {
                // 使用 Google Maps
                this.mapManager = new MapManager();
                await this.mapManager.initialize(containerId);
                console.log('[AgentMapController] 使用 Google Maps');
            } else {
                throw new Error('Google Maps 不可用');
            }

        } catch (error) {
            console.warn('[AgentMapController] Google Maps 初始化失败，使用后备地图:', error);
        }

        // 设置事件监听
        this.setupEventListeners();

        // 不再自动添加初始房产，等待从后端获取真实数据
        this.addInitialProperties();

        this.isInitialized = true;
        console.log('[AgentMapController] 初始化完成');
    }

    /**
     * 设置事件监听
     */
    setupEventListeners() {
        if (!this.mapManager) return;

        this.mapManager.on('agent:clicked', (data) => {
            this.handleAgentClick(data);
        });

        this.mapManager.on('property:clicked', (data) => {
            this.handlePropertyClick(data);
        });
    }

    /**
     * 添加初始房产
     */
    addInitialProperties() {
        this.propertyPositions.forEach((property, index) => {
            const propertyId = `property_${index + 1}`;
            this.mapManager.addPropertyMarker(propertyId, property, property.info);
            this.properties.set(propertyId, {
                position: property,
                ...property.info,
                status: 'available'
            });
        });
    }

    /**
     * 添加智能体
     */
    async addAgent(agentId, type, info = {}, customPosition = null) {
        if (!this.isInitialized) {
            console.warn('[AgentMapController] 控制器未初始化');
            return;
        }

        let position;
        
        // 如果提供了自定义位置，使用自定义位置
        if (customPosition) {
            position = customPosition;
        } else {
            // 否则使用预设位置
            const positionIndex = this.agents.size % this.agentPositions.length;
            position = this.agentPositions[positionIndex];
        }

        // 生成头像
        const avatarDataUri = await this.avatarGenerator.generateAvatar(agentId, type, info.name);

        // 添加到地图
        const marker = this.mapManager.addAgentMarker(agentId, position, type, {
            ...info,
            status: 'idle'
        }, avatarDataUri);

        // 记录智能体信息
        this.agents.set(agentId, {
            type,
            position,
            marker,
            status: 'idle',
            avatarDataUri,
            ...info
        });

        console.log(`[AgentMapController] 添加智能体: ${agentId} (${type}) at ${position.lat}, ${position.lng}`);
        return marker;
    }

    /**
     * 更新智能体状态
     */
    updateAgentStatus(agentId, status, message = '') {
        const agent = this.agents.get(agentId);
        if (!agent) {
            console.warn(`[AgentMapController] 智能体不存在: ${agentId}`);
            return;
        }

        agent.status = status;
        agent.currentMessage = message;

        this.mapManager.updateAgentStatus(agentId, status, {
            type: agent.type,
            status,
            currentMessage: message,
            ...agent
        }, agent.avatarDataUri);

        console.log(`[AgentMapController] 更新智能体状态: ${agentId} -> ${status}`);
    }

    /**
     * 显示智能体对话
     */
    showAgentDialogue(agentId, message, duration = 5000) {
        if (this.agents.has(agentId)) {
            this.mapManager.showDialogueBubble(agentId, message, duration);
            console.log(`[AgentMapController] 显示对话: ${agentId} -> ${message}`);
        }
    }

    /**
     * 开始协商会话
     */
    startNegotiation(sessionId, tenantId, landlordId, propertyId) {
        // 更新智能体状态
        this.updateAgentStatus(tenantId, 'negotiating');
        this.updateAgentStatus(landlordId, 'negotiating');

        // 更新房产状态
        if (this.properties.has(propertyId)) {
            const property = this.properties.get(propertyId);
            property.status = 'negotiating';
        }

        // 记录协商会话
        this.negotiationSessions.set(sessionId, {
            tenantId,
            landlordId,
            propertyId,
            startTime: new Date(),
            status: 'active'
        });

        // 聚焦到相关位置
        const tenant = this.agents.get(tenantId);
        if (tenant) {
            this.mapManager.focusOn(tenant.position, 14);
        }

        console.log(`[AgentMapController] 开始协商: ${sessionId}`);
    }

    /**
     * 结束协商会话
     */
    endNegotiation(sessionId, result = 'completed') {
        const session = this.negotiationSessions.get(sessionId);
        if (!session) return;

        const { tenantId, landlordId, propertyId } = session;

        // 更新智能体状态
        const finalStatus = result === 'agreement' ? 'active' : 'idle';
        this.updateAgentStatus(tenantId, finalStatus);
        this.updateAgentStatus(landlordId, finalStatus);

        // 更新房产状态
        if (this.properties.has(propertyId)) {
            const property = this.properties.get(propertyId);
            property.status = result === 'agreement' ? 'rented' : 'available';
        }

        // 更新会话状态
        session.status = result;
        session.endTime = new Date();

        console.log(`[AgentMapController] 结束协商: ${sessionId} -> ${result}`);
    }

    /**
     * 移动智能体到指定位置
     */
    moveAgent(agentId, newPosition) {
        const agent = this.agents.get(agentId);
        if (agent) {
            agent.position = newPosition;
            this.mapManager.updateAgentPosition(agentId, newPosition);
        }
    }

    /**
     * 从后端数据添加房产标记
     */
    addPropertyFromData(propertyData) {
        if (!this.isInitialized) {
            console.warn('[AgentMapController] 控制器未初始化');
            return;
        }

        const position = {
            lat: propertyData.latitude || 51.5074,
            lng: propertyData.longitude || -0.1278
        };

        const info = {
            title: propertyData.address || 'Unknown Address',
            rent: propertyData.price || 0,
            area: `${propertyData.bedrooms || 1} 卧室`,
            type: propertyData.property_type || 'Unknown',
            landlord_id: propertyData.landlord_id
        };

        this.mapManager.addPropertyMarker(propertyData.id, position, info);
        this.properties.set(propertyData.id, {
            position,
            ...info,
            status: 'available'
        });

        console.log(`[AgentMapController] 添加房产: ${propertyData.id} at ${propertyData.address}`);
    }

    /**
     * 处理智能体点击
     */
    handleAgentClick(data) {
        const { agentId, type, info } = data;
        console.log(`[AgentMapController] 智能体被点击: ${agentId}`);
        
        // 可以在这里添加点击处理逻辑
        // 例如显示详细信息、开始交互等
    }

    /**
     * 处理房产点击
     */
    handlePropertyClick(data) {
        const { propertyId, info } = data;
        console.log(`[AgentMapController] 房产被点击: ${propertyId}`);
        
        // 可以在这里添加房产点击处理逻辑
    }

    /**
     * 获取智能体信息
     */
    getAgent(agentId) {
        return this.agents.get(agentId);
    }

    /**
     * 获取所有智能体
     */
    getAllAgents() {
        return Array.from(this.agents.entries()).map(([id, agent]) => ({
            id,
            ...agent
        }));
    }

    /**
     * 清除所有智能体
     */
    clearAllAgents() {
        this.agents.clear();
        this.negotiationSessions.clear();
        this.properties.clear(); // 也清除房产，准备接收新数据
        this.avatarGenerator.clearCache(); // 清除头像缓存
        if (this.mapManager) {
            this.mapManager.clearAllMarkers();
        }
    }

    /**
     * 销毁控制器
     */
    destroy() {
        if (this.mapManager) {
            this.mapManager.destroy();
            this.mapManager = null;
        }
        
        this.agents.clear();
        this.properties.clear();
        this.negotiationSessions.clear();
        this.isInitialized = false;
    }
}

export default AgentMapController;
