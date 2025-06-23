/**
 * Base Character class for both Tenant and Landlord
 */
export class Character {
  constructor(scene, x, y, characterName = 'ada') {
    this.scene = scene;
    this.characterName = characterName;
    this.messageQueue = [];
    this.isMoving = false;
    this.isThinking = false;
    this.emotionIcon = null;
    this.id = null;
    this.data = null;
    this.nameText = null;
    
    // 创建角色精灵，使用atlas纹理
    this.sprite = scene.physics.add.sprite(x, y, characterName, `${characterName}-front`);
    
    // Configure physics
    this.sprite.setCollideWorldBounds(true);
    this.sprite.setDepth(10); // 确保角色在背景之上
    
    // 开始空闲动画
    if (scene.anims.exists(`${characterName}_idle`)) {
      this.sprite.play(`${characterName}_idle`);
    }
    
    // Speech bubble container
    this.speechBubble = {
      container: null,
      background: null,
      text: null,
      timer: null
    };
  }
  
  setId(id) {
    this.id = id;
    return this;
  }
  
  setData(data) {
    this.data = data;
    return this;
  }
  
  setCharacterName(name) {
    this.characterName = name;
    return this;
  }
  
  /**
   * Show a speech bubble with the specified message
   */
  showMessage(message, duration = 5000) {
    // If there's already a message showing, queue this one
    if (this.speechBubble.container && this.speechBubble.container.visible) {
      this.messageQueue.push({ message, duration });
      return;
    }
    
    // Create speech bubble if it doesn't exist
    if (!this.speechBubble.container) {
      this.createSpeechBubble(message);
    } else {
      // Update existing speech bubble
      this.speechBubble.text.setText(message);
      this.speechBubble.container.setVisible(true);
      
      // Resize the background
      const bounds = this.speechBubble.text.getBounds();
      this.speechBubble.background.setSize(
        bounds.width + 20, 
        bounds.height + 20
      );
    }
    
    // Position the bubble above the character
    this.updateSpeechBubblePosition();
    
    // Hide the bubble after duration
    if (this.speechBubble.timer) {
      this.speechBubble.timer.remove();
    }
    
    this.speechBubble.timer = this.scene.time.delayedCall(duration, () => {
      this.hideSpeechBubble();
      
      // Process next message in queue if any
      if (this.messageQueue.length > 0) {
        const nextMessage = this.messageQueue.shift();
        this.showMessage(nextMessage.message, nextMessage.duration);
      }
    });
  }
  
  /**
   * Create a new speech bubble
   */
  createSpeechBubble(message) {
    // Create container
    this.speechBubble.container = this.scene.add.container(
      this.sprite.x,
      this.sprite.y - 80
    );
    
    // Create background
    this.speechBubble.background = this.scene.add.graphics();
    this.speechBubble.background.fillStyle(0xffffff, 0.8);
    this.speechBubble.background.lineStyle(2, 0x000000, 1);
    
    // Create text
    this.speechBubble.text = this.scene.add.text(0, 0, message, {
      fontFamily: 'Arial',
      fontSize: '14px',
      color: '#000000',
      wordWrap: { width: 150 }
    });
    this.speechBubble.text.setOrigin(0.5);
    
    // Set background size based on text
    const bounds = this.speechBubble.text.getBounds();
    this.speechBubble.background.fillRoundedRect(
      -bounds.width / 2 - 10,
      -bounds.height / 2 - 10,
      bounds.width + 20,
      bounds.height + 20,
      8
    );
    this.speechBubble.background.strokeRoundedRect(
      -bounds.width / 2 - 10,
      -bounds.height / 2 - 10,
      bounds.width + 20,
      bounds.height + 20,
      8
    );
    
    // Add components to container
    this.speechBubble.container.add([
      this.speechBubble.background,
      this.speechBubble.text
    ]);
    
    // Add pointer to speech bubble
    const pointer = this.scene.add.graphics();
    pointer.fillStyle(0xffffff, 0.8);
    pointer.lineStyle(2, 0x000000, 1);
    pointer.beginPath();
    pointer.moveTo(-10, bounds.height / 2 + 10);
    pointer.lineTo(0, bounds.height / 2 + 25);
    pointer.lineTo(10, bounds.height / 2 + 10);
    pointer.closePath();
    pointer.fillPath();
    pointer.strokePath();
    this.speechBubble.container.add(pointer);
    
    // Set depth to ensure it appears above characters
    this.speechBubble.container.setDepth(100);
  }
  
  /**
   * Hide the speech bubble
   */
  hideSpeechBubble() {
    if (this.speechBubble.container) {
      this.speechBubble.container.setVisible(false);
    }
  }
  
  /**
   * Update the speech bubble position to follow the character
   */
  updateSpeechBubblePosition() {
    if (this.speechBubble.container) {
      this.speechBubble.container.setPosition(
        this.sprite.x,
        this.sprite.y - 80
      );
    }
  }
  
  /**
   * Show an emotion above the character
   */
  showEmotion(emotion, duration = 3000) {
    // Create emotion text instead of icon
    const emotionEmojis = {
      'happy': '😊',
      'angry': '😠',
      'confused': '😕',
      'thinking': '🤔',
      'neutral': '😐',
      'agreement': '🤝'
    };
    
    const emoji = emotionEmojis[emotion] || '😐';
    
    // Remove existing emotion text
    if (this.emotionText) {
      this.emotionText.destroy();
    }
    
    // Create new emotion text
    this.emotionText = this.scene.add.text(this.sprite.x, this.sprite.y - 50, emoji, {
      fontSize: '16px'
    }).setOrigin(0.5);
    this.emotionText.setDepth(20);
    
    // Hide the emotion text after duration
    this.scene.time.delayedCall(duration, () => {
      if (this.emotionText) {
        this.emotionText.destroy();
        this.emotionText = null;
      }
    });
  }
  
  /**
   * Update the emotion icon position to follow the character
   */
  updateEmotionIconPosition() {
    if (this.emotionIcon) {
      this.emotionIcon.setPosition(
        this.sprite.x,
        this.sprite.y - 40
      );
    }
  }
  
  /**
   * Move the character to a new position
   */
  moveTo(x, y, onComplete = null) {
    if (this.isMoving) return false;
    
    this.isMoving = true;
    
    // Calculate the direction and distance
    const dx = x - this.sprite.x;
    const dy = y - this.sprite.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    // Calculate the duration based on distance and speed (pixels per second)
    const speed = 100;
    const duration = (distance / speed) * 1000;
    
    // Determine the animation to play
    let anim = `${this.characterName}_idle`;
    if (Math.abs(dx) > Math.abs(dy)) {
      // Moving more horizontally
      anim = dx > 0 ? `${this.characterName}_walk_right` : `${this.characterName}_walk_left`;
    } else {
      // Moving more vertically
      anim = dy > 0 ? `${this.characterName}_walk_front` : `${this.characterName}_walk_back`;
    }
    
    // Play the animation if it exists
    if (this.scene.anims.exists(anim)) {
      this.sprite.play(anim);
    }
    
    // Update name text position
    if (this.nameText) {
      this.scene.tweens.add({
        targets: this.nameText,
        x: x,
        y: y - 30,
        duration: duration,
        ease: 'Linear'
      });
    }
    
    // Create the tween
    this.scene.tweens.add({
      targets: this.sprite,
      x: x,
      y: y,
      duration: duration,
      ease: 'Linear',
      onUpdate: () => {
        this.updateSpeechBubblePosition();
      },
      onComplete: () => {
        const idleAnim = `${this.characterName}_idle`;
        if (this.scene.anims.exists(idleAnim)) {
          this.sprite.play(idleAnim);
        }
        this.isMoving = false;
        
        if (onComplete) {
          onComplete();
        }
      }
    });
    
    return true;
  }
  
  /**
   * Play a celebration animation
   */
  celebrate() {
    this.sprite.play(`${this.type}_celebrate`);
    this.showEmotion('happy', 5000);
  }
  
  /**
   * Play a disappointed animation
   */
  showDisappointment() {
    this.sprite.play(`${this.type}_disappointed`);
    this.showEmotion('angry', 5000);
  }
  
  /**
   * Update the character
   */
  update() {
    // Any per-frame updates could go here
  }
}

/**
 * Tenant character class
 */
export default class Tenant extends Character {
  constructor(scene, x, y, characterName = 'ada') {
    super(scene, x, y, characterName);
    this.type = 'tenant';
    
    // Set appropriate scale for the character
    this.sprite.setScale(1.5);
  }
}
