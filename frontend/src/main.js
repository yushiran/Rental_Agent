import AgentMapController from './maps/AgentMapController.js';
import NetworkManager from './network/NetworkManager.js';

/**
 * RentalAgentApp - 租房智能体应用主类
 * 基于 Google Maps 的多智能体租房协商可视化系统
 */
class RentalAgentApp {
    constructor() {
        this.mapController = null;
        this.networkManager = null;
        this.currentSession = null;
        this.isInitialized = false;
        this.eventListeners = new Map();
        
        // 配置
        this.config = {
            apiKey: '', // Google Maps API Key (可选)
            backendUrl: 'http://localhost:8000',
            mapContainer: 'map'
        };
    }

    /**
     * 初始化应用
     */
    async initialize(config = {}) {
        console.log('[RentalAgentApp] 应用初始化开始...');
        
        try {
            // 合并配置
            this.config = { ...this.config, ...config };
            
            // 初始化网络管理器
            this.networkManager = new NetworkManager();
            await this.networkManager.initialize();
            
            // 初始化地图控制器
            this.mapController = new AgentMapController();
            await this.mapController.initialize(this.config.apiKey, this.config.mapContainer);
            
            // 设置事件监听
            this.setupEventListeners();
            
            // 更新UI状态
            this.updateUI();
            
            this.isInitialized = true;
            console.log('[RentalAgentApp] 应用初始化完成');
            
        } catch (error) {
            console.error('[RentalAgentApp] 初始化失败:', error);
            this.showError('应用初始化失败: ' + error.message);
            throw error;
        }
    }

    /**
     * 设置事件监听
     */
    setupEventListeners() {
        // 网络事件
        this.networkManager.on('connection:established', () => {
            this.updateConnectionStatus(true);
        });
        
        this.networkManager.on('connection:lost', () => {
            this.updateConnectionStatus(false);
        });
        
        // WebSocket 事件
        this.networkManager.on('websocket:message', (data) => {
            this.handleWebSocketMessage(data);
        });
        
        // UI 事件
        this.setupUIEventListeners();
    }

    /**
     * 设置UI事件监听
     */
    setupUIEventListeners() {
        // 初始化系统按钮
        const initBtn = document.getElementById('initialize-system');
        if (initBtn) {
            initBtn.addEventListener('click', () => this.initializeSystem());
        }
        
        // 开始协商按钮
        const startBtn = document.getElementById('start-negotiation');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startNegotiation());
        }
        
        // 重置按钮
        const resetBtn = document.getElementById('reset-session');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetSession());
        }
        
        // 清除日志按钮
        const clearLogsBtn = document.getElementById('clear-logs');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => this.clearLogs());
        }

        // API Key 输入框变化事件
        const apiKeyInput = document.getElementById('api-key-input');
        if (apiKeyInput) {
            apiKeyInput.addEventListener('change', (e) => {
                this.config.apiKey = e.target.value;
                console.log('[RentalAgentApp] API Key 已更新');
            });
        }
    }

    /**
     * 开始协商
     */
    async startNegotiation() {
        if (!this.isInitialized) {
            this.showError('应用未初始化');
            return;
        }

        try {
            this.updateStatus('正在启动协商...');
            this.setButtonLoading('start-negotiation', true);
            
            // 发送开始协商请求
            const response = await this.networkManager.request('/start-session', {
                method: 'POST',
                body: JSON.stringify({
                    tenant_preferences: {
                        budget: 10000,
                        location: '北京市中心',
                        area: '80-120㎡'
                    }
                })
            });
            
            // 从响应中获取第一个会话ID（兼容后端格式）
            this.currentSession = response.session_ids && response.session_ids.length > 0 
                ? response.session_ids[0] 
                : `session_${Date.now()}`;
            
            // 连接WebSocket
            await this.networkManager.connectWebSocket(this.currentSession);
            
            // 添加智能体到地图
            this.addInitialAgents();
            
            this.updateStatus('协商已开始');
            this.addLog('info', `协商会话开始: ${this.currentSession}`);
            
        } catch (error) {
            console.error('[RentalAgentApp] 启动协商失败:', error);
            this.showError('启动协商失败: ' + error.message);
            this.updateStatus('协商启动失败');
        } finally {
            this.setButtonLoading('start-negotiation', false);
        }
    }

    /**
     * 重置会话
     */
    async resetSession() {
        try {
            this.updateStatus('正在重置会话...');
            
            // 重置后端状态
            await this.networkManager.request('/reset-memory', {
                method: 'POST'
            });
            
            // 清除地图上的智能体
            this.mapController.clearAllAgents();
            
            // 清除当前会话
            this.currentSession = null;
            
            // 更新UI
            this.updateStatus('会话已重置');
            this.addLog('info', '会话已重置');
            this.updateUI();
            
        } catch (error) {
            console.error('[RentalAgentApp] 重置会话失败:', error);
            this.showError('重置会话失败: ' + error.message);
        }
    }

    /**
     * 添加初始智能体
     */
    addInitialAgents() {
        // 获取租客数量设置
        const tenantCount = parseInt(document.getElementById('tenant-count')?.value || 3);
        
        // 添加租客
        const tenantNames = ['张三', '李四', '王五', '赵六', '钱七'];
        for (let i = 0; i < tenantCount; i++) {
            this.mapController.addAgent(`tenant_${i + 1}`, 'tenant', {
                name: `${tenantNames[i] || '租客' + (i + 1)}(租客)`,
                budget: 8000 + i * 2000,
                preferences: i % 2 === 0 ? '市中心, 交通便利' : '安静环境, 学区房'
            });
        }
        
        // 添加多个房东
        const landlords = [
            { id: 'landlord_1', name: '刘老板(房东)', properties: ['东城区公寓'] },
            { id: 'landlord_2', name: '陈老板(房东)', properties: ['西城区住宅'] },
            { id: 'landlord_3', name: '杨老板(房东)', properties: ['朝阳区复式'] },
            { id: 'landlord_4', name: '周老板(房东)', properties: ['海淀区学区房'] },
            { id: 'landlord_5', name: '吴老板(房东)', properties: ['丰台区新房'] }
        ];
        
        landlords.forEach(landlord => {
            this.mapController.addAgent(landlord.id, 'landlord', {
                name: landlord.name,
                properties: landlord.properties
            });
        });
        
        this.addLog('info', `已添加 ${tenantCount} 个租客和 ${landlords.length} 个房东到地图`);
    }

    /**
     * 处理WebSocket消息
     */
    handleWebSocketMessage(data) {
        const { sessionId, event, payload } = data;
        
        console.log(`[RentalAgentApp] 收到事件: ${event}`, payload);
        
        switch (event) {
            case 'agent_started':
                this.handleAgentStarted(payload);
                break;
            case 'message_sent':
                this.handleMessageSent(payload);
                break;
            case 'agent_thought':
                this.handleAgentThought(payload);
                break;
            case 'negotiation_update':
                this.handleNegotiationUpdate(payload);
                break;
            case 'agreement_reached':
                this.handleAgreementReached(payload);
                break;
            case 'dialogue_ended':
                this.handleDialogueEnded(payload);
                break;
            default:
                console.log(`[RentalAgentApp] 未知事件: ${event}`);
        }
    }

    /**
     * 处理智能体开始事件
     */
    handleAgentStarted(payload) {
        const { agent_id, agent_type } = payload;
        this.mapController.updateAgentStatus(agent_id, 'active');
        this.addLog('info', `${agent_type} ${agent_id} 开始行动`);
    }

    /**
     * 处理消息发送事件
     */
    handleMessageSent(payload) {
        const { agent_id, message, agent_type } = payload;
        
        // 在地图上显示对话气泡
        this.mapController.showAgentDialogue(agent_id, message);
        
        // 添加到日志
        this.addLog('message', `${agent_type} ${agent_id}: ${message}`);
    }

    /**
     * 处理智能体思考事件
     */
    handleAgentThought(payload) {
        const { agent_id, thought } = payload;
        this.mapController.updateAgentStatus(agent_id, 'thinking');
        this.addLog('thought', `${agent_id} 思考: ${thought}`);
    }

    /**
     * 处理协商更新事件
     */
    handleNegotiationUpdate(payload) {
        const { progress, details } = payload;
        this.updateStatus(`协商进行中 (${progress}%)`);
        
        if (details) {
            this.addLog('info', `协商进展: ${details}`);
        }
    }

    /**
     * 处理达成协议事件
     */
    handleAgreementReached(payload) {
        const { tenant_id, landlord_id, agreement_details } = payload;
        
        this.mapController.updateAgentStatus(tenant_id, 'active');
        this.mapController.updateAgentStatus(landlord_id, 'active');
        
        this.updateStatus('协商成功！');
        this.addLog('success', '协议达成！');
        this.addLog('info', `协议详情: ${JSON.stringify(agreement_details, null, 2)}`);
        
        this.showSuccess('协商成功！双方已达成协议');
    }

    /**
     * 处理对话结束事件
     */
    handleDialogueEnded(payload) {
        const { reason, final_status } = payload;
        
        this.updateStatus('协商结束');
        this.addLog('info', `协商结束原因: ${reason}`);
        
        if (final_status === 'failed') {
            this.showError('协商失败');
        }
    }

    /**
     * 更新连接状态
     */
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            statusEl.textContent = connected ? '已连接' : '未连接';
            statusEl.className = `status ${connected ? 'connected' : 'disconnected'}`;
        }
    }

    /**
     * 更新状态显示
     */
    updateStatus(status) {
        const statusEl = document.getElementById('current-status');
        if (statusEl) {
            statusEl.textContent = status;
        }
    }

    /**
     * 更新UI状态
     */
    updateUI() {
        const hasSession = !!this.currentSession;
        
        // 更新按钮状态
        const startBtn = document.getElementById('start-negotiation');
        const resetBtn = document.getElementById('reset-session');
        const initBtn = document.getElementById('initialize-system');
        
        if (startBtn) {
            startBtn.disabled = hasSession;
            startBtn.textContent = hasSession ? '协商进行中...' : '开始协商';
        }
        
        if (resetBtn) {
            resetBtn.disabled = !hasSession;
        }
        
        if (initBtn) {
            initBtn.disabled = hasSession;
        }
    }

    /**
     * 设置按钮加载状态
     */
    setButtonLoading(buttonId, loading) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = loading;
            if (loading) {
                button.textContent = button.dataset.loadingText || '加载中...';
            } else {
                button.textContent = button.dataset.originalText || button.textContent;
            }
        }
    }

    /**
     * 添加日志
     */
    addLog(type, message) {
        const logsContainer = document.getElementById('logs-container');
        if (!logsContainer) return;
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        
        const timestamp = new Date().toLocaleTimeString();
        logEntry.innerHTML = `
            <span class="timestamp">[${timestamp}]</span>
            <span class="message">${message}</span>
        `;
        
        logsContainer.appendChild(logEntry);
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    /**
     * 清除日志
     */
    clearLogs() {
        const logsContainer = document.getElementById('logs-container');
        if (logsContainer) {
            logsContainer.innerHTML = '';
        }
    }

    /**
     * 显示错误消息
     */
    showError(message) {
        this.showNotification(message, 'error');
    }

    /**
     * 显示成功消息
     */
    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    /**
     * 显示通知
     */
    showNotification(message, type = 'info') {
        // 简单的通知实现
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    /**
     * 初始化系统
     */
    async initializeSystem() {
        try {
            this.updateStatus('正在初始化系统...');
            this.setButtonLoading('initialize-system', true);
            
            // 获取参数
            const tenantCount = document.getElementById('tenant-count')?.value || 3;
            const resetData = document.getElementById('reset-data')?.checked || false;
            
            // 发送初始化请求
            const response = await this.networkManager.request('/initialize', {
                method: 'POST',
                body: JSON.stringify({
                    tenant_count: parseInt(tenantCount),
                    reset_data: resetData
                })
            });
            
            // 检查响应是否包含data字段，说明初始化成功
            if (response.data && response.status === 'initialized') {
                this.updateStatus(`系统初始化成功: ${response.data.tenants_count}个租客, ${response.data.landlords_count}个房东`);
                this.addLog('success', `系统初始化完成 - 租客:${response.data.tenants_count}, 房东:${response.data.landlords_count}`);
                
                // 启用开始协商按钮
                const startBtn = document.getElementById('start-negotiation');
                if (startBtn) {
                    startBtn.disabled = false;
                }
                
                // 添加从后端获取的真实数据到地图
                this.addRealDataToMap(response.data);
                
            } else {
                throw new Error(response.message || '初始化失败');
            }
            
        } catch (error) {
            console.error('[RentalAgentApp] 系统初始化失败:', error);
            this.showError('系统初始化失败: ' + error.message);
            this.updateStatus('初始化失败');
        } finally {
            this.setButtonLoading('initialize-system', false);
        }
    }

    /**
     * 将从后端获取的真实数据添加到地图
     */
    addRealDataToMap(data) {
        if (!this.mapController || !this.mapController.isInitialized) {
            console.warn('[RentalAgentApp] 地图控制器未初始化');
            return;
        }

        // 清除现有的智能体标记
        this.mapController.clearAllAgents();

        // 添加租客
        if (data.tenants && Array.isArray(data.tenants)) {
            data.tenants.forEach((tenant, index) => {
                this.mapController.addAgent(tenant.tenant_id, 'tenant', {
                    name: `${tenant.name || '租客' + (index + 1)}(租客)`,
                    budget: tenant.budget || 8000,
                    preferences: tenant.preferences || '寻找合适房源'
                });
            });
        }

        // 添加房东
        if (data.landlords && Array.isArray(data.landlords)) {
            data.landlords.forEach((landlord, index) => {
                this.mapController.addAgent(landlord.landlord_id, 'landlord', {
                    name: `${landlord.name || '房东' + (index + 1)}(房东)`,
                    properties: landlord.properties || ['待分配房产']
                });
            });
        }

        // 添加房产标记（使用map_data）
        if (data.map_data && Array.isArray(data.map_data)) {
            data.map_data.forEach(property => {
                this.mapController.addPropertyFromData(property);
            });
        }

        this.addLog('info', `已添加 ${data.tenants_count} 个租客、${data.landlords_count} 个房东和 ${data.properties_count} 个房产到地图`);
    }

    /**
     * 销毁应用
     */
    destroy() {
        if (this.mapController) {
            this.mapController.destroy();
        }
        
        if (this.networkManager) {
            // 网络管理器清理
        }
        
        this.eventListeners.clear();
        this.isInitialized = false;
    }
}

// 创建全局应用实例
const app = new RentalAgentApp();

// 应用启动
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // 可以在这里配置 Google Maps API Key
        const config = {
            apiKey: 'AIzaSyDSflr_l6w6IZIhqcFO2J_0WJacRga2UiU', // 如果有API Key请取消注释并填入
            backendUrl: 'http://localhost:8000'
        };
        
        await app.initialize(config);
        console.log('[App] 应用启动完成');
    } catch (error) {
        console.error('[App] 应用启动失败:', error);
        // 显示用户友好的错误信息
        const statusEl = document.getElementById('current-status');
        if (statusEl) {
            statusEl.textContent = '应用启动失败';
        }
    }
});

export default app;
