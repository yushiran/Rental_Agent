import BaseAgent from './BaseAgent.js';

/**
 * LandlordAgent - 房东智能体
 * 继承BaseAgent，添加房东特有的行为和视觉效果
 */
class LandlordAgent extends BaseAgent {
    constructor(id, data, scene) {
        super(id, 'landlord', data, scene);
        
        // 房东特有属性
        this.properties = data.properties || [];
        this.preferences = data.preferences || {};
        this.negotiationStyle = data.negotiation_style || 'moderate';
        this.status = 'available'; // available, busy, unavailable
        this.currentTenant = null;
        
        this.updateVisuals();
    }

    /**
     * 更新视觉效果
     */
    updateVisuals() {
        // 添加房东标识
        if (this.sprite) {
            this.landlordIcon = this.scene.add.text(
                this.position.x, 
                this.position.y, 
                '🏢',
                { fontSize: '16px' }
            ).setOrigin(0.5);
        }
        
        // 根据协商风格调整外观
        this.updateStyleVisuals();
    }

    /**
     * 根据协商风格更新视觉
     */
    updateStyleVisuals() {
        if (!this.sprite) return;
        
        let color = this.getAgentColor();
        switch (this.negotiationStyle) {
            case 'aggressive':
                color = 0xF44336; // 红色 - 强硬
                break;
            case 'flexible':
                color = 0x4CAF50; // 绿色 - 灵活
                break;
            case 'moderate':
                color = 0x2196F3; // 蓝色 - 温和
                break;
        }
        
        this.sprite.setFillStyle(color);
    }

    /**
     * 被租客联系
     */
    contactedByTenant(tenantId) {
        this.currentTenant = tenantId;
        this.status = 'busy';
        this.setStatus(`与 ${tenantId} 协商中`);
        this.setEmotion('serious');
        
        this.showSpeechBubble('有租客联系我了', 2000);
    }

    /**
     * 开始协商
     */
    startNegotiation() {
        this.status = 'busy';
        this.setStatus('协商中...');
        this.setEmotion('neutral');
    }

    /**
     * 考虑报价
     */
    considerOffer(offer) {
        this.setStatus('考虑中...');
        this.playAnimation('thinking', 'confused');
        this.showThoughtBubble('让我想想...', 2000);
        
        // 根据协商风格显示不同的思考时间
        const thinkingTime = this.getThinkingTime();
        return new Promise(resolve => {
            this.scene.time.delayedCall(thinkingTime, () => {
                resolve(this.evaluateOffer(offer));
            });
        });
    }

    /**
     * 获取思考时间
     */
    getThinkingTime() {
        switch (this.negotiationStyle) {
            case 'aggressive': return 1000; // 快速决定
            case 'flexible': return 1500;   // 中等速度
            case 'moderate': return 2000;   // 深思熟虑
            default: return 1500;
        }
    }

    /**
     * 评估报价
     */
    evaluateOffer(offer) {
        // 这里可以添加更复杂的评估逻辑
        const acceptance = Math.random() > 0.5; // 简单的随机决定
        
        if (acceptance) {
            this.setEmotion('pleased');
            this.showSpeechBubble('这个价格可以接受', 2000);
        } else {
            this.setEmotion('frustrated');
            this.showSpeechBubble('这个价格太低了', 2000);
        }
        
        return acceptance;
    }

    /**
     * 发出反报价
     */
    makeCounterOffer(originalOffer) {
        this.setStatus('发出反报价');
        this.playAnimation('talking', 'serious');
        
        // 根据协商风格调整反报价策略
        let adjustment = 0.1; // 默认调整10%
        switch (this.negotiationStyle) {
            case 'aggressive': adjustment = 0.2; break;  // 强硬，调整20%
            case 'flexible': adjustment = 0.05; break;   // 灵活，调整5%
            case 'moderate': adjustment = 0.1; break;    // 温和，调整10%
        }
        
        const counterOffer = originalOffer * (1 + adjustment);
        this.showSpeechBubble(`我的价格是 ¥${Math.round(counterOffer)}`, 3000);
        
        return counterOffer;
    }

    /**
     * 协商成功
     */
    negotiationSuccess(details) {
        this.status = 'unavailable';
        this.setStatus('已租出');
        this.playAnimation('excited', 'happy');
        this.showSpeechBubble('成交！很高兴合作', 3000);
        
        // 显示成功特效
        this.showSuccessEffect();
        
        // 标记为不可用
        this.markAsUnavailable();
    }

    /**
     * 协商失败
     */
    negotiationFailed(reason) {
        this.status = 'available';
        this.currentTenant = null;
        this.setStatus('重新可用');
        this.setEmotion('disappointed');
        this.showSpeechBubble(`协商失败：${reason}`, 3000);
        
        // 恢复可用状态
        this.scene.time.delayedCall(3000, () => {
            this.setStatus('等待租客');
            this.setEmotion('neutral');
        });
    }

    /**
     * 显示成功特效
     */
    showSuccessEffect() {
        if (!this.sprite) return;
        
        // 创建成功特效 - 金色光环
        const successRing = this.scene.add.circle(
            this.position.x, 
            this.position.y, 
            30, 
            0xFFD700, 
            0
        );
        successRing.setStrokeStyle(3, 0xFFD700, 0.8);
        
        this.scene.tweens.add({
            targets: successRing,
            radius: 60,
            alpha: 0,
            duration: 2000,
            ease: 'Power2',
            onComplete: () => successRing.destroy()
        });
    }

    /**
     * 标记为不可用
     */
    markAsUnavailable() {
        if (this.sprite) {
            // 添加"已租出"标记
            this.rentedLabel = this.scene.add.text(
                this.position.x, 
                this.position.y + 60, 
                '已租出',
                {
                    fontSize: '10px',
                    fill: '#FF5722',
                    backgroundColor: '#ffffff',
                    padding: { x: 4, y: 2 }
                }
            ).setOrigin(0.5);
            
            // 降低透明度
            this.sprite.setAlpha(0.6);
        }
    }

    /**
     * 显示房产信息
     */
    showPropertyInfo() {
        if (this.properties.length > 0) {
            const property = this.properties[0]; // 显示第一个房产
            const info = `房产: ${property.bedrooms || 1}室 ¥${property.price || 2000}/月`;
            this.showSpeechBubble(info, 3000);
        }
    }

    /**
     * 获取协商风格描述
     */
    getStyleDescription() {
        const styles = {
            'aggressive': '强硬型',
            'flexible': '灵活型',
            'moderate': '温和型'
        };
        return styles[this.negotiationStyle] || '未知';
    }

    /**
     * 更新位置时也要更新图标和标签
     */
    setPosition(x, y) {
        super.setPosition(x, y);
        if (this.landlordIcon) {
            this.landlordIcon.setPosition(x, y);
        }
        if (this.rentedLabel) {
            this.rentedLabel.setPosition(x, y + 60);
        }
    }

    /**
     * 移动时也要移动图标和标签
     */
    moveTo(targetX, targetY, duration = 1000) {
        super.moveTo(targetX, targetY, duration);
        
        if (this.landlordIcon) {
            this.scene.tweens.add({
                targets: this.landlordIcon,
                x: targetX,
                y: targetY,
                duration: duration,
                ease: 'Power2'
            });
        }
        
        if (this.rentedLabel) {
            this.scene.tweens.add({
                targets: this.rentedLabel,
                x: targetX,
                y: targetY + 60,
                duration: duration,
                ease: 'Power2'
            });
        }
    }

    /**
     * 销毁时也要销毁图标和标签
     */
    destroy() {
        if (this.landlordIcon) {
            this.landlordIcon.destroy();
            this.landlordIcon = null;
        }
        if (this.rentedLabel) {
            this.rentedLabel.destroy();
            this.rentedLabel = null;
        }
        super.destroy();
    }
}

export default LandlordAgent;
