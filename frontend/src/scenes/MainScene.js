import Phaser from 'phaser';
import GameCore from '../core/GameCore.js';
import TenantAgent from '../objects/TenantAgent.js';
import LandlordAgent from '../objects/LandlordAgent.js';

/**
 * MainScene - 主要游戏场景
 * 负责Agent Sandbox的可视化展示和交互
 */
class MainScene extends Phaser.Scene {
    constructor() {
        super({ key: 'MainScene' });
        
        // 游戏核心
        this.gameCore = null;
        
        // Agent集合
        this.tenantAgents = new Map();
        this.landlordAgents = new Map();
        
        // 场景状态
        this.initialized = false;
        this.simulationRunning = false;
        
        // 背景元素
        this.background = null;
        this.cityscape = null;
    }

    /**
     * 场景初始化
     */
    async create() {
        console.log('[MainScene] 场景初始化开始...');
        
        // 创建背景
        this.createBackground();
        
        // 初始化游戏核心
        await this.initializeGameCore();
        
        // 设置事件监听
        this.setupEventListeners();
        
        this.initialized = true;
        console.log('[MainScene] 场景初始化完成');
    }

    /**
     * 创建背景
     */
    createBackground() {
        // 渐变背景
        this.background = this.add.rectangle(400, 300, 800, 600, 0x87CEEB);
        
        // 创建简单的城市天际线
        this.createCityscape();
        
        // 添加标题
        this.add.text(400, 50, 'Agent Sandbox - 租房协商模拟', {
            fontSize: '24px',
            fontFamily: 'Arial',
            fill: '#2c3e50',
            stroke: '#ffffff',
            strokeThickness: 2
        }).setOrigin(0.5);
        
        // 添加状态指示器
        this.statusText = this.add.text(50, 550, '状态: 等待初始化', {
            fontSize: '14px',
            fill: '#34495e',
            backgroundColor: '#ecf0f1',
            padding: { x: 10, y: 5 }
        });
    }

    /**
     * 创建城市景观
     */
    createCityscape() {
        const buildings = [];
        const colors = [0x7f8c8d, 0x95a5a6, 0xbdc3c7];
        
        for (let i = 0; i < 10; i++) {
            const width = 60 + Math.random() * 40;
            const height = 80 + Math.random() * 120;
            const x = i * 80 + 40;
            const y = 600 - height / 2;
            
            const building = this.add.rectangle(
                x, y, width, height, 
                colors[Math.floor(Math.random() * colors.length)]
            );
            building.setAlpha(0.8);
            buildings.push(building);
            
            // 添加窗户
            this.createBuildingWindows(x, y, width, height);
        }
        
        this.cityscape = buildings;
    }

    /**
     * 创建建筑物窗户
     */
    createBuildingWindows(buildingX, buildingY, buildingWidth, buildingHeight) {
        const windowSize = 8;
        const windowSpacing = 15;
        const cols = Math.floor(buildingWidth / windowSpacing) - 1;
        const rows = Math.floor(buildingHeight / windowSpacing) - 2;
        
        for (let row = 0; row < rows; row++) {
            for (let col = 0; col < cols; col++) {
                if (Math.random() > 0.3) { // 70%的概率有窗户
                    const x = buildingX - buildingWidth/2 + windowSpacing + col * windowSpacing;
                    const y = buildingY - buildingHeight/2 + windowSpacing + row * windowSpacing;
                    
                    this.add.rectangle(x, y, windowSize, windowSize, 0xf39c12).setAlpha(0.8);
                }
            }
        }
    }

    /**
     * 初始化游戏核心
     */
    async initializeGameCore() {
        try {
            this.gameCore = new GameCore();
            await this.gameCore.initialize();
            
            this.updateStatus('游戏核心已初始化');
            
        } catch (error) {
            console.error('[MainScene] 游戏核心初始化失败:', error);
            this.updateStatus('初始化失败: ' + error.message);
        }
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        if (!this.gameCore) return;
        
        // 系统事件
        this.gameCore.on('core:initialized', () => {
            this.updateStatus('系统已准备就绪');
        });

        this.gameCore.on('system:data_loaded', (data) => {
            this.handleSystemDataLoaded(data);
        });

        this.gameCore.on('system:error', (data) => {
            this.updateStatus('错误: ' + data.error);
        });

        // Agent事件
        this.gameCore.on('agent:started', (data) => {
            this.handleAgentStarted(data);
        });

        this.gameCore.on('agent:message', (data) => {
            this.handleAgentMessage(data);
        });

        this.gameCore.on('agent:thought', (data) => {
            this.handleAgentThought(data);
        });

        this.gameCore.on('negotiation:started', (data) => {
            this.handleNegotiationStarted(data);
        });

        this.gameCore.on('negotiation:completed', (data) => {
            this.handleNegotiationCompleted(data);
        });

        // UI事件
        this.gameCore.on('ui:speech_bubble', (bubble) => {
            this.showAgentSpeechBubble(bubble);
        });

        this.gameCore.on('ui:thought_bubble', (bubble) => {
            this.showAgentThoughtBubble(bubble);
        });

        // 场景事件监听
        this.scene.get('UIScene')?.events.on('initialize-system', this.initializeSystem.bind(this));
        this.scene.get('UIScene')?.events.on('start-negotiation', this.startNegotiation.bind(this));
        this.scene.get('UIScene')?.events.on('reset-memory', this.resetMemory.bind(this));
    }

    /**
     * 处理系统数据加载
     */
    handleSystemDataLoaded(data) {
        console.log('[MainScene] 处理系统数据加载');
        
        // 清除现有Agent
        this.clearAllAgents();
        
        // 创建租客Agent
        if (data.tenants) {
            data.tenants.forEach((tenant, index) => {
                this.createTenantAgent(tenant, index);
            });
        }
        
        // 创建房东Agent
        if (data.landlords) {
            data.landlords.forEach((landlord, index) => {
                this.createLandlordAgent(landlord, index);
            });
        }
        
        this.updateStatus(`系统已加载: ${data.tenants_count || 0}个租客, ${data.landlords_count || 0}个房东`);
    }

    /**
     * 创建租客Agent
     */
    createTenantAgent(tenantData, index) {
        const position = this.getTenantPosition(index);
        tenantData.location = position;
        
        const tenantAgent = new TenantAgent(tenantData.tenant_id, tenantData, this);
        tenantAgent.setPosition(position.x, position.y);
        
        this.tenantAgents.set(tenantData.tenant_id, tenantAgent);
        
        // 添加点击交互
        tenantAgent.sprite.setInteractive();
        tenantAgent.sprite.on('pointerdown', () => {
            tenantAgent.showBudgetInfo();
        });
    }

    /**
     * 创建房东Agent
     */
    createLandlordAgent(landlordData, index) {
        const position = this.getLandlordPosition(index);
        landlordData.location = position;
        
        const landlordAgent = new LandlordAgent(landlordData.landlord_id, landlordData, this);
        landlordAgent.setPosition(position.x, position.y);
        
        this.landlordAgents.set(landlordData.landlord_id, landlordAgent);
        
        // 添加点击交互
        landlordAgent.sprite.setInteractive();
        landlordAgent.sprite.on('pointerdown', () => {
            landlordAgent.showPropertyInfo();
        });
    }

    /**
     * 获取租客位置
     */
    getTenantPosition(index) {
        const startX = 100;
        const startY = 200;
        const spacing = 100;
        
        return {
            x: startX + (index % 3) * spacing,
            y: startY + Math.floor(index / 3) * spacing
        };
    }

    /**
     * 获取房东位置
     */
    getLandlordPosition(index) {
        const startX = 500;
        const startY = 200;
        const spacing = 100;
        
        return {
            x: startX + (index % 3) * spacing,
            y: startY + Math.floor(index / 3) * spacing
        };
    }

    /**
     * 处理Agent开始事件
     */
    handleAgentStarted(data) {
        const agent = this.getAgentById(data.agent_id);
        if (agent) {
            if (agent instanceof TenantAgent) {
                agent.startSearching();
            } else if (agent instanceof LandlordAgent) {
                agent.contactedByTenant(data.tenant_id || 'unknown');
            }
        }
    }

    /**
     * 处理Agent消息事件
     */
    handleAgentMessage(data) {
        const agent = this.getAgentById(data.agent_id);
        if (agent) {
            agent.showSpeechBubble(data.content, 3000);
            agent.playAnimation('talking', agent.getEmotionFromMessage?.(data.content) || 'neutral');
        }
    }

    /**
     * 处理Agent思考事件
     */
    handleAgentThought(data) {
        const agent = this.getAgentById(data.agent_id);
        if (agent) {
            agent.showThoughtBubble(data.content, 2000);
            agent.playAnimation('thinking', 'confused');
        }
    }

    /**
     * 处理协商开始事件
     */
    handleNegotiationStarted(data) {
        this.simulationRunning = true;
        this.updateStatus('协商已开始');
        
        if (data.sessions) {
            data.sessions.forEach(session => {
                const tenant = this.tenantAgents.get(session.tenant_id);
                const landlord = this.landlordAgents.get(session.landlord_id);
                
                if (tenant && landlord) {
                    tenant.foundLandlord(session.landlord_id);
                    landlord.contactedByTenant(session.tenant_id);
                    
                    // 创建连接线
                    this.createConnectionLine(tenant, landlord, session.session_id);
                }
            });
        }
    }

    /**
     * 处理协商完成事件
     */
    handleNegotiationCompleted(data) {
        const { session_id, result, tenant_id, landlord_id } = data;
        
        const tenant = this.tenantAgents.get(tenant_id);
        const landlord = this.landlordAgents.get(landlord_id);
        
        if (tenant && landlord) {
            if (result === 'agreement') {
                tenant.negotiationSuccess(data);
                landlord.negotiationSuccess(data);
                this.updateStatus(`协商成功: ${tenant_id} 与 ${landlord_id}`);
            } else {
                tenant.negotiationFailed(result);
                landlord.negotiationFailed(result);
                this.updateStatus(`协商失败: ${result}`);
            }
        }
        
        // 移除连接线
        this.removeConnectionLine(session_id);
        
        // 检查是否所有协商都已完成
        if (this.gameCore.getState().activeNegotiations.size === 0) {
            this.simulationRunning = false;
            this.updateStatus('所有协商已完成');
        }
    }

    /**
     * 创建连接线
     */
    createConnectionLine(tenant, landlord, sessionId) {
        const line = this.add.line(
            0, 0,
            tenant.position.x, tenant.position.y,
            landlord.position.x, landlord.position.y,
            0x34495e, 0.5
        );
        line.setLineWidth(2);
        line.setDepth(-1);
        
        // 存储连接线
        if (!this.connectionLines) {
            this.connectionLines = new Map();
        }
        this.connectionLines.set(sessionId, line);
    }

    /**
     * 移除连接线
     */
    removeConnectionLine(sessionId) {
        if (this.connectionLines && this.connectionLines.has(sessionId)) {
            const line = this.connectionLines.get(sessionId);
            line.destroy();
            this.connectionLines.delete(sessionId);
        }
    }

    /**
     * 显示Agent对话气泡
     */
    showAgentSpeechBubble(bubble) {
        const agent = this.getAgentById(bubble.agentId);
        if (agent) {
            agent.showSpeechBubble(bubble.content, bubble.duration);
        }
    }

    /**
     * 显示Agent思考气泡
     */
    showAgentThoughtBubble(bubble) {
        const agent = this.getAgentById(bubble.agentId);
        if (agent) {
            agent.showThoughtBubble(bubble.content, bubble.duration);
        }
    }

    /**
     * 根据ID获取Agent
     */
    getAgentById(agentId) {
        return this.tenantAgents.get(agentId) || this.landlordAgents.get(agentId);
    }

    /**
     * 初始化系统
     */
    async initializeSystem(options = {}) {
        if (!this.gameCore) {
            this.updateStatus('游戏核心未初始化');
            return;
        }
        
        try {
            this.updateStatus('正在初始化系统...');
            await this.gameCore.initializeSystemData(options);
        } catch (error) {
            console.error('[MainScene] 初始化系统失败:', error);
            this.updateStatus('系统初始化失败: ' + error.message);
        }
    }

    /**
     * 开始协商
     */
    async startNegotiation(tenantIds = []) {
        if (!this.gameCore) {
            this.updateStatus('游戏核心未初始化');
            return;
        }
        
        try {
            this.updateStatus('正在启动协商...');
            await this.gameCore.startNegotiation(tenantIds);
        } catch (error) {
            console.error('[MainScene] 启动协商失败:', error);
            this.updateStatus('启动协商失败: ' + error.message);
        }
    }

    /**
     * 重置记忆
     */
    async resetMemory() {
        if (!this.gameCore) {
            this.updateStatus('游戏核心未初始化');
            return;
        }
        
        try {
            this.updateStatus('正在重置记忆...');
            await this.gameCore.resetMemory();
            
            // 清除所有Agent
            this.clearAllAgents();
            
            this.updateStatus('记忆已重置');
        } catch (error) {
            console.error('[MainScene] 重置记忆失败:', error);
            this.updateStatus('重置记忆失败: ' + error.message);
        }
    }

    /**
     * 清除所有Agent
     */
    clearAllAgents() {
        // 清除租客Agent
        for (const agent of this.tenantAgents.values()) {
            agent.destroy();
        }
        this.tenantAgents.clear();
        
        // 清除房东Agent
        for (const agent of this.landlordAgents.values()) {
            agent.destroy();
        }
        this.landlordAgents.clear();
        
        // 清除连接线
        if (this.connectionLines) {
            for (const line of this.connectionLines.values()) {
                line.destroy();
            }
            this.connectionLines.clear();
        }
    }

    /**
     * 更新状态文本
     */
    updateStatus(status) {
        if (this.statusText) {
            this.statusText.setText('状态: ' + status);
        }
        console.log('[MainScene] 状态更新:', status);
    }

    /**
     * 场景更新
     */
    update() {
        // 这里可以添加持续的更新逻辑
        // 例如动画更新、状态检查等
    }

    /**
     * 场景销毁
     */
    destroy() {
        console.log('[MainScene] 场景销毁');
        
        this.clearAllAgents();
        
        if (this.gameCore) {
            this.gameCore.destroy();
        }
    }
}

export default MainScene;
