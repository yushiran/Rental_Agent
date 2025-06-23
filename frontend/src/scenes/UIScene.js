import Phaser from 'phaser';

/**
 * UI Scene that sits on top of the main scene
 * Used for displaying UI elements like dialogue history
 */
export default class UIScene extends Phaser.Scene {
  constructor() {
    super('UIScene');
    this.messageHistory = [];
    this.maxMessages = 5;
  }

  create() {
    // Create message history container
    this.createMessageHistory();
    
    // Listen for WebSocket events from main scene
    this.listenToMainScene();
  }
  
  createMessageHistory() {
    // Create a semi-transparent panel for message history
    this.panel = this.add.rectangle(
      650, 
      300, 
      280, 
      200, 
      0x000000, 
      0.7
    );
    
    // Add title
    this.add.text(650, 210, 'Message History', {
      fontFamily: 'Arial',
      fontSize: '16px',
      color: '#ffffff'
    }).setOrigin(0.5);
    
    // Container for messages
    this.messageContainer = this.add.container(510, 230);
  }
  
  listenToMainScene() {
    // Get reference to main scene
    const mainScene = this.scene.get('MainScene');
    
    // Listen for message events
    mainScene.events.on('ws-message_sent', (data) => {
      this.addMessageToHistory(data);
    });
    
    // Listen for reset event
    this.game.events.on('memory-reset', () => {
      this.clearMessageHistory();
    });
  }
  
  addMessageToHistory(data) {
    const sender = data.sender;
    const content = data.content;
    
    // Truncate message if too long
    let displayContent = content;
    if (displayContent.length > 30) {
      displayContent = displayContent.substring(0, 27) + '...';
    }
    
    // Create icon based on sender
    const iconTexture = sender === 'tenant' ? 'tenant_icon' : 'landlord_icon';
    
    // Create message entry
    const messageEntry = this.add.container(0, this.messageHistory.length * 30);
    
    // Add icon
    const icon = this.add.image(0, 0, iconTexture);
    icon.setScale(0.3);
    messageEntry.add(icon);
    
    // Add text
    const text = this.add.text(25, 0, displayContent, {
      fontFamily: 'Arial',
      fontSize: '14px',
      color: '#ffffff'
    });
    text.setOrigin(0, 0.5);
    messageEntry.add(text);
    
    // Add to message container
    this.messageContainer.add(messageEntry);
    this.messageHistory.push(messageEntry);
    
    // Remove oldest message if we have too many
    if (this.messageHistory.length > this.maxMessages) {
      const oldestMessage = this.messageHistory.shift();
      oldestMessage.destroy();
      
      // Reposition remaining messages
      this.messageHistory.forEach((msg, index) => {
        msg.y = index * 30;
      });
    }
  }
  
  clearMessageHistory() {
    // Clear all messages
    this.messageHistory.forEach(msg => msg.destroy());
    this.messageHistory = [];
  }
}
