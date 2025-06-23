import Phaser from 'phaser';
import Tenant from '../objects/Tenant';
import Landlord from '../objects/Landlord';
import ApiService from '../network/ApiService';
import GoogleMapsService from '../services/GoogleMapsService';

export default class MainScene extends Phaser.Scene {
  constructor() {
    super('MainScene');
    this.api = null;
    this.tenants = [];
    this.landlords = [];
    this.properties = [];
    this.mapData = [];
    this.propertyMarkers = [];
    this.currentSessions = [];
    this.isNegotiationActive = false;
    this.contractZone = null;
    this.systemInitialized = false;
    this.googleMaps = new GoogleMapsService();
    this.mapBackground = null;
    this.mapBounds = null;
    this.useNonGoogleMap = false;
    this.googleMapsAvailable = false;
    this.googleMapUrl = null;
  }

  preload() {
    // 定义可用的哲学家角色
    this.characterNames = [
      'ada', 'aristotle', 'chomsky', 'dennett', 'descartes', 
      'leibniz', 'miguel', 'paul', 'plato', 'searle', 
      'socrates', 'sophia', 'turing'
    ];
    
    // 加载所有角色的纹理集
    this.characterNames.forEach(name => {
      this.load.atlas(name, `assets/characters/${name}/atlas.png`, `assets/characters/${name}/atlas.json`);
    });
    
    // 设置CORS
    this.load.crossOrigin = 'anonymous';
  }
  
  initializeGoogleMaps() {
    // 首先创建fallback地图
    this.createLondonMap();
    
    // 然后异步加载Google Maps
    this.googleMaps.loadConfig().then(apiKey => {
      console.log('Google Maps API key loaded:', apiKey);
      
      // 现在加载伦敦地图
      return this.googleMaps.createLondonMap({
        size: '800x600',
        zoom: 11,
        maptype: 'roadmap'
      });
    }).then(londonMapUrl => {
      console.log('London map URL created:', londonMapUrl);
      
      // 设置标志表示Google Maps可用
      this.googleMapsAvailable = true;
      this.googleMapUrl = londonMapUrl;
      
      // 直接用Image加载，然后创建纹理
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        console.log('Google Maps image loaded, creating texture');
        
        // 创建纹理
        this.textures.addImage('london_map', img);
        
        // 更新地图显示
        this.updateMapDisplay();
      };
      img.onerror = (error) => {
        console.error('Failed to load Google Maps image:', error);
      };
      img.src = londonMapUrl;
      
    }).catch(error => {
      console.error('Failed to initialize Google Maps:', error);
      // 设置标志，使用备用地图
      this.useNonGoogleMap = true;
      this.googleMapsAvailable = false;
    });
  }
  
  updateMapDisplay() {
    // 如果Google Maps纹理已加载，更新显示
    if (this.googleMapsAvailable && this.textures.exists('london_map')) {
      // 如果当前显示的是fallback地图，替换它
      if (this.mapBackground && this.mapBackground.texture.key !== 'london_map') {
        this.mapBackground.destroy();
        this.mapBackground = this.add.image(400, 300, 'london_map');
        this.mapBackground.setDisplaySize(800, 600);
        this.mapBackground.setDepth(0);
        console.log('Replaced fallback map with Google Maps');
      }
    }
  }

  create() {
    // Initialize API service
    this.api = new ApiService(this);
    
    // Initialize Google Maps first, then create the map
    this.initializeGoogleMaps();
    
    // Create animations for all characters
    this.createAllCharacterAnimations();
    
    // Connect to WebSocket
    this.api.connectWebSocket();
    
    // Set up event listeners
    this.setupEventListeners();
  }
  
  createLondonMap() {
    // 设置地图边界（伦敦区域）
    this.mapBounds = this.googleMaps.getLondonBounds();
    
    // 检查是否应该使用备用地图或Google地图是否已加载
    if (this.useNonGoogleMap || !this.textures.exists('london_map')) {
      console.log('Using fallback map - Google Maps not available');
      this.createFallbackMap();
    } else {
      // 添加Google Maps背景图像
      try {
        this.mapBackground = this.add.image(400, 300, 'london_map');
        this.mapBackground.setDisplaySize(800, 600);
        this.mapBackground.setDepth(0); // 确保在最底层
        
        console.log('Google Maps background loaded successfully');
      } catch (error) {
        console.warn('Failed to load Google Maps background, using fallback:', error);
        this.createFallbackMap();
        return; // 返回，避免重复添加覆盖层
      }
    }
    
    // 添加半透明覆盖层来降低背景亮度，突出角色
    const overlay = this.add.rectangle(400, 300, 800, 600, 0x000000, 0.2);
    overlay.setDepth(1);
    
    // 添加地图标题
    this.add.text(400, 30, 'London Rental Properties Map', {
      fontSize: '20px',
      fill: '#ffffff',
      backgroundColor: '#000000',
      padding: { x: 10, y: 5 }
    }).setOrigin(0.5).setDepth(50);
  }
  
  createFallbackMap() {
    // 备用地图（如果Google Maps加载失败）
    this.mapBackground = this.add.rectangle(400, 300, 800, 600, 0x2a3f2a);
    this.mapBackground.setDepth(0);
    
    // 添加简单的地标标识
    const landmarks = [
      { name: 'Westminster', x: 350, y: 320 },
      { name: 'City of London', x: 450, y: 280 },
      { name: 'Camden', x: 400, y: 200 },
      { name: 'Greenwich', x: 550, y: 400 },
      { name: 'Canary Wharf', x: 500, y: 320 }
    ];
    
    landmarks.forEach(landmark => {
      this.add.circle(landmark.x, landmark.y, 3, 0xffffff).setDepth(5);
      this.add.text(landmark.x, landmark.y - 15, landmark.name, {
        fontSize: '10px',
        fill: '#ffffff',
        backgroundColor: '#000000',
        padding: { x: 2, y: 1 }
      }).setOrigin(0.5).setDepth(5);
    });
    
    console.log('Fallback map created successfully');
  }
  
  createAllCharacterAnimations() {
    // 为每个角色创建动画
    this.characterNames.forEach(characterName => {
      // 创建基本动画（空闲、行走等）
      this.createCharacterAnimations(characterName);
    });
  }
  
  createCharacterAnimations(characterName) {
    // 为特定角色创建动画集
    const animationsToCreate = [
      { suffix: 'idle', frames: [`${characterName}-front`], frameRate: 2 },
      { suffix: 'walk_front', frames: [`${characterName}-front-walk-0000`, `${characterName}-front-walk-0001`, `${characterName}-front-walk-0002`, `${characterName}-front-walk-0003`], frameRate: 8 },
      { suffix: 'walk_back', frames: [`${characterName}-back-walk-0000`, `${characterName}-back-walk-0001`, `${characterName}-back-walk-0002`, `${characterName}-back-walk-0003`], frameRate: 8 },
      { suffix: 'walk_left', frames: [`${characterName}-left-walk-0000`, `${characterName}-left-walk-0001`, `${characterName}-left-walk-0002`, `${characterName}-left-walk-0003`], frameRate: 8 },
      { suffix: 'walk_right', frames: [`${characterName}-right-walk-0000`, `${characterName}-right-walk-0001`, `${characterName}-right-walk-0002`, `${characterName}-right-walk-0003`], frameRate: 8 }
    ];
    
    animationsToCreate.forEach(anim => {
      const key = `${characterName}_${anim.suffix}`;
      
      // 检查动画是否已存在
      if (!this.anims.exists(key)) {
        try {
          this.anims.create({
            key: key,
            frames: anim.frames.map(frame => ({ key: characterName, frame: frame })),
            frameRate: anim.frameRate,
            repeat: -1
          });
        } catch (error) {
          // 如果特定帧不存在，使用备用帧
          console.warn(`Animation frames not found for ${key}, using fallback`);
          this.anims.create({
            key: key,
            frames: [{ key: characterName, frame: `${characterName}-front` }],
            frameRate: 2,
            repeat: -1
          });
        }
      }
    });
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
    this.game.events.on('system-initialized', (result) => {
      this.handleSystemInitialized(result);
    });
    
    this.game.events.on('negotiation-started', (result) => {
      this.isNegotiationActive = true;
      console.log('Negotiation started in MainScene:', result);
      this.currentSessions = result.sessions || [];
      // Start negotiation animations
      this.startNegotiationAnimations();
    });
    
    this.game.events.on('memory-reset', () => {
      this.resetSimulation();
    });
  }
  
  handleSystemInitialized(result) {
    console.log('System initialized:', result);
    this.systemInitialized = true;
    
    // Store the data
    this.mapData = result.data.map_data || [];
    this.properties = result.data.properties || [];
    
    // Clear existing objects
    this.clearGameObjects();
    
    // Create property markers on the map
    this.createPropertyMarkers();
    
    // Create tenants based on the data
    this.createTenantsFromData(result.data.tenants || []);
    
    // Create landlords at property locations
    this.createLandlordsFromData(result.data.landlords || []);
  }
  
  clearGameObjects() {
    // Clear existing tenants
    this.tenants.forEach(tenant => {
      if (tenant.sprite) tenant.sprite.destroy();
      if (tenant.speechBubble && tenant.speechBubble.container) tenant.speechBubble.container.destroy();
      if (tenant.emotionText) tenant.emotionText.destroy();
      if (tenant.nameText) tenant.nameText.destroy();
    });
    this.tenants = [];
    
    // Clear existing landlords
    this.landlords.forEach(landlord => {
      if (landlord.sprite) landlord.sprite.destroy();
      if (landlord.speechBubble && landlord.speechBubble.container) landlord.speechBubble.container.destroy();
      if (landlord.emotionText) landlord.emotionText.destroy();
      if (landlord.nameText) landlord.nameText.destroy();
    });
    this.landlords = [];
    
    // Clear property markers
    this.propertyMarkers.forEach(marker => marker.destroy());
    this.propertyMarkers = [];
  }
  
  createPropertyMarkers() {
    if (!this.mapData || this.mapData.length === 0) return;
    
    // 使用伦敦的实际边界
    const bounds = this.mapBounds || this.googleMaps.getLondonBounds();
    
    this.mapData.forEach((property, index) => {
      // Convert GPS coordinates to screen coordinates
      const coords = this.googleMaps.latLngToScreenCoordinates(
        property.latitude, 
        property.longitude, 
        bounds, 
        800, 
        600
      );
      
      // Create property marker (house icon with better visibility)
      const marker = this.add.graphics();
      marker.fillStyle(0xff4444); // Bright red for properties
      marker.lineStyle(2, 0xffffff); // White border
      
      // Draw house shape
      marker.fillRect(coords.x - 8, coords.y - 6, 16, 12);
      marker.fillTriangle(coords.x - 10, coords.y - 6, coords.x + 10, coords.y - 6, coords.x, coords.y - 16);
      marker.strokeRect(coords.x - 8, coords.y - 6, 16, 12);
      marker.strokeTriangle(coords.x - 10, coords.y - 6, coords.x + 10, coords.y - 6, coords.x, coords.y - 16);
      
      marker.setDepth(15); // 确保在角色之上
      
      // Add property info
      marker.setInteractive(new Phaser.Geom.Rectangle(coords.x - 10, coords.y - 16, 20, 22), Phaser.Geom.Rectangle.Contains);
      marker.on('pointerover', () => {
        this.showPropertyInfo(property, coords.x, coords.y);
      });
      marker.on('pointerout', () => {
        this.hidePropertyInfo();
      });
      
      // Add property price label
      const priceText = this.add.text(coords.x, coords.y + 15, `£${property.price}`, {
        fontSize: '8px',
        fill: '#ffffff',
        backgroundColor: '#ff4444',
        padding: { x: 2, y: 1 }
      }).setOrigin(0.5).setDepth(15);
      
      this.propertyMarkers.push(marker);
      this.propertyMarkers.push(priceText);
    });
  }
  
  showPropertyInfo(property, x, y) {
    this.hidePropertyInfo(); // Clear any existing info
    
    this.propertyInfoText = this.add.text(x, y - 30, 
      `${property.address}\n£${property.price}/month\n${property.bedrooms} bed`, {
      fontFamily: 'Arial',
      fontSize: '12px',
      color: '#ffffff',
      backgroundColor: '#000000',
      padding: { x: 5, y: 3 }
    });
    this.propertyInfoText.setOrigin(0.5, 1);
    this.propertyInfoText.setDepth(100);
  }
  
  hidePropertyInfo() {
    if (this.propertyInfoText) {
      this.propertyInfoText.destroy();
      this.propertyInfoText = null;
    }
  }
  
  createTenantsFromData(tenantsData) {
    // 随机分配哲学家角色给租客
    const availableCharacters = [...this.characterNames];
    const bounds = this.mapBounds || this.googleMaps.getLondonBounds();
    
    // 定义伦敦的一些知名区域坐标，用于放置租客
    const londonAreas = [
      { lat: 51.5074, lng: -0.1278, name: 'Central London' },      // 市中心
      { lat: 51.5155, lng: -0.1419, name: 'Oxford Street' },       // 牛津街
      { lat: 51.5033, lng: -0.1195, name: 'Westminster' },         // 威斯敏斯特
      { lat: 51.5144, lng: -0.0875, name: 'The City' },           // 金融城
      { lat: 51.4995, lng: -0.1248, name: 'South Bank' },         // 南岸
      { lat: 51.5194, lng: -0.1270, name: 'Fitzrovia' },          // 菲茨罗维亚
      { lat: 51.4893, lng: -0.1334, name: 'Vauxhall' },           // 沃克斯豪尔
      { lat: 51.5092, lng: -0.0955, name: 'Borough' },            // 博罗市场
    ];
    
    tenantsData.forEach((tenantData, index) => {
      // 随机选择一个角色
      const characterIndex = Math.floor(Math.random() * availableCharacters.length);
      const characterName = availableCharacters.splice(characterIndex, 1)[0];
      
      // 为每个租客选择一个伦敦区域
      const area = londonAreas[index % londonAreas.length];
      
      // 在选定区域附近添加一些随机偏移
      const offsetLat = (Math.random() - 0.5) * 0.01; // 约1km范围内的偏移
      const offsetLng = (Math.random() - 0.5) * 0.01;
      
      const coords = this.googleMaps.latLngToScreenCoordinates(
        area.lat + offsetLat,
        area.lng + offsetLng,
        bounds,
        800,
        600
      );
      
      const tenant = new Tenant(this, coords.x, coords.y, characterName);
      tenant.setId(tenantData.tenant_id);
      tenant.setData(tenantData);
      tenant.setCharacterName(characterName);
      this.tenants.push(tenant);
      
      // 添加名称标签
      const nameText = this.add.text(coords.x, coords.y - 35, tenantData.name || characterName, {
        fontSize: '9px',
        fill: '#00ff88',
        backgroundColor: '#000000',
        padding: { x: 3, y: 2 }
      }).setOrigin(0.5).setDepth(20);
      
      tenant.nameText = nameText;
    });
  }
  
  createLandlordsFromData(landlordsData) {
    // 在房产附近放置房东
    const usedCharacters = this.tenants.map(t => t.characterName);
    const availableCharacters = this.characterNames.filter(name => !usedCharacters.includes(name));
    const bounds = this.mapBounds || this.googleMaps.getLondonBounds();
    
    landlordsData.forEach((landlordData, index) => {
      // 随机选择角色
      const characterIndex = Math.floor(Math.random() * availableCharacters.length);
      const characterName = availableCharacters.splice(characterIndex, 1)[0] || this.characterNames[0];
      
      // 在地图上的房产位置附近放置房东
      const propertiesForLandlord = this.mapData.filter(prop => prop.landlord_id === landlordData.landlord_id);
      
      let coords = { x: 100 + (index * 120), y: 500 }; // 默认位置
      
      if (propertiesForLandlord.length > 0) {
        // 找到房产的平均位置
        const avgLat = propertiesForLandlord.reduce((sum, prop) => sum + prop.latitude, 0) / propertiesForLandlord.length;
        const avgLng = propertiesForLandlord.reduce((sum, prop) => sum + prop.longitude, 0) / propertiesForLandlord.length;
        
        // 添加一些偏移，让房东不直接在房产上
        const offsetLat = (Math.random() - 0.5) * 0.008; // 约800m偏移
        const offsetLng = (Math.random() - 0.5) * 0.008;
        
        coords = this.googleMaps.latLngToScreenCoordinates(
          avgLat + offsetLat,
          avgLng + offsetLng,
          bounds,
          800,
          600
        );
      }
      
      const landlord = new Landlord(this, coords.x, coords.y, characterName);
      landlord.setId(landlordData.landlord_id);
      landlord.setData(landlordData);
      landlord.setCharacterName(characterName);
      this.landlords.push(landlord);
      
      // 添加名称标签
      const nameText = this.add.text(coords.x, coords.y - 35, landlordData.name || characterName, {
        fontSize: '9px',
        fill: '#ff8844',
        backgroundColor: '#000000',
        padding: { x: 3, y: 2 }
      }).setOrigin(0.5).setDepth(20);
      
      landlord.nameText = nameText;
      
      // 如果房东有房产，用线连接到房产
      if (propertiesForLandlord.length > 0) {
        propertiesForLandlord.forEach(property => {
          const propCoords = this.googleMaps.latLngToScreenCoordinates(
            property.latitude,
            property.longitude,
            bounds,
            800,
            600
          );
          
          // 画一条虚线连接房东和房产
          const line = this.add.graphics();
          line.lineStyle(1, 0xffaa44, 0.5);
          line.setLineDash([3, 3]);
          line.moveTo(coords.x, coords.y);
          line.lineTo(propCoords.x, propCoords.y);
          line.strokePath();
          line.setDepth(2);
          
          this.propertyMarkers.push(line);
        });
      }
    });
  }
  
  startNegotiationAnimations() {
    // Move tenants to start positions and begin animations
    this.currentSessions.forEach((session, index) => {
      const tenant = this.tenants.find(t => t.data && t.data.tenant_id === session.tenant_name);
      if (tenant) {
        // Move tenant to center area
        const targetX = 300 + (index * 50);
        const targetY = 300;
        tenant.moveTo(targetX, targetY);
      }
    });
  }
  
  handleAgentStarted(data) {
    const agentType = data.agent_type;
    
    if (agentType === 'tenant' && this.tenants.length > 0) {
      // Show thinking emotion for the first tenant (or find specific tenant)
      this.tenants[0].showEmotion('thinking');
    } else if (agentType === 'landlord' && this.landlords.length > 0) {
      // Show thinking emotion for landlords
      this.landlords[0].showEmotion('thinking');
    }
  }
  
  handleMessageSent(data) {
    const sender = data.sender;
    const content = data.content;
    
    if (sender === 'tenant' && this.tenants.length > 0) {
      // Find the appropriate tenant or use the first one
      const tenant = this.tenants[0];
      tenant.showMessage(content);
      
      // Show appropriate emotion based on message content
      if (content.toLowerCase().includes('agree') || content.toLowerCase().includes('accept')) {
        tenant.showEmotion('happy');
      } else if (content.toLowerCase().includes('disagree') || content.toLowerCase().includes('reject')) {
        tenant.showEmotion('angry');
      } else if (content.toLowerCase().includes('?') || content.toLowerCase().includes('how about')) {
        tenant.showEmotion('confused');
      } else {
        tenant.showEmotion('neutral');
      }
    } else if (sender === 'landlord' && this.landlords.length > 0) {
      const landlord = this.landlords[0];
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
    if (this.tenants) {
      this.tenants.forEach(tenant => tenant.update());
    }
    
    if (this.landlords) {
      this.landlords.forEach(landlord => landlord.update());
    }
  }
}
