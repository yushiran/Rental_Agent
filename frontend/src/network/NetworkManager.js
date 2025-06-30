/**
 * NetworkManager - 网络通信管理器
 * 处理与后端的HTTP请求和WebSocket连接
 */
class NetworkManager {
    constructor() {
        this.baseUrl = 'http://localhost:8000';
        this.wsUrl = 'ws://localhost:8000';
        this.connections = new Map();
        this.eventListeners = new Map();
        this.connectionStatus = 'disconnected';
        this.retryAttempts = 0;
        this.maxRetryAttempts = 3;
        this.heartbeatIntervals = new Map();
    }

    /**
     * 初始化网络管理器
     */
    async initialize() {
        console.log('[NetworkManager] 初始化中...');
        await this.checkConnection();
    }

    /**
     * 检查后端连接
     */
    async checkConnection() {
        try {
            const response = await fetch(`${this.baseUrl}/`, {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                this.connectionStatus = 'connected';
                this.retryAttempts = 0;
                this.emit('connection:established', { status: 'connected' });
                console.log('[NetworkManager] 后端连接成功');
                return true;
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.connectionStatus = 'disconnected';
            this.emit('connection:lost', { error: error.message });
            console.error('[NetworkManager] 后端连接失败:', error);
            
            // 如果是网络错误，显示更友好的提示
            if (error.name === 'TypeError' || error.message.includes('fetch')) {
                console.warn('[NetworkManager] 提示：请确保后端服务正在运行在 http://localhost:8000');
            }
            
            return false;
        }
    }

    /**
     * 发送HTTP请求
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`[NetworkManager] 请求失败 ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * 连接WebSocket
     */
    async connectWebSocket(sessionId) {
        if (this.connections.has(sessionId)) {
            console.log(`[NetworkManager] WebSocket ${sessionId} 已连接`);
            return this.connections.get(sessionId);
        }

        const wsUrl = `${this.wsUrl}/ws/${sessionId}`;
        
        return new Promise((resolve, reject) => {
            try {
                const ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    console.log(`[NetworkManager] WebSocket ${sessionId} 连接成功`);
                    this.setupHeartbeat(sessionId, ws);
                    this.emit('websocket:connected', { sessionId });
                    resolve(ws);
                };

                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleWebSocketMessage(sessionId, data);
                    } catch (error) {
                        console.error(`[NetworkManager] WebSocket消息解析失败:`, error);
                    }
                };

                ws.onclose = () => {
                    console.log(`[NetworkManager] WebSocket ${sessionId} 连接关闭`);
                    this.cleanupConnection(sessionId);
                    this.emit('websocket:disconnected', { sessionId });
                };

                ws.onerror = (error) => {
                    console.error(`[NetworkManager] WebSocket ${sessionId} 错误:`, error);
                    this.emit('websocket:error', { sessionId, error });
                    reject(error);
                };

                this.connections.set(sessionId, ws);

            } catch (error) {
                console.error(`[NetworkManager] WebSocket连接失败:`, error);
                reject(error);
            }
        });
    }

    /**
     * 设置心跳机制
     */
    setupHeartbeat(sessionId, ws) {
        const interval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
            } else {
                clearInterval(interval);
                this.heartbeatIntervals.delete(sessionId);
            }
        }, 10000); // 每10秒发送一次心跳

        this.heartbeatIntervals.set(sessionId, interval);
    }

    /**
     * 清理连接
     */
    cleanupConnection(sessionId) {
        this.connections.delete(sessionId);
        
        // 清理心跳
        if (this.heartbeatIntervals.has(sessionId)) {
            clearInterval(this.heartbeatIntervals.get(sessionId));
            this.heartbeatIntervals.delete(sessionId);
        }
    }

    /**
     * 处理WebSocket消息
     */
    handleWebSocketMessage(sessionId, data) {
        console.log(`[NetworkManager] 收到WebSocket消息 ${sessionId}:`, data);

        // 处理心跳响应
        if (data.type === 'pong' || data.type === 'server_ping') {
            return; // 心跳消息不需要进一步处理
        }

        // 根据消息类型分发事件
        switch (data.type) {
            case 'agent_started':
                this.emit('agent:started', { ...data, sessionId });
                break;
            case 'message_sent':
                this.emit('message:sent', { ...data, sessionId });
                break;
            case 'agent_thought':
                this.emit('agent:thought', { ...data, sessionId });
                break;
            case 'agreement_reached':
            case 'dialogue_ended':
                this.emit('negotiation:completed', { ...data, sessionId });
                break;
            case 'negotiation_started':
                this.emit('negotiation:started', { ...data, sessionId });
                break;
            case 'history':
                this.emit('negotiation:history', { ...data, sessionId });
                break;
            case 'connection_status':
                this.emit('connection:status', { ...data, sessionId });
                break;
            default:
                this.emit('websocket:message', { ...data, sessionId });
        }
    }

    /**
     * 发送WebSocket消息
     */
    sendWebSocketMessage(sessionId, message) {
        const ws = this.connections.get(sessionId);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
            return true;
        }
        console.warn(`[NetworkManager] WebSocket ${sessionId} 不可用`);
        return false;
    }

    /**
     * 获取配置信息
     */
    async getConfig() {
        try {
            return await this.request('/config');
        } catch (error) {
            console.error('[NetworkManager] 获取配置失败:', error);
            return null;
        }
    }

    /**
     * 重试连接
     */
    async retryConnection() {
        if (this.retryAttempts >= this.maxRetryAttempts) {
            console.error('[NetworkManager] 已达到最大重试次数');
            return false;
        }

        this.retryAttempts++;
        console.log(`[NetworkManager] 重试连接 (${this.retryAttempts}/${this.maxRetryAttempts})`);
        
        await new Promise(resolve => setTimeout(resolve, 2000 * this.retryAttempts));
        return await this.checkConnection();
    }

    /**
     * 获取连接状态
     */
    getConnectionStatus() {
        return {
            status: this.connectionStatus,
            activeConnections: this.connections.size,
            retryAttempts: this.retryAttempts
        };
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
                    console.error(`[NetworkManager] 事件处理器错误 (${event}):`, error);
                }
            });
        }
    }

    /**
     * 关闭所有WebSocket连接
     */
    closeAllConnections() {
        for (const [sessionId, ws] of this.connections) {
            if (ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
            this.cleanupConnection(sessionId);
        }
        this.connections.clear();
    }

    /**
     * 销毁网络管理器
     */
    destroy() {
        this.closeAllConnections();
        this.eventListeners.clear();
        console.log('[NetworkManager] 已销毁');
    }
}

export default NetworkManager;
