/**
 * NetworkManager - Network Communication Manager
 * Handles HTTP requests and WebSocket connections with backend
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
     * Initialize network manager
     */
    async initialize() {
        console.log('[NetworkManager] Initializing...');
        await this.checkConnection();
    }

    /**
     * Check backend connection
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
                console.log('[NetworkManager] Backend connection successful');
                return true;
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.connectionStatus = 'disconnected';
            this.emit('connection:lost', { error: error.message });
            console.error('[NetworkManager] Backend connection failed:', error);
            
            // Display friendlier message for network errors
            if (error.name === 'TypeError' || error.message.includes('fetch')) {
                console.warn('[NetworkManager] Tip: Please ensure backend service is running on http://localhost:8000');
            }
            
            return false;
        }
    }

    /**
     * Send HTTP request
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
            console.error(`[NetworkManager] Request failed ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * Connect WebSocket
     */
    async connectWebSocket(sessionId) {
        if (this.connections.has(sessionId)) {
            console.log(`[NetworkManager] WebSocket ${sessionId} already connected`);
            return this.connections.get(sessionId);
        }

        const wsUrl = `${this.wsUrl}/ws/${sessionId}`;
        
        return new Promise((resolve, reject) => {
            try {
                const ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    console.log(`[NetworkManager] WebSocket ${sessionId} connected successfully`);
                    this.setupHeartbeat(sessionId, ws);
                    this.emit('websocket:connected', { sessionId });
                    resolve(ws);
                };

                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleWebSocketMessage(sessionId, data);
                    } catch (error) {
                        console.error(`[NetworkManager] WebSocket message parsing failed:`, error);
                    }
                };

                ws.onclose = () => {
                    console.log(`[NetworkManager] WebSocket ${sessionId} connection closed`);
                    this.cleanupConnection(sessionId);
                    this.emit('websocket:disconnected', { sessionId });
                };

                ws.onerror = (error) => {
                    console.error(`[NetworkManager] WebSocket ${sessionId} error:`, error);
                    this.emit('websocket:error', { sessionId, error });
                    reject(error);
                };

                this.connections.set(sessionId, ws);

            } catch (error) {
                console.error(`[NetworkManager] WebSocket connection failed:`, error);
                reject(error);
            }
        });
    }

    /**
     * Setup heartbeat mechanism
     */
    setupHeartbeat(sessionId, ws) {
        const interval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
            } else {
                clearInterval(interval);
                this.heartbeatIntervals.delete(sessionId);
            }
        }, 10000); // Send heartbeat every 10 seconds

        this.heartbeatIntervals.set(sessionId, interval);
    }

    /**
     * Cleanup connection
     */
    cleanupConnection(sessionId) {
        this.connections.delete(sessionId);
        
        // Cleanup heartbeat
        if (this.heartbeatIntervals.has(sessionId)) {
            clearInterval(this.heartbeatIntervals.get(sessionId));
            this.heartbeatIntervals.delete(sessionId);
        }
    }

    /**
     * Handle WebSocket messages
     */
    handleWebSocketMessage(sessionId, data) {
        console.log(`[NetworkManager] Received WebSocket message ${sessionId}:`, data);

        // Handle heartbeat responses
        if (data.type === 'pong' || data.type === 'server_ping') {
            return; // Heartbeat messages don't need further processing
        }

        // Always forward the raw message to the main app for processing - THIS IS CRITICAL
        this.emit('websocket:message', { ...data, sessionId });
        
        // Debug the message to make sure it's properly structured
        if (data.type === 'message_sent') {
            console.log(`[NetworkManager] DIALOGUE MESSAGE: ${data.content || data.message}`, {
                agent_type: data.agent_type,
                agent_name: data.agent_name,
                session_id: sessionId
            });
        }
        
        // Also emit specific event types for compatibility
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
            case 'conversation_message':
                this.emit('conversation:message', { ...data, sessionId });
                break;
            case 'connection_status':
                this.emit('connection:status', { ...data, sessionId });
                break;
            default:
                this.emit('websocket:message', { ...data, sessionId });
        }
    }

    /**
     * Send WebSocket message
     */
    sendWebSocketMessage(sessionId, message) {
        const ws = this.connections.get(sessionId);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
            return true;
        }
        console.warn(`[NetworkManager] WebSocket ${sessionId} not available`);
        return false;
    }

    /**
     * Get configuration info
     */
    async getConfig() {
        try {
            return await this.request('/config');
        } catch (error) {
            console.error('[NetworkManager] Failed to get config:', error);
            return null;
        }
    }

    /**
     * Retry connection
     */
    async retryConnection() {
        if (this.retryAttempts >= this.maxRetryAttempts) {
            console.error('[NetworkManager] Maximum retry attempts reached');
            return false;
        }

        this.retryAttempts++;
        console.log(`[NetworkManager] Retrying connection (${this.retryAttempts}/${this.maxRetryAttempts})`);
        
        await new Promise(resolve => setTimeout(resolve, 2000 * this.retryAttempts));
        return await this.checkConnection();
    }

    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            status: this.connectionStatus,
            activeConnections: this.connections.size,
            retryAttempts: this.retryAttempts
        };
    }

    /**
     * Event system
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
                    console.error(`[NetworkManager] Event handler error (${event}):`, error);
                }
            });
        }
    }

    /**
     * Send message to WebSocket
     */
    sendToWebSocket(sessionId, data) {
        if (!this.connections.has(sessionId)) {
            console.error(`[NetworkManager] Attempting to send to non-existent WebSocket connection: ${sessionId}`);
            return false;
        }
        
        const ws = this.connections.get(sessionId);
        if (ws.readyState === WebSocket.OPEN) {
            try {
                ws.send(JSON.stringify(data));
                console.log(`[NetworkManager] Message sent to WebSocket ${sessionId}:`, data);
                return true;
            } catch (error) {
                console.error(`[NetworkManager] Failed to send WebSocket message:`, error);
                return false;
            }
        } else {
            console.warn(`[NetworkManager] WebSocket ${sessionId} not ready, cannot send message`);
            return false;
        }
    }
    
    /**
     * Close all WebSocket connections
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
     * Destroy network manager
     */
    destroy() {
        this.closeAllConnections();
        this.eventListeners.clear();
        console.log('[NetworkManager] Destroyed');
    }
}

export default NetworkManager;
