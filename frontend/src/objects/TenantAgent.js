import BaseAgent from './BaseAgent.js';

/**
 * TenantAgent - 租客智能体
 * 继承BaseAgent，添加租客特有的行为和视觉效果
 */
class TenantAgent extends BaseAgent {
    constructor(id, data, scene) {
        super(id, 'tenant', data, scene);
        
        // 租客特有属性
        this.budget = data.budget || { min: 1000, max: 3000 };
        this.preferences = data.preferences || {};
        this.searchStatus = 'searching'; // searching, negotiating, completed
        this.currentTarget = null;
        
        this.updateVisuals();
    }

    /**
     * 更新视觉效果
     */
    updateVisuals() {
        // 添加租客标识
        if (this.sprite) {
            // 添加一个小图标表示这是租客
            this.tenantIcon = this.scene.add.text(
                this.position.x, 
                this.position.y, 
                '🏠',
                { fontSize: '16px' }
            ).setOrigin(0.5);
        }
    }

    /**
     * 开始寻找房东
     */
    startSearching() {
        this.searchStatus = 'searching';
        this.setStatus('寻找房东...');
        this.playAnimation('thinking', 'confused');
        
        // 显示搜索动画
        this.showSearchAnimation();
    }

    /**
     * 显示搜索动画
     */
    showSearchAnimation() {
        if (!this.sprite) return;
        
        // 创建搜索范围圆圈
        this.searchCircle = this.scene.add.circle(
            this.position.x, 
            this.position.y, 
            0, 
            0x4CAF50, 
            0.2
        );
        
        // 扩展动画
        this.scene.tweens.add({
            targets: this.searchCircle,
            radius: 100,
            duration: 2000,
            ease: 'Power2',
            onComplete: () => {
                this.searchCircle.destroy();
            }
        });
    }

    /**
     * 找到房东
     */
    foundLandlord(landlordId) {
        this.currentTarget = landlordId;
        this.searchStatus = 'negotiating';
        this.setStatus(`与 ${landlordId} 协商中`);
        this.playAnimation('excited', 'happy');
        
        this.showSpeechBubble('找到了！开始协商吧', 2000);
    }

    /**
     * 开始协商
     */
    startNegotiation() {
        this.searchStatus = 'negotiating';
        this.setStatus('协商中...');
        this.setEmotion('neutral');
    }

    /**
     * 协商成功
     */
    negotiationSuccess(details) {
        this.searchStatus = 'completed';
        this.setStatus('协商成功！');
        this.playAnimation('excited', 'happy');
        this.showSpeechBubble('太好了！成交了！', 3000);
        
        // 显示成功特效
        this.showSuccessEffect();
    }

    /**
     * 协商失败
     */
    negotiationFailed(reason) {
        this.searchStatus = 'searching';
        this.setStatus('协商失败，继续寻找');
        this.setEmotion('disappointed');
        this.showSpeechBubble(`协商失败：${reason}`, 3000);
        
        // 重新开始搜索
        this.scene.time.delayedCall(2000, () => {
            this.startSearching();
        });
    }

    /**
     * 显示成功特效
     */
    showSuccessEffect() {
        if (!this.sprite) return;
        
        // 创建庆祝特效
        for (let i = 0; i < 8; i++) {
            const particle = this.scene.add.circle(
                this.position.x, 
                this.position.y, 
                3, 
                0xFFD700
            );
            
            const angle = (i / 8) * Math.PI * 2;
            const distance = 50;
            
            this.scene.tweens.add({
                targets: particle,
                x: this.position.x + Math.cos(angle) * distance,
                y: this.position.y + Math.sin(angle) * distance,
                alpha: 0,
                duration: 1000,
                ease: 'Power2',
                onComplete: () => particle.destroy()
            });
        }
    }

    /**
     * 显示预算信息
     */
    showBudgetInfo() {
        const budgetText = `预算: ¥${this.budget.min} - ¥${this.budget.max}`;
        this.showSpeechBubble(budgetText, 3000);
    }

    /**
     * 更新位置时也要更新图标
     */
    setPosition(x, y) {
        super.setPosition(x, y);
        if (this.tenantIcon) {
            this.tenantIcon.setPosition(x, y);
        }
    }

    /**
     * 移动时也要移动图标
     */
    moveTo(targetX, targetY, duration = 1000) {
        super.moveTo(targetX, targetY, duration);
        
        if (this.tenantIcon) {
            this.scene.tweens.add({
                targets: this.tenantIcon,
                x: targetX,
                y: targetY,
                duration: duration,
                ease: 'Power2'
            });
        }
    }

    /**
     * 销毁时也要销毁图标
     */
    destroy() {
        if (this.tenantIcon) {
            this.tenantIcon.destroy();
            this.tenantIcon = null;
        }
        if (this.searchCircle) {
            this.searchCircle.destroy();
            this.searchCircle = null;
        }
        super.destroy();
    }
}

export default TenantAgent;
