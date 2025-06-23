/**
 * API service for communication with the backend
 */
export default class ApiService {
  constructor(scene) {
    this.scene = scene;
    this.baseUrl = 'http://localhost:8000';
    this.ws = null;
    this.isConnected = false;
  }

  /**
   * Initialize WebSocket connection for real-time events
   */
  connectWebSocket() {
    if (this.ws) {
      this.ws.close();
    }

    this.ws = new WebSocket('ws://localhost:8000/ws/global');

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.isConnected = true;
      this.scene.events.emit('ws-connected');
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.isConnected = false;
      this.scene.events.emit('ws-disconnected');
      
      // Attempt to reconnect after a delay
      setTimeout(() => this.connectWebSocket(), 3000);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.scene.events.emit('ws-error', error);
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        
        // Emit an event based on the message type
        if (data.type) {
          this.scene.events.emit(`ws-${data.type}`, data);
          
          // Also emit a generic message event
          this.scene.events.emit('ws-message', data);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
  }

  /**
   * Close WebSocket connection
   */
  disconnectWebSocket() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Start a new negotiation session
   * @returns {Promise} The response from the API
   */
  async startSession() {
    try {
      const response = await fetch(`${this.baseUrl}/start-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      
      return await response.json();
    } catch (error) {
      console.error('Error starting session:', error);
      throw error;
    }
  }

  /**
   * Reset the memory state
   * @returns {Promise} The response from the API
   */
  async resetMemory() {
    try {
      const response = await fetch(`${this.baseUrl}/reset-memory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      
      return await response.json();
    } catch (error) {
      console.error('Error resetting memory:', error);
      throw error;
    }
  }

  /**
   * Check if the backend is available
   * @returns {Promise<boolean>} True if the backend is available, false otherwise
   */
  async checkBackendStatus() {
    try {
      const response = await fetch(this.baseUrl);
      return response.ok;
    } catch (error) {
      console.error('Backend check failed:', error);
      return false;
    }
  }
}
