import AgentMapController from './maps/AgentMapController.js';
import NetworkManager from './network/NetworkManager.js';
import MarketAnalysisOverlay from './components/MarketAnalysisOverlay.js';

/**
 * RentalAgentApp - Rental Agent Application Main Class
 * Multi-Agent Rental Negotiation Visualization System Based on Google Maps
 */
class RentalAgentApp {
    constructor() {
        this.mapController = null;
        this.networkManager = null;
        this.marketAnalysis = null; // 🔥 新增市场分析组件
        this.currentSession = null;
        this.negotiationSessions = [];
        this.isInitialized = false;
        this.eventListeners = new Map();
        this._initializedData = null; // Store initialized data from backend

        // 配置
        this.config = {
            apiKey: '', // Google Maps API Key - should be set externally
            backendUrl: 'http://localhost:8000',
            mapContainer: 'map'
        };
    }

    /**
     * Initialize Application
     */
    async initialize(config = {}) {
        console.log('[RentalAgentApp] Application initialization started...');

        try {
            // Merge configuration
            this.config = { ...this.config, ...config };

            // Initialize network manager
            this.networkManager = new NetworkManager();
            await this.networkManager.initialize();

            // Initialize map controller
            this.mapController = new AgentMapController();
            await this.mapController.initialize(this.config.apiKey, this.config.mapContainer);
            
            // 🔥 Initialize market analysis overlay
            this.marketAnalysis = new MarketAnalysisOverlay({
                backendUrl: this.config.backendUrl
            });
            this.marketAnalysis.initialize(this); // 传入this作为logger

            // Setup event listeners
            this.setupEventListeners();

            // Manually check connection status once
            this.updateConnectionStatus(this.networkManager.connectionStatus === 'connected');

            // Update UI state
            this.updateUI();

            this.isInitialized = true;
            console.log('[RentalAgentApp] Application initialization completed');

        } catch (error) {
            console.error('[RentalAgentApp] Initialization failed:', error);
            this.showError('Application initialization failed: ' + error.message);
            throw error;
        }
    }

    /**
     * Setup Event Listeners
     */
    setupEventListeners() {
        // Network events
        this.networkManager.on('connection:established', () => {
            this.updateConnectionStatus(true);
        });

        this.networkManager.on('connection:lost', () => {
            this.updateConnectionStatus(false);
        });

        // WebSocket events - primary handler for all WebSocket messages
        this.networkManager.on('websocket:message', (data) => {
            this.addLog('debug', `收到WebSocket原始消息: ${data.type || 'unknown'}`);
            this.handleWebSocketMessage(data);
        });

        // WebSocket connection events
        this.networkManager.on('websocket:connected', (data) => {
            this.addLog('success', `WebSocket连接已建立: ${data.sessionId || 'unknown'}`);
            this.handleWebSocketConnected(data);
        });

        this.networkManager.on('websocket:disconnected', (data) => {
            this.addLog('error', `WebSocket连接已断开: ${data.sessionId || 'unknown'}`);
        });

        this.networkManager.on('websocket:error', (data) => {
            this.addLog('error', `WebSocket错误: ${data.sessionId || 'unknown'}`);
        });

        // UI events
        this.setupUIEventListeners();
    }

    /**
     * Setup UI Event Listeners
     */
    setupUIEventListeners() {
        // Initialize system button
        const initBtn = document.getElementById('initialize-system');
        if (initBtn) {
            initBtn.addEventListener('click', () => this.initializeSystem());
        }

        // Start negotiation button
        const startBtn = document.getElementById('start-negotiation');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startNegotiation());
        }

        // Reset button
        const resetBtn = document.getElementById('reset-session');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetSession());
        }

        // Clear logs button
        const clearLogsBtn = document.getElementById('clear-logs');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => this.clearLogs());
        }


    }

    /**
     * Start Negotiation
     */
    async startNegotiation() {
        if (!this.isInitialized) {
            this.showError('Application not initialized');
            return;
        }

        try {
            this.updateStatus('Starting negotiation...');
            this.setButtonLoading('start-negotiation', true);

            // Get tenant IDs from stored data if available
            const tenantIds = [];
            if (this._initializedData && this._initializedData.tenants) {
                tenantIds.push(...this._initializedData.tenants.map(tenant => tenant.tenant_id));
                this.addLog('info', `Using ${tenantIds.length} tenants for negotiation`);
            } else {
                this.addLog('warning', 'No initialized tenant data available, proceeding with empty tenant selection');
            }

            // Send start negotiation request with tenant IDs
            const response = await this.networkManager.request('/start-negotiation', {
                method: 'POST',
                body: JSON.stringify({
                    tenant_ids: tenantIds
                })
            });

            if (response.sessions && response.sessions.length > 0) {
                this.updateStatus(`Negotiation started with ${response.total_sessions} sessions`);
                this.addLog('info', `Negotiation started: ${response.total_sessions} sessions created`);

                // Store all negotiation sessions
                this.negotiationSessions = response.sessions;

                // Connect WebSocket for each session and start negotiation visualization
                for (const session of response.sessions) {
                    await this.startNegotiationSession(session);
                }

                this.updateStatus('All negotiation sessions active');

            } else {
                throw new Error('No negotiation sessions created');
            }

        } catch (error) {
            console.error('[RentalAgentApp] Failed to start negotiation:', error);
            this.showError('Failed to start negotiation: ' + error.message);
            this.updateStatus('Failed to start negotiation');
        } finally {
            this.setButtonLoading('start-negotiation', false);
        }
    }

    /**
     * Start individual negotiation session
     */
    async startNegotiationSession(session) {
        try {
            // Connect WebSocket for this session
            await this.networkManager.connectWebSocket(session.session_id);

            // Find available agents
            const allAgents = this.mapController.getAllAgents();
            const availableTenants = allAgents.filter(a => a.type === 'tenant' && a.status === 'idle');
            const availableLandlords = allAgents.filter(a => a.type === 'landlord' && a.status === 'idle');

            // Smart agent assignment: use first available agents if names don't match
            let tenantAgent = this.mapController.getAgentByName(session.tenant_name);
            let landlordAgent = this.mapController.getAgentByName(session.landlord_name);

            // Fallback to available agents if names don't match
            if (!tenantAgent && availableTenants.length > 0) {
                tenantAgent = availableTenants[0];
            }
            if (!landlordAgent && availableLandlords.length > 0) {
                landlordAgent = availableLandlords[0];
            }

            if (tenantAgent && landlordAgent) {
                // Update agent statuses to negotiating
                this.mapController.updateAgentStatus(tenantAgent.id, 'negotiating');
                this.mapController.updateAgentStatus(landlordAgent.id, 'negotiating');

                // Store session mapping for WebSocket messages
                session._frontendAgents = {
                    tenant: tenantAgent,
                    landlord: landlordAgent
                };

                // Set agents to ready for receiving WebSocket messages
                this.mapController.updateAgentStatus(tenantAgent.id, 'ready');
                this.mapController.updateAgentStatus(landlordAgent.id, 'ready');

                // Initialize session - no hardcoded dialogue, only WebSocket content
                // Visual effects will be triggered after WebSocket connection

                // Just move tenant to appropriate position
                setTimeout(async () => {
                    this.triggerNegotiationVisuals(session);
                }, 500);

                this.addLog('info', `Session ${session.session_id}: ${tenantAgent.name} ↔ ${landlordAgent.name} (Score: ${session.match_score})`);
            } else {
                this.addLog('error', `No available agents for session ${session.session_id}`);
            }

        } catch (error) {
            console.error(`[RentalAgentApp] Failed to start session ${session.session_id}:`, error);
            this.addLog('error', `Failed to start session ${session.session_id}: ${error.message}`);
        }
    }

    /**
     * Move tenant towards landlord visually
     */
    async moveTenantToLandlord(tenantAgent, landlordAgent) {
        const tenantPos = tenantAgent.position;
        const landlordPos = landlordAgent.position;

        // Calculate intermediate position (closer to landlord)
        const moveDistance = 0.3; // 30% of the way
        const newPosition = {
            lat: tenantPos.lat + (landlordPos.lat - tenantPos.lat) * moveDistance,
            lng: tenantPos.lng + (landlordPos.lng - tenantPos.lng) * moveDistance
        };

        // Move tenant to new position
        this.mapController.moveAgent(tenantAgent.id, newPosition);

        // Update agent position in our records
        tenantAgent.position = newPosition;

        // Wait for animation to complete
        await new Promise(resolve => setTimeout(resolve, 1500));
    }

    /**
     * Start chat visualization for a session
     */
    startChatVisualization(session, tenantAgent, landlordAgent) {
        // Store agents in session for later reference
        if (!session._frontendAgents) {
            session._frontendAgents = {
                tenant: tenantAgent,
                landlord: landlordAgent
            };
        }

        // Send WebSocket heartbeat to trigger backend activity
        setTimeout(() => {
            try {
                this.networkManager.sendToWebSocket(session.session_id, {
                    type: "client_ready",
                    timestamp: Date.now()
                });
            } catch (error) {
                console.error(`[RentalAgentApp] Failed to send client ready message:`, error);
            }
        }, 1000);
    }

    /**
     * Reset Session
     */
    async resetSession() {
        try {
            this.updateStatus('Resetting session...');

            // Close all WebSocket connections
            this.networkManager.closeAllConnections();

            // Reset backend state
            await this.networkManager.request('/reset-memory', {
                method: 'POST'
            });

            // Clear agents from map
            this.mapController.clearAllAgents();

            // Clear current session and negotiation sessions
            this.currentSession = null;
            this.negotiationSessions = [];

            // Update UI
            this.updateStatus('Session reset');
            this.addLog('info', 'Session has been reset');
            this.updateUI();

        } catch (error) {
            console.error('[RentalAgentApp] Failed to reset session:', error);
            this.showError('Failed to reset session: ' + error.message);
        }
    }




    handleWebSocketMessage(data) {
        const {
            sessionId,
            session_id,
            event,
            payload,
            type,
            message,
            content,
            agent_id,
            agent_name,
            agent_type,
            active_agent,
            role
        } = data;

        // 统一会话ID提取
        const finalSessionId = sessionId || session_id;

        // 统一消息内容提取
        const messageContent = message || content || (payload && payload.content);

        // 统一事件类型提取
        const eventType = event || type;

        this.addLog('debug', `WebSocket消息类型: ${eventType || 'unknown'}`);

        // 🎯 关键：如果消息包含对话内容，直接处理为对话
        if (messageContent && typeof messageContent === 'string' && messageContent.trim() !== '') {
            this.displayAgentDialogue({
                session_id: finalSessionId,
                content: messageContent,
                agent_type: agent_type || active_agent,
                agent_name: agent_name,
                agent_id: agent_id,
                role: role,
                originalData: data
            });
        }

        // 🎯 根据事件类型处理特定逻辑
        switch (eventType) {
            case 'agent_started':
                this.handleAgentStarted(payload || data);
                break;
            case 'agent_thought':
                this.handleAgentThought(payload || data);
                break;
            case 'agreement_reached':
                this.handleAgreementReached(payload || data);
                break;
            case 'dialogue_ended':
                this.handleDialogueEnded(payload || data);
                break;
            case 'connected':
                this.handleWebSocketConnected(data);
                break;
            case 'message_sent':
                // 已通过上面的messageContent检查处理
                break;
            default:
                this.addLog('debug', `未处理的事件类型: ${eventType}`);
        }
    }

    /**
     * 🎯 核心方法：统一的智能体对话显示处理
     */
    displayAgentDialogue({ session_id, content, agent_type, agent_name, agent_id, role, originalData }) {
        try {
            const targetAgent = this.findTargetAgent(session_id, agent_type, agent_id, agent_name);

            if (!targetAgent) {
                this.addLog('warning', `找不到对应的智能体 - ${agent_name || agent_type || 'unknown'}: ${content.substring(0, 50)}...`);
                return;
            }

            // 显示对话气泡
            const displayTime = this.calculateDisplayTime(content);
            this.mapController.showAgentDialogue(targetAgent.id, content, displayTime);

            // 更新智能体状态动画
            this.updateAgentSpeakingAnimation(targetAgent);

            // 记录对话日志
            this.logDialogueMessage(session_id, targetAgent, agent_type, content, role);

        } catch (error) {
            this.addLog('error', `显示对话失败: ${error.message}`);
        }
    }

    /**
     * 🔍 智能体查找方法 - 多层回退机制
     */
    findTargetAgent(session_id, agent_type, agent_id, agent_name) {
        let targetAgent = null;

        // 通过会话ID查找
        if (session_id) {
            const matchedSession = this.negotiationSessions.find(s => s.session_id === session_id);
            if (matchedSession && matchedSession._frontendAgents) {
                if (agent_type === 'tenant') {
                    targetAgent = matchedSession._frontendAgents.tenant;
                } else if (agent_type === 'landlord') {
                    targetAgent = matchedSession._frontendAgents.landlord;
                }
            }
        }

        // 通过智能体ID查找
        if (!targetAgent && agent_id) {
            targetAgent = this.mapController.getAgent(agent_id);
        }

        // 通过智能体名称查找
        if (!targetAgent && agent_name) {
            targetAgent = this.mapController.getAgentByName(agent_name);
        }

        // 按类型查找第一个可用智能体
        if (!targetAgent && agent_type) {
            const allAgents = this.mapController.getAllAgents();
            const matchingAgents = allAgents.filter(a => a.type === agent_type);
            if (matchingAgents.length > 0) {
                targetAgent = matchingAgents[0];
            }
        }

        // 使用任意可用智能体
        if (!targetAgent) {
            const allAgents = this.mapController.getAllAgents();
            if (allAgents.length > 0) {
                targetAgent = allAgents[0];
            }
        }

        return targetAgent;
    }

    /**
     * 🎬 计算对话气泡显示时间
     */
    calculateDisplayTime(content) {
        const baseTime = 5000; // 5秒基础时间
        const maxTime = 12000; // 12秒最大时间
        const timePerChar = 80; // 每个字符80毫秒

        return Math.max(baseTime, Math.min(content.length * timePerChar, maxTime));
    }

    /**
     * 🎭 更新智能体说话动画
     */
    updateAgentSpeakingAnimation(targetAgent) {
        this.mapController.updateAgentStatus(targetAgent.id, 'speaking');
        setTimeout(() => {
            this.mapController.updateAgentStatus(targetAgent.id, 'active');
        }, 1500);
    }

    /**
     * 📝 记录对话日志
     */
    logDialogueMessage(session_id, targetAgent, agent_type, content, role) {
        let rolePrefix = '';
        if (role === 'user') rolePrefix = '💬 ';
        else if (role === 'assistant') rolePrefix = '🤖 ';

        const logMessage = session_id
            ? `[${session_id}] ${rolePrefix}${targetAgent.name} (${agent_type}): ${content}`
            : `${rolePrefix}${targetAgent.name}: ${content}`;

        this.addLog('message', logMessage);
    }

    /**
     * Handle Agent Started Event
     */
    handleAgentStarted(payload) {
        const { agent_id, agent_type } = payload;
        this.mapController.updateAgentStatus(agent_id, 'active');
        this.addLog('info', `${agent_type} ${agent_id} started action`);
    }
    /**
     * Handle WebSocket Connected Event
     */
    handleWebSocketConnected(data) {
        const sessionId = data.session_id || data.sessionId;
        if (sessionId) {
            this.addLog('info', `Session ${sessionId} WebSocket connected`);

            // Find the session and trigger visual effects
            const session = this.negotiationSessions.find(s => s.session_id === sessionId);
            if (session) {
                setTimeout(() => {
                    this.triggerNegotiationVisuals(session);
                }, 500);
            }
        }
    }

    /**
     * Trigger negotiation visual effects
     */
    async triggerNegotiationVisuals(session) {
        // Use pre-assigned agents if available
        if (session._frontendAgents) {
            const { tenant: tenantAgent, landlord: landlordAgent } = session._frontendAgents;

            // Move tenant towards landlord
            await this.moveTenantToLandlord(tenantAgent, landlordAgent);

            // Start chat visualization
            this.startChatVisualization(session, tenantAgent, landlordAgent);

            this.addLog('info', `Visual effects started for ${tenantAgent.name} ↔ ${landlordAgent.name}`);
        }
    }

    /**
     * Handle Agent Thought Event
     */
    handleAgentThought(payload) {
        const { agent_id, agent_name, thought, session_id } = payload;

        // Find the agent to update status
        let targetAgent = this.mapController.getAgent(agent_id) || this.mapController.getAgentByName(agent_name);

        if (targetAgent) {
            this.mapController.updateAgentStatus(targetAgent.id, 'thinking');
        }

        // Log the thought
        const logMessage = session_id
            ? `[${session_id}] ${agent_name || agent_id} thinking: ${thought}`
            : `${agent_name || agent_id} thinking: ${thought}`;
        this.addLog('thought', logMessage);
    }

    /**
     * Handle Agreement Reached Event
     */
    handleAgreementReached(payload) {
        const { tenant_id, landlord_id, agreement_details, session_id } = payload;

        if (tenant_id) this.mapController.updateAgentStatus(tenant_id, 'active');
        if (landlord_id) this.mapController.updateAgentStatus(landlord_id, 'active');

        this.updateStatus('Negotiation successful!');
        this.addLog('success', 'Agreement reached!');

        if (agreement_details) {
            this.addLog('info', `Agreement details: ${JSON.stringify(agreement_details, null, 2)}`);
        }

        this.showSuccess('Negotiation successful!');
    }

    async handleDialogueEnded(payload) {
        const { reason, final_status, session_id } = payload;

        this.updateStatus('Negotiation ended');

        const logMessage = session_id
            ? `[${session_id}] Negotiation ended - ${reason}`
            : `Negotiation ended - ${reason}`;
        this.addLog('info', logMessage);

        if (final_status === 'failed') {
            this.showError('Negotiation failed');
        } else {
            this.addLog('success', 'Negotiation completed successfully');
        }

        // 🔥 使用新的市场分析组件
        if (this.marketAnalysis) {
            await this.marketAnalysis.fetchAndDisplay();
        }
    }

    /**
     * 🔥 提供给市场分析组件的快捷方法
     */
    displayMarketAnalysis(analysisResult) {
        if (this.marketAnalysis) {
            this.marketAnalysis.displayAnalysis(analysisResult);
        }
    }

    hideMarketAnalysis() {
        if (this.marketAnalysis) {
            this.marketAnalysis.hide();
        }
    }

    toggleMarketAnalysis() {
        if (this.marketAnalysis) {
            this.marketAnalysis.toggle();
        }
    }

    /**
     * Update Connection Status
     */
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            // Use text from data attributes, fallback to default values if not available
            const connectedText = statusEl.dataset.connectedText || 'Connected';
            const disconnectedText = statusEl.dataset.disconnectedText || 'Disconnected';

            statusEl.textContent = connected ? connectedText : disconnectedText;
            statusEl.className = `status ${connected ? 'connected' : 'disconnected'}`;
        }
    }

    /**
     * Update Status Display
     */
    updateStatus(status) {
        const statusEl = document.getElementById('current-status');
        if (statusEl) {
            statusEl.textContent = status;
        }
    }

    /**
     * Update UI State
     */
    updateUI() {
        const hasSession = !!this.currentSession || this.negotiationSessions.length > 0;

        // Update button states
        const startBtn = document.getElementById('start-negotiation');
        const resetBtn = document.getElementById('reset-session');
        const initBtn = document.getElementById('initialize-system');

        if (startBtn) {
            startBtn.disabled = hasSession;
            if (hasSession) {
                const sessionCount = this.negotiationSessions.length;
                startBtn.textContent = sessionCount > 0 ? `Negotiation in progress (${sessionCount} sessions)` : 'Negotiation in progress...';
            } else {
                startBtn.textContent = 'Start Negotiation';
            }
        }

        if (resetBtn) {
            resetBtn.disabled = !hasSession;
        }

        if (initBtn) {
            initBtn.disabled = hasSession;
        }
    }

    /**
     * Set Button Loading State
     */
    setButtonLoading(buttonId, loading) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.disabled = loading;
            if (loading) {
                button.textContent = button.dataset.loadingText || 'Loading...';
            } else {
                button.textContent = button.dataset.originalText || button.textContent;
            }
        }
    }

    /**
     * Add Log Entry
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
     * Clear Logs
     */
    clearLogs() {
        const logsContainer = document.getElementById('logs-container');
        if (logsContainer) {
            logsContainer.innerHTML = '';
        }
    }

    /**
     * Show Error/Success Message
     */
    showError(message) {
        this.showNotification(message, 'error');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    /**
     * Show Notification
     */
    showNotification(message, type = 'info') {
        // Simple notification implementation
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    /**
     * Initialize System
     */
    async initializeSystem() {
        try {
            this.updateStatus('Initializing system...');
            this.setButtonLoading('initialize-system', true);

            // Get parameters
            const tenantCount = document.getElementById('tenant-count')?.value || 3;
            const resetData = document.getElementById('reset-data')?.checked || false;

            // Send initialization request
            const response = await this.networkManager.request('/initialize', {
                method: 'POST',
                body: JSON.stringify({
                    tenant_count: parseInt(tenantCount),
                    reset_data: resetData
                })
            });

            // Check if response contains data field, indicating successful initialization
            if (response.data && response.status === 'initialized') {
                this.updateStatus(`System initialization successful: ${response.data.tenants_count} tenants, ${response.data.landlords_count} landlords, ${response.data.properties_count} properties`);
                this.addLog('success', `System initialization completed - Tenants: ${response.data.tenants_count}, Landlords: ${response.data.landlords_count}, Properties: ${response.data.properties_count}`);

                // Store initialized data for later use in negotiations
                this._initializedData = response.data;

                // Log some tenant IDs for debugging
                if (response.data.tenants && response.data.tenants.length > 0) {
                    const tenantIds = response.data.tenants.map(t => t.tenant_id).slice(0, 3);
                    this.addLog('info', `Available tenant IDs: ${tenantIds.join(', ')}...`);
                }

                // Enable start negotiation button
                const startBtn = document.getElementById('start-negotiation');
                if (startBtn) {
                    startBtn.disabled = false;
                }

                // Add real data from backend to map
                await this.addRealDataToMap(response.data);

            } else {
                throw new Error(response.message || 'Initialization failed');
            }

        } catch (error) {
            console.error('[RentalAgentApp] System initialization failed:', error);
            this.showError('System initialization failed: ' + error.message);
            this.updateStatus('Initialization failed');
        } finally {
            this.setButtonLoading('initialize-system', false);
        }
    }

    /**
     * Add Real Data from Backend to Map
     */
    async addRealDataToMap(data) {
        if (!this.mapController || !this.mapController.isInitialized) {
            console.warn('[RentalAgentApp] Map controller not initialized');
            return;
        }

        // Clear existing agent markers
        this.mapController.clearAllAgents();

        // Add tenants
        if (data.tenants && Array.isArray(data.tenants)) {
            for (const tenant of data.tenants) {
                // Build preference information
                const preferences = [];
                if (tenant.min_bedrooms || tenant.max_bedrooms) {
                    preferences.push(`${tenant.min_bedrooms || 1}-${tenant.max_bedrooms || 'any'} bedrooms`);
                }
                if (tenant.max_budget) {
                    preferences.push(`Budget £${tenant.max_budget}/month`);
                }
                if (tenant.has_pets) {
                    preferences.push('With pets');
                }
                if (tenant.is_student) {
                    preferences.push('Student');
                }
                if (tenant.num_occupants > 1) {
                    preferences.push(`${tenant.num_occupants} occupants`);
                }

                // Get tenant's preferred location
                let tenantPosition = null;
                if (tenant.preferred_locations && tenant.preferred_locations.length > 0) {
                    // Use first preferred location
                    const preferredLocation = tenant.preferred_locations[0];
                    tenantPosition = {
                        lat: preferredLocation.latitude,
                        lng: preferredLocation.longitude
                    };
                }

                await this.mapController.addAgent(tenant.tenant_id, 'tenant', {
                    name: tenant.name || 'Tenant',
                    budget: tenant.max_budget || 0,
                    preferences: preferences.join(', ') || 'Looking for suitable property',
                    income: tenant.annual_income || 0,
                    email: tenant.email || '',
                    phone: tenant.phone || '',
                    hasGuarantor: tenant.has_guarantor || false,
                    isStudent: tenant.is_student || false,
                    hasPets: tenant.has_pets || false,
                    isSmoker: tenant.is_smoker || false
                }, tenantPosition); // Pass tenant's preferred position
            }
        }

        // Add landlords
        if (data.landlords && Array.isArray(data.landlords)) {
            for (const landlord of data.landlords) {
                // Count landlord's property information
                const propertyCount = landlord.properties ? landlord.properties.length : 0;
                const propertyTypes = landlord.properties
                    ? [...new Set(landlord.properties.map(p => p.property_sub_type || p.property_type_full_description))]
                    : [];

                // Get landlord's location (based on first property's location)
                let landlordPosition = null;
                if (landlord.properties && landlord.properties.length > 0) {
                    const firstProperty = landlord.properties[0];
                    if (firstProperty.location) {
                        landlordPosition = {
                            lat: firstProperty.location.latitude,
                            lng: firstProperty.location.longitude
                        };
                    }
                }

                await this.mapController.addAgent(landlord.landlord_id, 'landlord', {
                    name: landlord.name || 'Landlord',
                    properties: `${propertyCount} properties`,
                    propertyTypes: propertyTypes.join(', ') || 'Properties to be assigned',
                    branchName: landlord.branch_name || '',
                    phone: landlord.phone || '',
                    petFriendly: landlord.preferences?.pet_friendly || false,
                    smokingAllowed: landlord.preferences?.smoking_allowed || false,
                    depositWeeks: landlord.preferences?.deposit_weeks || 0
                }, landlordPosition); // Pass landlord's location based on properties
            }
        }

        // Add property markers (using map_data)
        if (data.map_data && Array.isArray(data.map_data)) {
            data.map_data.forEach(property => {
                this.mapController.addPropertyFromData(property);
            });
        }

        this.addLog('info', `Added ${data.tenants_count} tenants, ${data.landlords_count} landlords and ${data.properties_count} properties to map`);
    }

    /**
     * Destroy Application
     */
    destroy() {
        if (this.mapController) {
            this.mapController.destroy();
        }

        if (this.networkManager) {
            // Network manager cleanup
        }
        
        // 🔥 销毁市场分析组件
        if (this.marketAnalysis) {
            this.marketAnalysis.destroy();
        }

        this.eventListeners.clear();
        this.isInitialized = false;
    }


}

// 🌍 将方法暴露到全局，供HTML中的按钮调用
window.hideMarketAnalysis = () => {
    if (window.app && window.app.marketAnalysis) {
        window.app.marketAnalysis.hide();
    }
};

window.toggleMarketAnalysis = () => {
    if (window.app && window.app.marketAnalysis) {
        window.app.marketAnalysis.toggle();
    }
};

// Create global application instance
const app = new RentalAgentApp();
window.app = app; // 🔥 暴露到全局以便其他地方调用

// Application startup
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Configure backend URL
        const config = {
            apiKey: 'AIzaSyDSflr_l6w6IZIhqcFO2J_0WJacRga2UiU', // Google Maps API Key
            backendUrl: 'http://localhost:8000'
        };

        await app.initialize(config);
        console.log('[App] Application startup completed');
    } catch (error) {
        console.error('[App] Application startup failed:', error);
        // Display user-friendly error message
        const statusEl = document.getElementById('current-status');
        if (statusEl) {
            statusEl.textContent = 'Application startup failed';
        }
    }
});

export default app;
