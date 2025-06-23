/**
 * Base Character class for both Tenant and Landlord
 */
export class Character {
  constructor(scene, x, y, texture, frame) {
    this.sprite = scene.physics.add.sprite(x, y, texture, frame);
    this.scene = scene;
    this.messageQueue = [];
    this.isMoving = false;
    this.isThinking = false;
    this.emotionIcon = null;
    
    // Configure physics
    this.sprite.setCollideWorldBounds(true);
    
    // Create emotion icon (hidden by default)
    this.emotionIcon = scene.add.sprite(x, y - 40, 'emotion_neutral');
    this.emotionIcon.setVisible(false);
    this.emotionIcon.setScale(0.5);
    
    // Speech bubble container
    this.speechBubble = {
      container: null,
      background: null,
      text: null,
      timer: null
    };
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
   * Show an emotion icon above the character
   */
  showEmotion(emotion, duration = 3000) {
    // Map the emotion to the corresponding texture
    const emotionMap = {
      happy: 'emotion_happy',
      angry: 'emotion_angry',
      confused: 'emotion_confused',
      neutral: 'emotion_neutral',
      thinking: 'emotion_thinking',
      agreement: 'emotion_agreement'
    };
    
    const texture = emotionMap[emotion] || 'emotion_neutral';
    
    // Set the emotion icon texture
    this.emotionIcon.setTexture(texture);
    this.emotionIcon.setVisible(true);
    
    // Position the emotion icon above the character
    this.updateEmotionIconPosition();
    
    // Hide the emotion icon after duration
    this.scene.time.delayedCall(duration, () => {
      this.emotionIcon.setVisible(false);
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
    let anim = '';
    if (Math.abs(dx) > Math.abs(dy)) {
      // Moving more horizontally
      anim = dx > 0 ? `${this.type}_walk_right` : `${this.type}_walk_left`;
    } else {
      // Moving more vertically
      anim = dy > 0 ? `${this.type}_walk_down` : `${this.type}_walk_up`;
    }
    
    // Play the animation
    this.sprite.play(anim);
    
    // Create the tween
    this.scene.tweens.add({
      targets: this.sprite,
      x: x,
      y: y,
      duration: duration,
      ease: 'Linear',
      onUpdate: () => {
        this.updateSpeechBubblePosition();
        this.updateEmotionIconPosition();
      },
      onComplete: () => {
        this.sprite.play(`${this.type}_idle`);
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
  constructor(scene, x, y) {
    super(scene, x, y, 'tenant_idle', 0);
    this.type = 'tenant';
    
    // Set the scale if needed
    this.sprite.setScale(2);
  }
}
