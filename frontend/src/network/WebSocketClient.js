/**
 * WebSocketClient for handling WebSocket connections to the backend
 */
export default class WebSocketClient {
  constructor(url, onMessage, onConnect, onDisconnect, onError) {
    this.url = url;
    this.ws = null;
    this.onMessage = onMessage || (() => {});
    this.onConnect = onConnect || (() => {});
    this.onDisconnect = onDisconnect || (() => {});
    this.onError = onError || (() => {});
    this.isConnected = false;
    this.reconnectTimer = null;
  }

  /**
   * Connect to the WebSocket server
   */
  connect() {
    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    // Close any existing connection
    if (this.ws) {
      this.ws.close();
    }
    
    // Create new WebSocket connection
    try {
      this.ws = new WebSocket(this.url);
      
      // Set up event handlers
      this.ws.onopen = () => {
        console.log('WebSocket connected to', this.url);
        this.isConnected = true;
        this.onConnect();
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.isConnected = false;
        this.onDisconnect();
        
        // Attempt to reconnect after a delay
        this.reconnectTimer = setTimeout(() => this.connect(), 3000);
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.onError(error);
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      
      // Attempt to reconnect after a delay
      this.reconnectTimer = setTimeout(() => this.connect(), 3000);
    }
  }
  
  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  /**
   * Send data through the WebSocket
   * @param {Object} data - The data to send
   */
  send(data) {
    if (this.isConnected && this.ws) {
      try {
        this.ws.send(JSON.stringify(data));
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
      }
    } else {
      console.warn('Cannot send WebSocket message: not connected');
    }
  }
}
