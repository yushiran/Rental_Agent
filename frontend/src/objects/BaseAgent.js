/**
 * BaseAgent - 基础智能体类
 * 为租客和房东提供共同的基础功能
 */
class BaseAgent {
    constructor(id, type, data, scene) {
        this.id = id;
        this.type = type;
        this.data = data;
        this.scene = scene;
        
        // 视觉属性
        this.sprite = null;
        this.nameText = null;
        this.statusText = null;
        this.speechBubble = null;
        this.thoughtBubble = null;
        
        // 状态属性
        this.position = data.location || { x: 400, y: 300 };
        this.currentAnimation = 'idle';
        this.currentEmotion = 'neutral';
        this.isVisible = true;
        
        // 动画队列
        this.animationQueue = [];
        this.isAnimating = false;
        
        this.createVisuals();
    }

    /**
     * 创建视觉元素
     */
    createVisuals() {
        // 创建精灵
        this.sprite = this.scene.add.rectangle(
            this.position.x, 
            this.position.y, 
            40, 60, 
            this.getAgentColor()
        );
        this.sprite.setStrokeStyle(2, 0x000000);
        
        // 创建名称文本
        this.nameText = this.scene.add.text(
            this.position.x, 
            this.position.y - 40, 
            this.data.name || this.id,
            {
                fontSize: '12px',
                fill: '#000000',
                backgroundColor: '#ffffff',
                padding: { x: 4, y: 2 }
            }
        ).setOrigin(0.5);
        
        // 创建状态文本
        this.statusText = this.scene.add.text(
            this.position.x, 
            this.position.y + 40, 
            '空闲',
            {
                fontSize: '10px',
                fill: '#666666'
            }
        ).setOrigin(0.5);
        
        this.updateVisibility();
    }

    /**
     * 获取智能体颜色
     */
    getAgentColor() {
        return this.type === 'tenant' ? 0x4CAF50 : 0x2196F3;
    }

    /**
     * 更新位置
     */
    setPosition(x, y) {
        this.position = { x, y };
        if (this.sprite) {
            this.sprite.setPosition(x, y);
            this.nameText.setPosition(x, y - 40);
            this.statusText.setPosition(x, y + 40);
            
            // 更新气泡位置
            if (this.speechBubble) {
                this.speechBubble.setPosition(x, y - 60);
            }
            if (this.thoughtBubble) {
                this.thoughtBubble.setPosition(x + 50, y - 30);
            }
        }
    }

    /**
     * 移动到指定位置
     */
    moveTo(targetX, targetY, duration = 1000) {
        if (!this.sprite) return;
        
        this.setStatus('移动中');
        this.currentAnimation = 'walking';
        
        this.scene.tweens.add({
            targets: [this.sprite, this.nameText, this.statusText],
            x: targetX,
            y: (target) => {
                if (target === this.nameText) return targetY - 40;
                if (target === this.statusText) return targetY + 40;
                return targetY;
            },
            duration: duration,
            ease: 'Power2',
            onComplete: () => {
                this.position = { x: targetX, y: targetY };
                this.setStatus('空闲');
                this.currentAnimation = 'idle';
            }
        });
    }

    /**
     * 设置状态文本
     */
    setStatus(status) {
        if (this.statusText) {
            this.statusText.setText(status);
        }
    }

    /**
     * 显示对话气泡
     */
    showSpeechBubble(content, duration = 3000) {
        this.hideSpeechBubble();
        
        // 创建气泡背景
        const bubbleWidth = Math.min(content.length * 8 + 20, 200);
        const bubbleHeight = 40;
        
        this.speechBubble = this.scene.add.group();
        
        const bubble = this.scene.add.rectangle(
            this.position.x, 
            this.position.y - 60, 
            bubbleWidth, 
            bubbleHeight, 
            0xffffff
        );
        bubble.setStrokeStyle(2, 0x000000);
        
        const text = this.scene.add.text(
            this.position.x, 
            this.position.y - 60, 
            content,
            {
                fontSize: '10px',
                fill: '#000000',
                wordWrap: { width: bubbleWidth - 10 }
            }
        ).setOrigin(0.5);
        
        this.speechBubble.add([bubble, text]);
        
        // 自动隐藏
        this.scene.time.delayedCall(duration, () => {
            this.hideSpeechBubble();
        });
        
        // 动画效果
        this.speechBubble.setAlpha(0);
        this.scene.tweens.add({
            targets: this.speechBubble.getChildren(),
            alpha: 1,
            duration: 300,
            ease: 'Power2'
        });
    }

    /**
     * 隐藏对话气泡
     */
    hideSpeechBubble() {
        if (this.speechBubble) {
            this.speechBubble.destroy();
            this.speechBubble = null;
        }
    }

    /**
     * 显示思考气泡
     */
    showThoughtBubble(content, duration = 3000) {
        this.hideThoughtBubble();
        
        const bubbleWidth = Math.min(content.length * 6 + 20, 150);
        const bubbleHeight = 30;
        
        this.thoughtBubble = this.scene.add.group();
        
        const bubble = this.scene.add.ellipse(
            this.position.x + 50, 
            this.position.y - 30, 
            bubbleWidth, 
            bubbleHeight, 
            0xf0f0f0
        );
        bubble.setStrokeStyle(1, 0x666666);
        
        const text = this.scene.add.text(
            this.position.x + 50, 
            this.position.y - 30, 
            content,
            {
                fontSize: '9px',
                fill: '#666666',
                wordWrap: { width: bubbleWidth - 10 }
            }
        ).setOrigin(0.5);
        
        this.thoughtBubble.add([bubble, text]);
        
        // 自动隐藏
        this.scene.time.delayedCall(duration, () => {
            this.hideThoughtBubble();
        });
        
        // 动画效果
        this.thoughtBubble.setAlpha(0);
        this.scene.tweens.add({
            targets: this.thoughtBubble.getChildren(),
            alpha: 1,
            duration: 300,
            ease: 'Power2'
        });
    }

    /**
     * 隐藏思考气泡
     */
    hideThoughtBubble() {
        if (this.thoughtBubble) {
            this.thoughtBubble.destroy();
            this.thoughtBubble = null;
        }
    }

    /**
     * 设置情绪
     */
    setEmotion(emotion) {
        this.currentEmotion = emotion;
        
        // 根据情绪改变颜色
        let color = this.getAgentColor();
        switch (emotion) {
            case 'happy': color = 0x8BC34A; break;
            case 'excited': color = 0xFF9800; break;
            case 'confused': color = 0x9E9E9E; break;
            case 'disappointed': color = 0x607D8B; break;
            case 'frustrated': color = 0xFF5722; break;
        }
        
        if (this.sprite) {
            this.sprite.setFillStyle(color);
        }
    }

    /**
     * 播放动画
     */
    playAnimation(animationType, emotion = null) {
        this.currentAnimation = animationType;
        
        if (emotion) {
            this.setEmotion(emotion);
        }
        
        switch (animationType) {
            case 'talking':
                this.animateTalking();
                break;
            case 'thinking':
                this.animateThinking();
                break;
            case 'excited':
                this.animateExcited();
                break;
        }
    }

    /**
     * 说话动画
     */
    animateTalking() {
        if (!this.sprite) return;
        
        this.scene.tweens.add({
            targets: this.sprite,
            scaleX: 1.1,
            scaleY: 1.1,
            duration: 500,
            yoyo: true,
            repeat: 2,
            ease: 'Power2'
        });
    }

    /**
     * 思考动画
     */
    animateThinking() {
        if (!this.sprite) return;
        
        this.scene.tweens.add({
            targets: this.sprite,
            rotation: 0.1,
            duration: 1000,
            yoyo: true,
            repeat: -1,
            ease: 'Sine.easeInOut'
        });
        
        // 3秒后停止
        this.scene.time.delayedCall(3000, () => {
            this.scene.tweens.killTweensOf(this.sprite);
            this.sprite.setRotation(0);
        });
    }

    /**
     * 兴奋动画
     */
    animateExcited() {
        if (!this.sprite) return;
        
        this.scene.tweens.add({
            targets: this.sprite,
            y: this.position.y - 10,
            duration: 200,
            yoyo: true,
            repeat: 3,
            ease: 'Power2'
        });
    }

    /**
     * 更新可见性
     */
    updateVisibility() {
        const visible = this.isVisible;
        if (this.sprite) this.sprite.setVisible(visible);
        if (this.nameText) this.nameText.setVisible(visible);
        if (this.statusText) this.statusText.setVisible(visible);
    }

    /**
     * 设置可见性
     */
    setVisible(visible) {
        this.isVisible = visible;
        this.updateVisibility();
    }

    /**
     * 销毁智能体
     */
    destroy() {
        this.hideSpeechBubble();
        this.hideThoughtBubble();
        
        if (this.sprite) {
            this.sprite.destroy();
            this.sprite = null;
        }
        if (this.nameText) {
            this.nameText.destroy();
            this.nameText = null;
        }
        if (this.statusText) {
            this.statusText.destroy();
            this.statusText = null;
        }
    }
}

export default BaseAgent;
