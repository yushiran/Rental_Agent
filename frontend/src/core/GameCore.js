/**
 * GameCore - Agent Sandbox核心管理器
 * 负责协调前端所有系统：场景、网络、状态管理等
 */
class GameCore {
    constructor() {
        this.initialized = false;
        this.config = null;
        this.networkManager = null;
        this.sceneManager = null;
        this.stateManager = null;
        this.agentManager = null;
        
        // 游戏状态
        this.gameState = {
            isRunning: false,
            currentSession: null,
            agents: new Map(),
            properties: new Map(),
            activeNegotiations: new Set()
        };
        
        // 事件监听器
        this.eventListeners = new Map();
    }

    /**
     * 初始化游戏核心
     */
    async initialize() {
        if (this.initialized) return;
        
        try {
            console.log('[GameCore] 初始化开始...');
            
            // 1. 加载配置
            await this.loadConfig();
            
            // 2. 初始化网络管理器
            const NetworkManager = (await import('../network/NetworkManager.js')).default;
            this.networkManager = new NetworkManager();
            await this.networkManager.initialize();
            
            // 3. 初始化状态管理器
            const StateManager = (await import('./StateManager.js')).default;
            this.stateManager = new StateManager(this);
            
            // 4. 初始化Agent管理器
            const AgentManager = (await import('./AgentManager.js')).default;
            this.agentManager = new AgentManager(this);
            
            // 5. 设置事件监听
            this.setupEventListeners();
            
            this.initialized = true;
            console.log('[GameCore] 初始化完成');
            
            this.emit('core:initialized', { success: true });
            
        } catch (error) {
            console.error('[GameCore] 初始化失败:', error);
            this.emit('core:error', { error: error.message });
            throw error;
        }
    }

    /**
     * 加载后端配置
     */
    async loadConfig() {
        try {
            this.config = await this.networkManager?.getConfig() || {
                backend_url: 'http://localhost:8000',
                websocket_url: 'ws://localhost:8000'
            };
            console.log('[GameCore] 配置加载完成:', this.config);
        } catch (error) {
            console.warn('[GameCore] 配置加载失败，使用默认配置:', error);
            this.config = {
                backend_url: 'http://localhost:8000',
                websocket_url: 'ws://localhost:8000'
            };
        }
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 网络事件
        this.networkManager.on('connection:established', (data) => {
            this.emit('system:status', { type: 'network', status: 'connected', data });
        });

        this.networkManager.on('connection:lost', (data) => {
            this.emit('system:status', { type: 'network', status: 'disconnected', data });
        });

        // Agent事件
        this.networkManager.on('agent:started', (data) => {
            this.agentManager.handleAgentStarted(data);
            this.emit('agent:started', data);
        });

        this.networkManager.on('message:sent', (data) => {
            this.agentManager.handleMessageSent(data);
            this.emit('agent:message', data);
        });

        this.networkManager.on('agent:thought', (data) => {
            this.agentManager.handleAgentThought(data);
            this.emit('agent:thought', data);
        });

        this.networkManager.on('negotiation:completed', (data) => {
            this.handleNegotiationCompleted(data);
            this.emit('negotiation:completed', data);
        });
    }

    /**
     * 初始化系统数据
     */
    async initializeSystemData(options = {}) {
        const {
            tenant_count = 3,
            reset_data = false
        } = options;

        try {
            console.log('[GameCore] 初始化系统数据...');
            
            const result = await this.networkManager.request('/initialize', {
                method: 'POST',
                body: JSON.stringify({ tenant_count, reset_data })
            });

            if (result.data) {
                // 更新游戏状态
                this.updateSystemData(result.data);
                
                console.log(`[GameCore] 系统数据初始化完成: ${result.data.tenants_count}个租客, ${result.data.properties_count}个房产`);
                
                this.emit('system:data_loaded', result.data);
                return result.data;
            }
            
        } catch (error) {
            console.error('[GameCore] 系统数据初始化失败:', error);
            this.emit('system:error', { error: error.message });
            throw error;
        }
    }

    /**
     * 更新系统数据
     */
    updateSystemData(data) {
        // 更新租客数据
        if (data.tenants) {
            data.tenants.forEach(tenant => {
                this.gameState.agents.set(tenant.tenant_id, {
                    id: tenant.tenant_id,
                    type: 'tenant',
                    data: tenant,
                    status: 'idle'
                });
            });
        }

        // 更新房东数据
        if (data.landlords) {
            data.landlords.forEach(landlord => {
                this.gameState.agents.set(landlord.landlord_id, {
                    id: landlord.landlord_id,
                    type: 'landlord',
                    data: landlord,
                    status: 'idle'
                });
            });
        }

        // 更新房产数据
        if (data.properties) {
            data.properties.forEach(property => {
                this.gameState.properties.set(property.property_id, property);
            });
        }
    }

    /**
     * 开始协商流程
     */
    async startNegotiation(tenantIds = []) {
        try {
            console.log('[GameCore] 开始协商流程...');
            
            const result = await this.networkManager.request('/start-negotiation', {
                method: 'POST',
                body: JSON.stringify({ tenant_ids: tenantIds })
            });

            if (result.sessions) {
                // 建立WebSocket连接
                for (const session of result.sessions) {
                    await this.networkManager.connectWebSocket(session.session_id);
                    this.gameState.activeNegotiations.add(session.session_id);
                }
                
                this.gameState.isRunning = true;
                console.log(`[GameCore] 协商已启动: ${result.sessions.length}个会话`);
                
                this.emit('negotiation:started', result);
                return result;
            }
            
        } catch (error) {
            console.error('[GameCore] 启动协商失败:', error);
            this.emit('negotiation:error', { error: error.message });
            throw error;
        }
    }

    /**
     * 重置记忆
     */
    async resetMemory() {
        try {
            console.log('[GameCore] 重置记忆...');
            
            await this.networkManager.request('/reset-memory', {
                method: 'POST'
            });
            
            // 清理本地状态
            this.gameState.activeNegotiations.clear();
            this.gameState.isRunning = false;
            this.gameState.currentSession = null;
            
            console.log('[GameCore] 记忆重置完成');
            this.emit('system:memory_reset');
            
        } catch (error) {
            console.error('[GameCore] 重置记忆失败:', error);
            this.emit('system:error', { error: error.message });
            throw error;
        }
    }

    /**
     * 处理协商完成
     */
    handleNegotiationCompleted(data) {
        const sessionId = data.session_id;
        this.gameState.activeNegotiations.delete(sessionId);
        
        if (this.gameState.activeNegotiations.size === 0) {
            this.gameState.isRunning = false;
            console.log('[GameCore] 所有协商已完成');
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

    off(event, callback) {
        if (this.eventListeners.has(event)) {
            const listeners = this.eventListeners.get(event);
            const index = listeners.indexOf(callback);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        if (this.eventListeners.has(event)) {
            this.eventListeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[GameCore] 事件处理器错误 (${event}):`, error);
                }
            });
        }
    }

    /**
     * 获取游戏状态
     */
    getState() {
        return { ...this.gameState };
    }

    /**
     * 获取Agent信息
     */
    getAgent(agentId) {
        return this.gameState.agents.get(agentId);
    }

    /**
     * 获取所有租客
     */
    getTenants() {
        return Array.from(this.gameState.agents.values())
            .filter(agent => agent.type === 'tenant');
    }

    /**
     * 获取所有房东
     */
    getLandlords() {
        return Array.from(this.gameState.agents.values())
            .filter(agent => agent.type === 'landlord');
    }

    /**
     * 销毁游戏核心
     */
    destroy() {
        console.log('[GameCore] 销毁中...');
        
        if (this.networkManager) {
            this.networkManager.destroy();
        }
        
        this.eventListeners.clear();
        this.gameState.agents.clear();
        this.gameState.properties.clear();
        this.gameState.activeNegotiations.clear();
        
        this.initialized = false;
        console.log('[GameCore] 已销毁');
    }
}

export default GameCore;