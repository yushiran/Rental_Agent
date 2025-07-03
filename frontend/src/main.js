import AgentMapController from './maps/AgentMapController.js';
import NetworkManager from './network/NetworkManager.js';

/**
 * RentalAgentApp - Rental Agent Application Main Class
 * Multi-Agent Rental Negotiation Visualization System Based on Google Maps
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
        
        // WebSocket events
        this.networkManager.on('websocket:message', (data) => {
            this.handleWebSocketMessage(data);
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
            
            // Send start negotiation request
            const response = await this.networkManager.request('/start-session', {
                method: 'POST',
                body: JSON.stringify({
                    tenant_preferences: {
                        budget: 10000,
                        location: 'Beijing City Center',
                        area: '80-120㎡'
                    }
                })
            });
            
            // Get the first session ID from response (compatible with backend format)
            this.currentSession = response.session_ids && response.session_ids.length > 0 
                ? response.session_ids[0] 
                : `session_${Date.now()}`;
            
            // Connect WebSocket
            await this.networkManager.connectWebSocket(this.currentSession);
            
            // // Add agents to map
            // this.addInitialAgents();
            
            this.updateStatus('Negotiation started');
            this.addLog('info', `Negotiation session started: ${this.currentSession}`);
            
        } catch (error) {
            console.error('[RentalAgentApp] Failed to start negotiation:', error);
            this.showError('Failed to start negotiation: ' + error.message);
            this.updateStatus('Failed to start negotiation');
        } finally {
            this.setButtonLoading('start-negotiation', false);
        }
    }

    /**
     * Reset Session
     */
    async resetSession() {
        try {
            this.updateStatus('Resetting session...');
            
            // Reset backend state
            await this.networkManager.request('/reset-memory', {
                method: 'POST'
            });
            
            // Clear agents from map
            this.mapController.clearAllAgents();
            
            // Clear current session
            this.currentSession = null;
            
            // Update UI
            this.updateStatus('Session reset');
            this.addLog('info', 'Session has been reset');
            this.updateUI();
            
        } catch (error) {
            console.error('[RentalAgentApp] Failed to reset session:', error);
            this.showError('Failed to reset session: ' + error.message);
        }
    }



    /**
     * Handle WebSocket Messages
     */
    handleWebSocketMessage(data) {
        const { sessionId, event, payload } = data;
        
        console.log(`[RentalAgentApp] Received event: ${event}`, payload);
        
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
                console.log(`[RentalAgentApp] Unknown event: ${event}`);
        }
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
     * Handle Message Sent Event
     */
    handleMessageSent(payload) {
        const { agent_id, message, agent_type } = payload;
        
        // Show dialogue bubble on map
        this.mapController.showAgentDialogue(agent_id, message);
        
        // Add to log
        this.addLog('message', `${agent_type} ${agent_id}: ${message}`);
    }

    /**
     * Handle Agent Thought Event
     */
    handleAgentThought(payload) {
        const { agent_id, thought } = payload;
        this.mapController.updateAgentStatus(agent_id, 'thinking');
        this.addLog('thought', `${agent_id} thinking: ${thought}`);
    }

    /**
     * Handle Negotiation Update Event
     */
    handleNegotiationUpdate(payload) {
        const { progress, details } = payload;
        this.updateStatus(`Negotiation in progress (${progress}%)`);
        
        if (details) {
            this.addLog('info', `Negotiation progress: ${details}`);
        }
    }

    /**
     * Handle Agreement Reached Event
     */
    handleAgreementReached(payload) {
        const { tenant_id, landlord_id, agreement_details } = payload;
        
        this.mapController.updateAgentStatus(tenant_id, 'active');
        this.mapController.updateAgentStatus(landlord_id, 'active');
        
        this.updateStatus('Negotiation successful!');
        this.addLog('success', 'Agreement reached!');
        this.addLog('info', `Agreement details: ${JSON.stringify(agreement_details, null, 2)}`);
        
        this.showSuccess('Negotiation successful! Both parties reached an agreement');
    }

    /**
     * Handle Dialogue Ended Event
     */
    handleDialogueEnded(payload) {
        const { reason, final_status } = payload;
        
        this.updateStatus('Negotiation ended');
        this.addLog('info', `Negotiation end reason: ${reason}`);
        
        if (final_status === 'failed') {
            this.showError('Negotiation failed');
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
        const hasSession = !!this.currentSession;
        
        // Update button states
        const startBtn = document.getElementById('start-negotiation');
        const resetBtn = document.getElementById('reset-session');
        const initBtn = document.getElementById('initialize-system');
        
        if (startBtn) {
            startBtn.disabled = hasSession;
            startBtn.textContent = hasSession ? 'Negotiation in progress...' : 'Start Negotiation';
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
     * Show Error Message
     */
    showError(message) {
        this.showNotification(message, 'error');
    }

    /**
     * Show Success Message
     */
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
                    console.log(`[RentalAgentApp] Tenant ${tenant.name} preferred location: ${tenantPosition.lat}, ${tenantPosition.lng}`);
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
                        console.log(`[RentalAgentApp] Landlord ${landlord.name} location: ${landlordPosition.lat}, ${landlordPosition.lng}`);
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
        
        this.eventListeners.clear();
        this.isInitialized = false;
    }
}

// Create global application instance
const app = new RentalAgentApp();

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
