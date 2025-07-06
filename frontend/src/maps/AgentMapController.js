import MapManager from './MapManager.js';
import googleMapsLoader from './GoogleMapsLoader.js';
import AvatarGenerator from '../utils/AvatarGenerator.js';

/**
 * AgentMapController - Agent Map Controller
 * Specialized in handling agent visualization and interaction on the map
 */
class AgentMapController {
    constructor() {
        this.mapManager = null;
        this.avatarGenerator = new AvatarGenerator();
        this.agents = new Map();
        this.properties = new Map();
        this.negotiationSessions = new Map();
        this.isInitialized = false;
        // Preset positions (Central London)
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
     * Initialize map controller
     */
    async initialize(apiKey = '', containerId = 'map') {
        try {
            console.log('[AgentMapController] Attempting to load Google Maps...');
            
            // Load Google Maps API
            if (apiKey) {
                googleMapsLoader.setApiKey(apiKey);
            }
            await googleMapsLoader.load();

            // Check if Google Maps is really available
            if (window.google && window.google.maps) {
                // Use Google Maps
                this.mapManager = new MapManager();
                await this.mapManager.initialize(containerId);
                console.log('[AgentMapController] Using Google Maps');
            } else {
                throw new Error('Google Maps not available');
            }

        } catch (error) {
            console.warn('[AgentMapController] Google Maps initialization failed, using fallback map:', error);
        }

        // Set up event listeners
        this.setupEventListeners();

        // No longer automatically add initial properties, wait for real data from backend
        this.addInitialProperties();

        this.isInitialized = true;
        console.log('[AgentMapController] Initialization completed');
    }

    /**
     * Set up event listeners
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
     * Add initial properties
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
     * Add agent
     */
    async addAgent(agentId, type, info = {}, customPosition = null) {
        if (!this.isInitialized) {
            console.warn('[AgentMapController] Controller not initialized');
            return;
        }

        let position;
        
        // If custom position is provided, use it
        if (customPosition) {
            position = customPosition;
        } else {
            // Otherwise use preset position
            const positionIndex = this.agents.size % this.agentPositions.length;
            position = this.agentPositions[positionIndex];
        }

        // Generate avatar
        const avatarDataUri = await this.avatarGenerator.generateAvatar(agentId, type, info.name);

        // Add to map
        const marker = this.mapManager.addAgentMarker(agentId, position, type, {
            ...info,
            status: 'idle'
        }, avatarDataUri);

        // Record agent information
        this.agents.set(agentId, {
            type,
            position,
            marker,
            status: 'idle',
            avatarDataUri,
            ...info
        });

        console.log(`[AgentMapController] Added agent: ${agentId} (${type}) at ${position.lat}, ${position.lng}`);
        return marker;
    }

    /**
     * Update agent status
     */
    updateAgentStatus(agentId, status, message = '') {
        const agent = this.agents.get(agentId);
        if (!agent) {
            console.warn(`[AgentMapController] Agent does not exist: ${agentId}`);
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

        console.log(`[AgentMapController] Updated agent status: ${agentId} -> ${status}`);
    }

    /**
     * Show agent dialogue
     */
    showAgentDialogue(agentId, message, duration = 5000) {
        if (this.agents.has(agentId)) {
            this.mapManager.showDialogueBubble(agentId, message, duration);
        }
    }

    /**
     * Start negotiation session
     */
    startNegotiation(sessionId, tenantId, landlordId, propertyId) {
        // Update agent statuses
        this.updateAgentStatus(tenantId, 'negotiating');
        this.updateAgentStatus(landlordId, 'negotiating');

        // Update property status
        if (this.properties.has(propertyId)) {
            const property = this.properties.get(propertyId);
            property.status = 'negotiating';
        }

        // Record negotiation session
        this.negotiationSessions.set(sessionId, {
            tenantId,
            landlordId,
            propertyId,
            startTime: new Date(),
            status: 'active'
        });

        // Focus on relevant location
        const tenant = this.agents.get(tenantId);
        if (tenant) {
            this.mapManager.focusOn(tenant.position, 14);
        }

        console.log(`[AgentMapController] Started negotiation: ${sessionId}`);
    }

    /**
     * End negotiation session
     */
    endNegotiation(sessionId, result = 'completed') {
        const session = this.negotiationSessions.get(sessionId);
        if (!session) return;

        const { tenantId, landlordId, propertyId } = session;

        // Update agent statuses
        const finalStatus = result === 'agreement' ? 'active' : 'idle';
        this.updateAgentStatus(tenantId, finalStatus);
        this.updateAgentStatus(landlordId, finalStatus);

        // Update property status
        if (this.properties.has(propertyId)) {
            const property = this.properties.get(propertyId);
            property.status = result === 'agreement' ? 'rented' : 'available';
        }

        // Update session status
        session.status = result;
        session.endTime = new Date();

        console.log(`[AgentMapController] Ended negotiation: ${sessionId} -> ${result}`);
    }

    /**
     * Move agent to specific location
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
     * Get agent information
     */
    getAgent(agentId) {
        return this.agents.get(agentId);
    }

    /**
     * Get agent by name
     */
    getAgentByName(name) {
        for (const [agentId, agent] of this.agents) {
            if (agent.name === name) {
                return { id: agentId, ...agent };
            }
        }
        return null;
    }

    /**
     * Get all agents
     */
    getAllAgents() {
        return Array.from(this.agents.entries()).map(([id, agent]) => ({
            id,
            ...agent
        }));
    }

    /**
     * Clear all agents
     */
    clearAllAgents() {
        this.agents.clear();
        this.negotiationSessions.clear();
        this.properties.clear(); // Also clear properties, prepare to receive new data
        this.avatarGenerator.clearCache(); // Clear avatar cache
        if (this.mapManager) {
            this.mapManager.clearAllMarkers();
        }
    }

    /**
     * Destroy controller
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
