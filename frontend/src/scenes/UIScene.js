import Phaser from 'phaser';

/**
 * UIScene - 用户界面场景
 * 管理控制面板、消息历史和用户交互
 */
class UIScene extends Phaser.Scene {
    constructor() {
        super({ key: 'UIScene' });
        
        // UI状态
        this.panelVisible = true;
        this.messageHistory = [];
        this.maxMessages = 10;
        
        // UI元素
        this.controlPanel = null;
        this.messagePanel = null;
        this.statusPanel = null;
        this.buttons = new Map();
    }

    /**
     * 创建UI场景
     */
    create() {
        console.log('[UIScene] 创建UI场景');
        
        // 创建控制面板
        this.createControlPanel();
        
        // 创建消息面板
        this.createMessagePanel();
        
        // 创建状态面板
        this.createStatusPanel();
        
        // 设置事件监听
        this.setupEventListeners();
    }

    /**
     * 创建控制面板
     */
    createControlPanel() {
        // 控制面板背景
        this.controlPanel = this.add.container(0, 0);
        
        const panelBg = this.add.rectangle(150, 50, 280, 80, 0x2c3e50, 0.9);
        panelBg.setStrokeStyle(2, 0x34495e);
        this.controlPanel.add(panelBg);
        
        // 标题
        const title = this.add.text(150, 20, '控制面板', {
            fontSize: '16px',
            fontFamily: 'Arial',
            fill: '#ecf0f1',
            stroke: '#2c3e50',
            strokeThickness: 1
        }).setOrigin(0.5);
        this.controlPanel.add(title);
        
        // 按钮配置
        const buttonConfigs = [
            { key: 'initialize', text: '初始化', x: 50, y: 50, width: 70, color: 0x3498db },
            { key: 'start', text: '开始协商', x: 130, y: 50, width: 70, color: 0x27ae60 },
            { key: 'reset', text: '重置', x: 210, y: 50, width: 70, color: 0xe74c3c },
            { key: 'toggle', text: '隐藏面板', x: 150, y: 75, width: 80, color: 0x95a5a6 }
        ];
        
        // 创建按钮
        buttonConfigs.forEach(config => {
            this.createButton(config);
        });
    }

    /**
     * 创建按钮
     */
    createButton(config) {
        const button = this.add.container(config.x, config.y);
        
        // 按钮背景
        const bg = this.add.rectangle(0, 0, config.width, 20, config.color);
        bg.setStrokeStyle(1, 0x2c3e50);
        bg.setInteractive();
        
        // 按钮文本
        const text = this.add.text(0, 0, config.text, {
            fontSize: '12px',
            fontFamily: 'Arial',
            fill: '#ffffff'
        }).setOrigin(0.5);
        
        button.add([bg, text]);
        this.controlPanel.add(button);
        
        // 按钮交互
        bg.on('pointerdown', () => this.handleButtonClick(config.key));
        bg.on('pointerover', () => bg.setFillStyle(this.lightenColor(config.color)));
        bg.on('pointerout', () => bg.setFillStyle(config.color));
        
        // 存储按钮引用
        this.buttons.set(config.key, { button, bg, text, config });
    }

    /**
     * 创建消息面板
     */
    createMessagePanel() {
        this.messagePanel = this.add.container(600, 0);
        
        // 消息面板背景
        const panelBg = this.add.rectangle(0, 150, 200, 280, 0x34495e, 0.9);
        panelBg.setStrokeStyle(2, 0x2c3e50);
        this.messagePanel.add(panelBg);
        
        // 标题
        const title = this.add.text(0, 20, '消息历史', {
            fontSize: '14px',
            fontFamily: 'Arial',
            fill: '#ecf0f1'
        }).setOrigin(0.5);
        this.messagePanel.add(title);
        
        // 消息容器
        this.messageContainer = this.add.container(0, 50);
        this.messagePanel.add(this.messageContainer);
        
        // 清空按钮
        const clearButton = this.add.text(0, 270, '清空', {
            fontSize: '10px',
            fontFamily: 'Arial',
            fill: '#e74c3c',
            backgroundColor: '#2c3e50',
            padding: { x: 8, y: 4 }
        }).setOrigin(0.5);
        clearButton.setInteractive();
        clearButton.on('pointerdown', () => this.clearMessageHistory());
        this.messagePanel.add(clearButton);
    }

    /**
     * 创建状态面板
     */
    createStatusPanel() {
        this.statusPanel = this.add.container(20, 520);
        
        // 状态面板背景
        const panelBg = this.add.rectangle(200, 0, 380, 60, 0x2c3e50, 0.8);
        panelBg.setStrokeStyle(1, 0x34495e);
        this.statusPanel.add(panelBg);
        
        // 网络状态
        this.networkStatus = this.add.text(30, -15, '网络: 未连接', {
            fontSize: '12px',
            fill: '#e74c3c'
        });
        this.statusPanel.add(this.networkStatus);
        
        // 系统状态
        this.systemStatus = this.add.text(30, 0, '系统: 未初始化', {
            fontSize: '12px',
            fill: '#f39c12'
        });
        this.statusPanel.add(this.systemStatus);
        
        // 协商状态
        this.negotiationStatus = this.add.text(30, 15, '协商: 未开始', {
            fontSize: '12px',
            fill: '#95a5a6'
        });
        this.statusPanel.add(this.negotiationStatus);
        
        // Agent统计
        this.agentStats = this.add.text(200, -8, '租客: 0 | 房东: 0 | 活跃协商: 0', {
            fontSize: '11px',
            fill: '#bdc3c7'
        });
        this.statusPanel.add(this.agentStats);
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 监听MainScene事件
        const mainScene = this.scene.get('MainScene');
        if (mainScene && mainScene.gameCore) {
            this.listenToGameCore(mainScene.gameCore);
        } else {
            // 延迟监听
            this.time.delayedCall(1000, () => {
                const mainScene = this.scene.get('MainScene');
                if (mainScene?.gameCore) {
                    this.listenToGameCore(mainScene.gameCore);
                }
            });
        }
    }

    /**
     * 监听GameCore事件
     */
    listenToGameCore(gameCore) {
        // 系统状态事件
        gameCore.on('system:status', (data) => {
            this.updateNetworkStatus(data.status);
        });

        gameCore.on('system:data_loaded', (data) => {
            this.updateSystemStatus('已初始化');
            this.updateAgentStats(data);
        });

        gameCore.on('system:error', (data) => {
            this.updateSystemStatus('错误');
            this.addMessage('系统', data.error, 'error');
        });

        // Agent事件
        gameCore.on('agent:message', (data) => {
            this.addMessage(data.agent_id, data.content, 'message');
        });

        gameCore.on('agent:thought', (data) => {
            this.addMessage(data.agent_id, data.content, 'thought');
        });

        // 协商事件
        gameCore.on('negotiation:started', (data) => {
            this.updateNegotiationStatus('进行中');
            this.addMessage('系统', `协商已开始: ${data.sessions.length}个会话`, 'system');
        });

        gameCore.on('negotiation:completed', (data) => {
            const result = data.result === 'agreement' ? '成功' : '失败';
            this.addMessage('系统', `协商${result}: ${data.tenant_id} & ${data.landlord_id}`, 'system');
        });
    }

    /**
     * 处理按钮点击
     */
    handleButtonClick(buttonKey) {
        console.log(`[UIScene] 按钮点击: ${buttonKey}`);
        
        switch (buttonKey) {
            case 'initialize':
                this.handleInitializeClick();
                break;
            case 'start':
                this.handleStartClick();
                break;
            case 'reset':
                this.handleResetClick();
                break;
            case 'toggle':
                this.togglePanelVisibility();
                break;
        }
    }

    /**
     * 处理初始化按钮
     */
    handleInitializeClick() {
        this.events.emit('initialize-system', {
            tenant_count: 3,
            reset_data: false
        });
        this.updateSystemStatus('初始化中...');
    }

    /**
     * 处理开始按钮
     */
    handleStartClick() {
        this.events.emit('start-negotiation', []);
        this.updateNegotiationStatus('启动中...');
    }

    /**
     * 处理重置按钮
     */
    handleResetClick() {
        this.events.emit('reset-memory');
        this.updateSystemStatus('重置中...');
        this.updateNegotiationStatus('未开始');
        this.clearMessageHistory();
    }

    /**
     * 切换面板可见性
     */
    togglePanelVisibility() {
        this.panelVisible = !this.panelVisible;
        
        if (this.panelVisible) {
            this.controlPanel.setAlpha(1);
            this.messagePanel.setAlpha(1);
            this.buttons.get('toggle').text.setText('隐藏面板');
        } else {
            this.controlPanel.setAlpha(0.3);
            this.messagePanel.setAlpha(0.3);
            this.buttons.get('toggle').text.setText('显示面板');
        }
    }

    /**
     * 添加消息到历史
     */
    addMessage(sender, content, type = 'message') {
        const message = {
            sender,
            content,
            type,
            timestamp: Date.now()
        };
        
        this.messageHistory.push(message);
        
        // 限制消息数量
        if (this.messageHistory.length > this.maxMessages) {
            this.messageHistory.shift();
        }
        
        this.updateMessageDisplay();
    }

    /**
     * 更新消息显示
     */
    updateMessageDisplay() {
        // 清除现有消息
        this.messageContainer.removeAll(true);
        
        // 显示最新消息
        this.messageHistory.forEach((message, index) => {
            const y = index * 20 - 100;
            const color = this.getMessageColor(message.type);
            
            const text = this.add.text(-90, y, `${message.sender}: ${message.content}`, {
                fontSize: '9px',
                fontFamily: 'Arial',
                fill: color,
                wordWrap: { width: 180 }
            });
            
            this.messageContainer.add(text);
        });
    }

    /**
     * 获取消息颜色
     */
    getMessageColor(type) {
        const colors = {
            message: '#ecf0f1',
            thought: '#95a5a6',
            system: '#3498db',
            error: '#e74c3c'
        };
        return colors[type] || '#ecf0f1';
    }

    /**
     * 清空消息历史
     */
    clearMessageHistory() {
        this.messageHistory = [];
        this.updateMessageDisplay();
    }

    /**
     * 更新网络状态
     */
    updateNetworkStatus(status) {
        const color = status === 'connected' ? '#27ae60' : '#e74c3c';
        const text = status === 'connected' ? '已连接' : '未连接';
        
        this.networkStatus.setText(`网络: ${text}`);
        this.networkStatus.setFill(color);
    }

    /**
     * 更新系统状态
     */
    updateSystemStatus(status) {
        const colorMap = {
            '未初始化': '#95a5a6',
            '初始化中...': '#f39c12',
            '已初始化': '#27ae60',
            '重置中...': '#f39c12',
            '错误': '#e74c3c'
        };
        
        this.systemStatus.setText(`系统: ${status}`);
        this.systemStatus.setFill(colorMap[status] || '#ecf0f1');
    }

    /**
     * 更新协商状态
     */
    updateNegotiationStatus(status) {
        const colorMap = {
            '未开始': '#95a5a6',
            '启动中...': '#f39c12',
            '进行中': '#27ae60',
            '已完成': '#3498db',
            '失败': '#e74c3c'
        };
        
        this.negotiationStatus.setText(`协商: ${status}`);
        this.negotiationStatus.setFill(colorMap[status] || '#ecf0f1');
    }

    /**
     * 更新Agent统计
     */
    updateAgentStats(data) {
        const tenantCount = data.tenants_count || 0;
        const landlordCount = data.landlords_count || 0;
        const activeNegotiations = 0; // 从GameCore获取
        
        this.agentStats.setText(`租客: ${tenantCount} | 房东: ${landlordCount} | 活跃协商: ${activeNegotiations}`);
    }

    /**
     * 颜色工具函数
     */
    lightenColor(color) {
        // 简单的颜色加亮函数
        const r = (color >> 16) & 0xFF;
        const g = (color >> 8) & 0xFF;
        const b = color & 0xFF;
        
        return ((Math.min(255, r + 30) << 16) + 
                (Math.min(255, g + 30) << 8) + 
                Math.min(255, b + 30));
    }

    /**
     * 场景更新
     */
    update() {
        // 可以添加UI动画或状态更新
    }

    /**
     * 场景销毁
     */
    destroy() {
        console.log('[UIScene] UI场景销毁');
        this.buttons.clear();
        this.messageHistory = [];
    }
}

export default UIScene;
