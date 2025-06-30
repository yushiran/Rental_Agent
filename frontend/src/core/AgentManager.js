/**
 * AgentManager - 智能体管理器
 * 负责管理租客和房东智能体的状态、行为和交互
 */
class AgentManager {
    constructor(gameCore) {
        this.gameCore = gameCore;
        this.stateManager = gameCore.stateManager;
        
        // Agent配置
        this.agentConfig = {
            tenant: {
                color: 0x4CAF50,
                animations: ['idle', 'walking', 'talking', 'thinking'],
                emotions: ['neutral', 'happy', 'confused', 'excited', 'disappointed']
            },
            landlord: {
                color: 0x2196F3,
                animations: ['idle', 'walking', 'talking', 'thinking'],
                emotions: ['neutral', 'happy', 'serious', 'pleased', 'frustrated']
            }
        };
        
        // 动画队列
        this.animationQueues = new Map();
        
        // 对话气泡
        this.speechBubbles = new Map();
    }

    /**
     * 处理Agent开始事件
     */
    handleAgentStarted(data) {
        const { agent_id, agent_type, session_id } = data;
        
        console.log(`[AgentManager] Agent ${agent_id} (${agent_type}) 开始行动`);
        
        // 更新Agent状态
        this.stateManager.updateAgentState(agent_id, {
            status: 'active',
            currentSession: session_id,
            lastAction: 'started',
            emotion: 'neutral'
        });
        
        // 触发动画
        this.queueAnimation(agent_id, {
            type: 'status_change',
            animation: 'thinking',
            emotion: 'neutral',
            duration: 1000
        });
        
        // 显示状态指示器
        this.showStatusIndicator(agent_id, '开始思考...', 2000);
    }

    /**
     * 处理Agent消息事件
     */
    handleMessageSent(data) {
        const { agent_id, content, session_id, message_type } = data;
        
        console.log(`[AgentManager] Agent ${agent_id} 发送消息:`, content);
        
        // 更新Agent状态
        this.stateManager.updateAgentState(agent_id, {
            status: 'talking',
            lastMessage: content,
            messageType: message_type,
            lastAction: 'message'
        });
        
        // 显示对话气泡
        this.showSpeechBubble(agent_id, content, {
            type: message_type || 'normal',
            duration: Math.min(content.length * 100, 5000) // 根据内容长度调整显示时间
        });
        
        // 触发说话动画
        this.queueAnimation(agent_id, {
            type: 'talking',
            animation: 'talking',
            emotion: this.getEmotionFromMessage(content, message_type),
            duration: 2000
        });
    }

    /**
     * 处理Agent思考事件
     */
    handleAgentThought(data) {
        const { agent_id, content, thought_type } = data;
        
        console.log(`[AgentManager] Agent ${agent_id} 思考:`, content);
        
        // 更新Agent状态
        this.stateManager.updateAgentState(agent_id, {
            status: 'thinking',
            lastThought: content,
            thoughtType: thought_type,
            lastAction: 'thought'
        });
        
        // 显示思考气泡
        this.showThoughtBubble(agent_id, content, {
            type: thought_type || 'normal',
            duration: 3000
        });
        
        // 触发思考动画
        this.queueAnimation(agent_id, {
            type: 'thinking',
            animation: 'thinking',
            emotion: 'confused',
            duration: 2000
        });
    }

    /**
     * 显示对话气泡
     */
    showSpeechBubble(agentId, content, options = {}) {
        const bubble = {
            id: `speech_${agentId}_${Date.now()}`,
            agentId,
            content,
            type: 'speech',
            style: options.type || 'normal',
            duration: options.duration || 3000,
            timestamp: Date.now()
        };
        
        this.speechBubbles.set(bubble.id, bubble);
        
        // 发送到UI系统显示
        this.gameCore.emit('ui:speech_bubble', bubble);
        
        // 自动移除
        setTimeout(() => {
            this.removeSpeechBubble(bubble.id);
        }, bubble.duration);
        
        return bubble.id;
    }

    /**
     * 显示思考气泡
     */
    showThoughtBubble(agentId, content, options = {}) {
        const bubble = {
            id: `thought_${agentId}_${Date.now()}`,
            agentId,
            content,
            type: 'thought',
            style: options.type || 'normal',
            duration: options.duration || 3000,
            timestamp: Date.now()
        };
        
        this.speechBubbles.set(bubble.id, bubble);
        
        // 发送到UI系统显示
        this.gameCore.emit('ui:thought_bubble', bubble);
        
        // 自动移除
        setTimeout(() => {
            this.removeSpeechBubble(bubble.id);
        }, bubble.duration);
        
        return bubble.id;
    }

    /**
     * 显示状态指示器
     */
    showStatusIndicator(agentId, message, duration = 2000) {
        const indicator = {
            id: `status_${agentId}_${Date.now()}`,
            agentId,
            message,
            duration,
            timestamp: Date.now()
        };
        
        // 发送到UI系统显示
        this.gameCore.emit('ui:status_indicator', indicator);
        
        return indicator.id;
    }

    /**
     * 移除对话气泡
     */
    removeSpeechBubble(bubbleId) {
        if (this.speechBubbles.has(bubbleId)) {
            this.speechBubbles.delete(bubbleId);
            this.gameCore.emit('ui:remove_bubble', { bubbleId });
        }
    }

    /**
     * 队列动画
     */
    queueAnimation(agentId, animation) {
        if (!this.animationQueues.has(agentId)) {
            this.animationQueues.set(agentId, []);
        }
        
        this.animationQueues.get(agentId).push({
            ...animation,
            id: `anim_${agentId}_${Date.now()}`,
            timestamp: Date.now()
        });
        
        // 处理动画队列
        this.processAnimationQueue(agentId);
    }

    /**
     * 处理动画队列
     */
    async processAnimationQueue(agentId) {
        const queue = this.animationQueues.get(agentId);
        if (!queue || queue.length === 0) return;
        
        const animation = queue.shift();
        
        // 更新动画状态
        this.stateManager.updateAnimationState(agentId, animation.type, {
            active: true,
            animation: animation.animation,
            emotion: animation.emotion,
            startTime: Date.now()
        });
        
        // 发送动画事件
        this.gameCore.emit('agent:animation', {
            agentId,
            ...animation
        });
        
        // 等待动画完成
        setTimeout(() => {
            this.stateManager.updateAnimationState(agentId, animation.type, {
                active: false,
                endTime: Date.now()
            });
            
            // 处理下一个动画
            if (queue.length > 0) {
                this.processAnimationQueue(agentId);
            }
        }, animation.duration);
    }

    /**
     * 根据消息内容推断情绪
     */
    getEmotionFromMessage(content, messageType) {
        const lowerContent = content.toLowerCase();
        
        // 根据消息类型和内容推断情绪
        if (messageType === 'agreement') {
            return 'happy';
        } else if (messageType === 'rejection') {
            return 'disappointed';
        } else if (lowerContent.includes('谢谢') || lowerContent.includes('好的')) {
            return 'pleased';
        } else if (lowerContent.includes('？') || lowerContent.includes('?')) {
            return 'confused';
        } else if (lowerContent.includes('不') || lowerContent.includes('拒绝')) {
            return 'frustrated';
        } else {
            return 'neutral';
        }
    }

    /**
     * 获取Agent的可视化配置
     */
    getAgentVisualConfig(agentId) {
        const agentData = this.gameCore.getAgent(agentId);
        if (!agentData) return null;
        
        const config = this.agentConfig[agentData.type];
        const state = this.stateManager.getAgentState(agentId);
        
        return {
            ...config,
            currentAnimation: state?.status || 'idle',
            currentEmotion: state?.emotion || 'neutral',
            position: agentData.data.location || { x: 0, y: 0 },
            name: agentData.data.name || agentId
        };
    }

    /**
     * 设置Agent位置
     */
    setAgentPosition(agentId, position) {
        this.stateManager.updateAgentState(agentId, {
            position: { ...position, lastUpdate: Date.now() }
        });
        
        this.gameCore.emit('agent:position_update', {
            agentId,
            position
        });
    }

    /**
     * 移动Agent到指定位置
     */
    moveAgentTo(agentId, targetPosition, duration = 2000) {
        const currentState = this.stateManager.getAgentState(agentId);
        const startPosition = currentState?.position || { x: 0, y: 0 };
        
        // 更新状态为移动中
        this.stateManager.updateAgentState(agentId, {
            status: 'moving',
            targetPosition,
            lastAction: 'move'
        });
        
        // 触发移动动画
        this.queueAnimation(agentId, {
            type: 'movement',
            animation: 'walking',
            startPosition,
            targetPosition,
            duration
        });
        
        // 在移动完成后更新位置
        setTimeout(() => {
            this.setAgentPosition(agentId, targetPosition);
            this.stateManager.updateAgentState(agentId, {
                status: 'idle'
            });
        }, duration);
    }

    /**
     * 获取所有活跃的对话气泡
     */
    getActiveSpeechBubbles() {
        return Array.from(this.speechBubbles.values());
    }

    /**
     * 清理Agent数据
     */
    clearAgent(agentId) {
        // 清理动画队列
        this.animationQueues.delete(agentId);
        
        // 清理对话气泡
        for (const [bubbleId, bubble] of this.speechBubbles) {
            if (bubble.agentId === agentId) {
                this.removeSpeechBubble(bubbleId);
            }
        }
        
        // 清理状态
        this.stateManager.updateAgentState(agentId, {
            status: 'idle',
            lastAction: 'cleared'
        });
    }

    /**
     * 重置所有Agent
     */
    resetAllAgents() {
        for (const agentId of this.gameCore.gameState.agents.keys()) {
            this.clearAgent(agentId);
        }
        
        console.log('[AgentManager] 所有Agent已重置');
    }

    /**
     * 销毁管理器
     */
    destroy() {
        this.animationQueues.clear();
        this.speechBubbles.clear();
        console.log('[AgentManager] 已销毁');
    }
}

export default AgentManager;
