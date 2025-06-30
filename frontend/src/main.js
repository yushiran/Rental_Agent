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
            
            // 手动检查一次连接状态
            this.updateConnectionStatus(this.networkManager.connectionStatus === 'connected');
            
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
            
            // // 添加智能体到地图
            // this.addInitialAgents();
            
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
            // 使用 data 属性中的文本，如果没有则使用默认值
            const connectedText = statusEl.dataset.connectedText || '已连接';
            const disconnectedText = statusEl.dataset.disconnectedText || '未连接';
            
            statusEl.textContent = connected ? connectedText : disconnectedText;
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
                this.updateStatus(`系统初始化成功: ${response.data.tenants_count}个租客, ${response.data.landlords_count}个房东， ${response.data.properties_count}个房产`);
                this.addLog('success', `系统初始化完成 - 租客:${response.data.tenants_count}, 房东:${response.data.landlords_count}, 房产:${response.data.properties_count}`);
                
                // 启用开始协商按钮
                const startBtn = document.getElementById('start-negotiation');
                if (startBtn) {
                    startBtn.disabled = false;
                }
                
                // 添加从后端获取的真实数据到地图
                await this.addRealDataToMap(response.data);
                
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
    async addRealDataToMap(data) {
        if (!this.mapController || !this.mapController.isInitialized) {
            console.warn('[RentalAgentApp] 地图控制器未初始化');
            return;
        }

        // 清除现有的智能体标记
        this.mapController.clearAllAgents();

        // 添加租客
        if (data.tenants && Array.isArray(data.tenants)) {
            for (const tenant of data.tenants) {
                // 构建偏好信息
                const preferences = [];
                if (tenant.min_bedrooms || tenant.max_bedrooms) {
                    preferences.push(`${tenant.min_bedrooms || 1}-${tenant.max_bedrooms || '任意'}卧室`);
                }
                if (tenant.max_budget) {
                    preferences.push(`预算£${tenant.max_budget}/月`);
                }
                if (tenant.has_pets) {
                    preferences.push('携带宠物');
                }
                if (tenant.is_student) {
                    preferences.push('学生');
                }
                if (tenant.num_occupants > 1) {
                    preferences.push(`${tenant.num_occupants}人居住`);
                }

                // 获取租客的偏好位置
                let tenantPosition = null;
                if (tenant.preferred_locations && tenant.preferred_locations.length > 0) {
                    // 使用第一个偏好位置
                    const preferredLocation = tenant.preferred_locations[0];
                    tenantPosition = {
                        lat: preferredLocation.latitude,
                        lng: preferredLocation.longitude
                    };
                    console.log(`[RentalAgentApp] 租客 ${tenant.name} 偏好位置: ${tenantPosition.lat}, ${tenantPosition.lng}`);
                }

                await this.mapController.addAgent(tenant.tenant_id, 'tenant', {
                    name: tenant.name || '租客',
                    budget: tenant.max_budget || 0,
                    preferences: preferences.join(', ') || '寻找合适房源',
                    income: tenant.annual_income || 0,
                    email: tenant.email || '',
                    phone: tenant.phone || '',
                    hasGuarantor: tenant.has_guarantor || false,
                    isStudent: tenant.is_student || false,
                    hasPets: tenant.has_pets || false,
                    isSmoker: tenant.is_smoker || false
                }, tenantPosition); // 传递租客的偏好位置
            }
        }

        // 添加房东
        if (data.landlords && Array.isArray(data.landlords)) {
            for (const landlord of data.landlords) {
                // 统计房东的房产信息
                const propertyCount = landlord.properties ? landlord.properties.length : 0;
                const propertyTypes = landlord.properties 
                    ? [...new Set(landlord.properties.map(p => p.property_sub_type || p.property_type_full_description))]
                    : [];

                // 获取房东的位置（基于第一个房产的位置）
                let landlordPosition = null;
                if (landlord.properties && landlord.properties.length > 0) {
                    const firstProperty = landlord.properties[0];
                    if (firstProperty.location) {
                        landlordPosition = {
                            lat: firstProperty.location.latitude,
                            lng: firstProperty.location.longitude
                        };
                        console.log(`[RentalAgentApp] 房东 ${landlord.name} 位置: ${landlordPosition.lat}, ${landlordPosition.lng}`);
                    }
                }

                await this.mapController.addAgent(landlord.landlord_id, 'landlord', {
                    name: landlord.name || '房东',
                    properties: `${propertyCount}套房产`,
                    propertyTypes: propertyTypes.join(', ') || '待分配房产',
                    branchName: landlord.branch_name || '',
                    phone: landlord.phone || '',
                    petFriendly: landlord.preferences?.pet_friendly || false,
                    smokingAllowed: landlord.preferences?.smoking_allowed || false,
                    depositWeeks: landlord.preferences?.deposit_weeks || 0
                }, landlordPosition); // 传递房东基于房产的位置
            }
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
        // 配置后端URL
        const config = {
            apiKey: 'AIzaSyDSflr_l6w6IZIhqcFO2J_0WJacRga2UiU', // Google Maps API Key
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
