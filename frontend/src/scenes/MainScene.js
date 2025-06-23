import Phaser from 'phaser';
import Tenant from '../objects/Tenant';
import Landlord from '../objects/Landlord';
import ApiService from '../network/ApiService';

export default class MainScene extends Phaser.Scene {
  constructor() {
    super('MainScene');
    this.api = null;
    this.tenant = null;
    this.landlords = [];
    this.currentLandlordId = null;
    this.isNegotiationActive = false;
    this.contractZone = null;
  }

  preload() {
    // Load tileset images
    this.load.image('grass_tile', '../assets/tilesets/grass_tile.png');
    this.load.image('floor_tile', '../assets/tilesets/floor_tile.png');
    this.load.image('path_tile', '../assets/tilesets/path_tile.png');
    this.load.image('special_tile', '../assets/tilesets/special_tile.png');
    
    // Load character spritesheets
    this.load.spritesheet('tenant_idle', '../assets/sprites/tenant_idle.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('tenant_walk_down', '../assets/sprites/tenant_walk_down.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('tenant_walk_up', '../assets/sprites/tenant_walk_up.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('tenant_walk_right', '../assets/sprites/tenant_walk_side.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('tenant_walk_left', '../assets/sprites/tenant_walk_side.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('tenant_celebrate', 'assets/sprites/tenant_celebrate.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('tenant_disappointed', 'assets/sprites/tenant_disappointed.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    
    // Load landlord spritesheets
    this.load.spritesheet('landlord_idle', 'assets/sprites/landlord_idle.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('landlord_walk_down', 'assets/sprites/landlord_walk_down.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('landlord_walk_up', 'assets/sprites/landlord_walk_up.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('landlord_walk_right', 'assets/sprites/landlord_walk_side.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('landlord_walk_left', 'assets/sprites/landlord_walk_side.png', { 
      frameWidth: 32, frameHeight: 32, flip: true 
    });
    this.load.spritesheet('landlord_celebrate', 'assets/sprites/landlord_celebrate.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    this.load.spritesheet('landlord_disappointed', 'assets/sprites/landlord_disappointed.png', { 
      frameWidth: 32, frameHeight: 32 
    });
    
    // Load UI elements
    this.load.image('contract_icon', 'assets/ui/contract_icon.png');
    this.load.image('emotion_agreement', 'assets/ui/emotion_agreement.png');
    this.load.image('emotion_angry', 'assets/ui/emotion_angry.png');
    this.load.image('emotion_confused', 'assets/ui/emotion_confused.png');
    this.load.image('emotion_happy', 'assets/ui/emotion_happy.png');
    this.load.image('emotion_neutral', 'assets/ui/emotion_neutral.png');
    this.load.image('emotion_thinking', 'assets/ui/emotion_thinking.png');
    this.load.image('landlord_icon', 'assets/ui/landlord_icon.png');
    this.load.image('tenant_icon', 'assets/ui/tenant_icon.png');
    this.load.image('system_icon', 'assets/ui/system_icon.png');
  }

  create() {
    // Initialize API service
    this.api = new ApiService(this);
    
    // Create the tilemap
    this.createTilemap();
    
    // Create contract zone
    this.createContractZone();
    
    // Create animations
    this.createAnimations();
    
    // Create tenant
    this.tenant = new Tenant(this, 200, 300);
    
    // Create landlords (3 for example)
    this.createLandlords();
    
    // Connect to WebSocket
    this.api.connectWebSocket();
    
    // Set up event listeners
    this.setupEventListeners();
  }
  
  createTilemap() {
    // Create a simple tilemap using Phaser's array tilemap
    const mapWidth = 25;
    const mapHeight = 19;
    const tileSize = 32;
    
    // Create the map data (0: grass, 1: path, 2: floor, 3: special)
    const mapData = [];
    
    // Fill with grass by default
    for (let y = 0; y < mapHeight; y++) {
      const row = [];
      for (let x = 0; x < mapWidth; x++) {
        row.push(0);
      }
      mapData.push(row);
    }
    
    // Add paths
    for (let x = 5; x < mapWidth - 5; x++) {
      mapData[9][x] = 1;
    }
    for (let y = 5; y < mapHeight - 5; y++) {
      mapData[y][12] = 1;
    }
    
    // Add building floors in different areas
    // Landlord 1 area
    for (let y = 3; y < 7; y++) {
      for (let x = 3; x < 8; x++) {
        mapData[y][x] = 2;
      }
    }
    
    // Landlord 2 area
    for (let y = 3; y < 7; y++) {
      for (let x = 17; x < 22; x++) {
        mapData[y][x] = 2;
      }
    }
    
    // Landlord 3 area
    for (let y = 12; y < 16; y++) {
      for (let x = 17; x < 22; x++) {
        mapData[y][x] = 2;
      }
    }
    
    // Contract signing area
    for (let y = 12; y < 16; y++) {
      for (let x = 3; x < 8; x++) {
        mapData[y][x] = 3;
      }
    }
    
    // Create the map layers
    this.map = {
      width: mapWidth,
      height: mapHeight,
      tileSize: tileSize,
      data: mapData
    };
    
    // Create the tilemap graphics
    for (let y = 0; y < mapHeight; y++) {
      for (let x = 0; x < mapWidth; x++) {
        const tileIndex = mapData[y][x];
        let tileName;
        
        switch (tileIndex) {
          case 0: tileName = 'grass_tile'; break;
          case 1: tileName = 'path_tile'; break;
          case 2: tileName = 'floor_tile'; break;
          case 3: tileName = 'special_tile'; break;
        }
        
        if (tileName) {
          this.add.image(
            x * tileSize + tileSize / 2, 
            y * tileSize + tileSize / 2, 
            tileName
          );
        }
      }
    }
  }
  
  createContractZone() {
    const zoneX = 5.5 * 32;
    const zoneY = 14 * 32;
    
    // Add a contract icon
    const contractIcon = this.add.image(zoneX, zoneY, 'contract_icon');
    contractIcon.setScale(0.5);
    
    // Add a pulsating effect
    this.tweens.add({
      targets: contractIcon,
      scaleX: 0.6,
      scaleY: 0.6,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
      duration: 800
    });
    
    // Save reference to contract zone for movement
    this.contractZone = { x: zoneX, y: zoneY };
  }
  
  createAnimations() {
    // Tenant animations
    this.anims.create({
      key: 'tenant_idle',
      frames: this.anims.generateFrameNumbers('tenant_idle', { start: 0, end: 3 }),
      frameRate: 5,
      repeat: -1
    });
    
    this.anims.create({
      key: 'tenant_walk_down',
      frames: this.anims.generateFrameNumbers('tenant_walk_down', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    this.anims.create({
      key: 'tenant_walk_up',
      frames: this.anims.generateFrameNumbers('tenant_walk_up', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    this.anims.create({
      key: 'tenant_walk_right',
      frames: this.anims.generateFrameNumbers('tenant_walk_right', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    this.anims.create({
      key: 'tenant_walk_left',
      frames: this.anims.generateFrameNumbers('tenant_walk_right', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1,
      flipX: true
    });
    
    this.anims.create({
      key: 'tenant_celebrate',
      frames: this.anims.generateFrameNumbers('tenant_celebrate', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    this.anims.create({
      key: 'tenant_disappointed',
      frames: this.anims.generateFrameNumbers('tenant_disappointed', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    // Landlord animations
    this.anims.create({
      key: 'landlord_idle',
      frames: this.anims.generateFrameNumbers('landlord_idle', { start: 0, end: 3 }),
      frameRate: 5,
      repeat: -1
    });
    
    this.anims.create({
      key: 'landlord_walk_down',
      frames: this.anims.generateFrameNumbers('landlord_walk_down', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    this.anims.create({
      key: 'landlord_walk_up',
      frames: this.anims.generateFrameNumbers('landlord_walk_up', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    this.anims.create({
      key: 'landlord_walk_right',
      frames: this.anims.generateFrameNumbers('landlord_walk_right', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    this.anims.create({
      key: 'landlord_walk_left',
      frames: this.anims.generateFrameNumbers('landlord_walk_left', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1,
      flipX: true
    });
    
    this.anims.create({
      key: 'landlord_celebrate',
      frames: this.anims.generateFrameNumbers('landlord_celebrate', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    this.anims.create({
      key: 'landlord_disappointed',
      frames: this.anims.generateFrameNumbers('landlord_disappointed', { start: 0, end: 3 }),
      frameRate: 8,
      repeat: -1
    });
    
    // Start idle animations
    if (this.tenant) {
      this.tenant.sprite.play('tenant_idle');
    }
  }
  
  createLandlords() {
    // Create three landlords in different positions
    const landlord1 = new Landlord(this, 5.5 * 32, 5 * 32).setId('landlord_1');
    const landlord2 = new Landlord(this, 19.5 * 32, 5 * 32).setId('landlord_2');
    const landlord3 = new Landlord(this, 19.5 * 32, 14 * 32).setId('landlord_3');
    
    // Start idle animations
    landlord1.sprite.play('landlord_idle');
    landlord2.sprite.play('landlord_idle');
    landlord3.sprite.play('landlord_idle');
    
    // Add to the landlords array
    this.landlords = [landlord1, landlord2, landlord3];
  }
  
  setupEventListeners() {
    // Listen for WebSocket events
    this.events.on('ws-agent_started', (data) => {
      this.handleAgentStarted(data);
    });
    
    this.events.on('ws-message_sent', (data) => {
      this.handleMessageSent(data);
    });
    
    this.events.on('ws-agent_thought', (data) => {
      this.handleAgentThought(data);
    });
    
    this.events.on('ws-agent_matched', (data) => {
      this.handleAgentMatched(data);
    });
    
    this.events.on('ws-agreement_reached', () => {
      this.handleAgreementReached();
    });
    
    this.events.on('ws-dialogue_ended', () => {
      this.handleDialogueEnded();
    });
    
    // Listen for button events (handled in main.js)
    this.game.events.on('negotiation-started', () => {
      this.isNegotiationActive = true;
      // Move tenant to center initially
      this.tenant.moveTo(12 * 32, 9 * 32);
    });
    
    this.game.events.on('memory-reset', () => {
      this.resetSimulation();
    });
  }
  
  handleAgentStarted(data) {
    const agentType = data.agent_type;
    
    if (agentType === 'tenant') {
      this.tenant.showEmotion('thinking');
    } else if (agentType === 'landlord' && this.currentLandlordId) {
      const landlord = this.getLandlordById(this.currentLandlordId);
      if (landlord) {
        landlord.showEmotion('thinking');
      }
    }
  }
  
  handleMessageSent(data) {
    const sender = data.sender;
    const content = data.content;
    
    if (sender === 'tenant') {
      this.tenant.showMessage(content);
      
      // Show appropriate emotion based on message content
      if (content.toLowerCase().includes('agree') || content.toLowerCase().includes('accept')) {
        this.tenant.showEmotion('happy');
      } else if (content.toLowerCase().includes('disagree') || content.toLowerCase().includes('reject')) {
        this.tenant.showEmotion('angry');
      } else if (content.toLowerCase().includes('?') || content.toLowerCase().includes('how about')) {
        this.tenant.showEmotion('confused');
      } else {
        this.tenant.showEmotion('neutral');
      }
    } else if (sender === 'landlord' && this.currentLandlordId) {
      const landlord = this.getLandlordById(this.currentLandlordId);
      if (landlord) {
        landlord.showMessage(content);
        
        // Show appropriate emotion based on message content
        if (content.toLowerCase().includes('agree') || content.toLowerCase().includes('accept')) {
          landlord.showEmotion('happy');
        } else if (content.toLowerCase().includes('disagree') || content.toLowerCase().includes('reject')) {
          landlord.showEmotion('angry');
        } else if (content.toLowerCase().includes('?') || content.toLowerCase().includes('how about')) {
          landlord.showEmotion('confused');
        } else {
          landlord.showEmotion('neutral');
        }
      }
    }
  }
  
  handleAgentThought(data) {
    const agentType = data.agent_type;
    const thought = data.thought;
    
    if (agentType === 'tenant') {
      this.tenant.showEmotion('thinking');
    } else if (agentType === 'landlord' && this.currentLandlordId) {
      const landlord = this.getLandlordById(this.currentLandlordId);
      if (landlord) {
        landlord.showEmotion('thinking');
      }
    }
  }
  
  handleAgentMatched(data) {
    this.currentLandlordId = data.landlord_id;
    
    // Find the selected landlord
    const landlord = this.getLandlordById(this.currentLandlordId);
    if (!landlord) return;
    
    // Move tenant to meet the landlord
    const meetingPointX = (landlord.sprite.x + this.tenant.sprite.x) / 2;
    const meetingPointY = (landlord.sprite.y + this.tenant.sprite.y) / 2;
    
    this.tenant.moveTo(meetingPointX, meetingPointY, () => {
      this.tenant.showEmotion('neutral');
      this.tenant.showMessage("Hello! I'm interested in renting a property.");
    });
  }
  
  handleAgreementReached() {
    // Move both to contract zone
    const landlord = this.getLandlordById(this.currentLandlordId);
    if (!landlord) return;
    
    // Move tenant first
    this.tenant.moveTo(this.contractZone.x - 32, this.contractZone.y, () => {
      this.tenant.showEmotion('agreement');
      this.tenant.celebrate();
    });
    
    // Move landlord
    landlord.moveTo(this.contractZone.x + 32, this.contractZone.y, () => {
      landlord.showEmotion('agreement');
      landlord.celebrate();
      
      // Show final message
      this.time.delayedCall(1000, () => {
        const systemMessage = this.add.text(400, 150, 'Agreement reached! Contract signed!', {
          fontFamily: 'Arial',
          fontSize: '24px',
          color: '#00ff00',
          backgroundColor: '#000000',
          padding: { x: 10, y: 5 }
        });
        systemMessage.setOrigin(0.5);
        systemMessage.setDepth(200);
        
        // Enable start button
        document.getElementById('start-btn').disabled = false;
      });
    });
  }
  
  handleDialogueEnded() {
    const landlord = this.getLandlordById(this.currentLandlordId);
    if (!landlord) return;
    
    // Show disappointed animation
    this.tenant.showDisappointment();
    landlord.showDisappointment();
    
    // Show final message
    this.time.delayedCall(1000, () => {
      const systemMessage = this.add.text(400, 150, 'Negotiation failed! No agreement reached.', {
        fontFamily: 'Arial',
        fontSize: '24px',
        color: '#ff0000',
        backgroundColor: '#000000',
        padding: { x: 10, y: 5 }
      });
      systemMessage.setOrigin(0.5);
      systemMessage.setDepth(200);
      
      // Enable start button
      document.getElementById('start-btn').disabled = false;
    });
  }
  
  resetSimulation() {
    // Reset tenant position
    this.tenant.moveTo(200, 300, () => {
      this.tenant.sprite.play('tenant_idle');
    });
    
    // Reset landlords if they moved
    this.landlords[0].moveTo(5.5 * 32, 5 * 32);
    this.landlords[1].moveTo(19.5 * 32, 5 * 32);
    this.landlords[2].moveTo(19.5 * 32, 14 * 32);
    
    // Clear all messages
    this.tenant.hideSpeechBubble();
    this.landlords.forEach(landlord => landlord.hideSpeechBubble());
    
    // Hide all emotions
    this.tenant.emotionIcon.setVisible(false);
    this.landlords.forEach(landlord => landlord.emotionIcon.setVisible(false));
    
    // Remove any system messages
    this.children.list
      .filter(child => child.type === 'Text')
      .forEach(text => text.destroy());
    
    // Reset state
    this.currentLandlordId = null;
    this.isNegotiationActive = false;
  }
  
  getLandlordById(id) {
    return this.landlords.find(landlord => landlord.id === id);
  }
  
  update() {
    // Update all characters
    if (this.tenant) {
      this.tenant.update();
    }
    
    if (this.landlords) {
      this.landlords.forEach(landlord => landlord.update());
    }
  }
}
