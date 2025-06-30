/**
 * StateManager - 状态管理器
 * 负责管理整个应用的状态，包括Agent状态、UI状态、动画状态等
 */
class StateManager {
    constructor(gameCore) {
        this.gameCore = gameCore;
        
        // 状态存储
        this.state = {
            // 系统状态
            system: {
                initialized: false,
                loading: false,
                error: null,
                networkStatus: 'disconnected'
            },
            
            // UI状态
            ui: {
                activePanel: 'control',
                notifications: [],
                modalOpen: false
            },
            
            // Agent状态
            agents: new Map(),
            
            // 协商状态
            negotiations: new Map(),
            
            // 动画状态
            animations: new Map()
        };
        
        // 状态变更监听器
        this.stateListeners = new Map();
        
        this.setupStateListeners();
    }

    /**
     * 设置状态监听器
     */
    setupStateListeners() {
        // 监听GameCore事件并更新状态
        this.gameCore.on('core:initialized', () => {
            this.setState('system.initialized', true);
        });

        this.gameCore.on('system:status', (data) => {
            if (data.type === 'network') {
                this.setState('system.networkStatus', data.status);
            }
        });

        this.gameCore.on('system:error', (data) => {
            this.setState('system.error', data.error);
            this.addNotification('error', data.error);
        });

        this.gameCore.on('agent:started', (data) => {
            this.updateAgentState(data.agent_id, { status: 'active', lastAction: 'started' });
        });

        this.gameCore.on('agent:message', (data) => {
            this.updateAgentState(data.agent_id, { 
                status: 'talking', 
                lastMessage: data.content,
                lastAction: 'message'
            });
        });

        this.gameCore.on('agent:thought', (data) => {
            this.updateAgentState(data.agent_id, { 
                status: 'thinking', 
                lastThought: data.content,
                lastAction: 'thought'
            });
        });

        this.gameCore.on('negotiation:started', (data) => {
            data.sessions.forEach(session => {
                this.updateNegotiationState(session.session_id, {
                    status: 'active',
                    participants: [session.tenant_id, session.landlord_id],
                    startTime: Date.now()
                });
            });
        });

        this.gameCore.on('negotiation:completed', (data) => {
            this.updateNegotiationState(data.session_id, {
                status: 'completed',
                result: data.result,
                endTime: Date.now()
            });
        });
    }

    /**
     * 设置状态值
     */
    setState(path, value) {
        const pathArray = path.split('.');
        let current = this.state;
        
        // 导航到目标对象
        for (let i = 0; i < pathArray.length - 1; i++) {
            if (!(pathArray[i] in current)) {
                current[pathArray[i]] = {};
            }
            current = current[pathArray[i]];
        }
        
        const lastKey = pathArray[pathArray.length - 1];
        const oldValue = current[lastKey];
        current[lastKey] = value;
        
        // 触发状态变更事件
        this.emitStateChange(path, value, oldValue);
    }

    /**
     * 获取状态值
     */
    getState(path) {
        if (!path) return { ...this.state };
        
        const pathArray = path.split('.');
        let current = this.state;
        
        for (const key of pathArray) {
            if (current === null || current === undefined || !(key in current)) {
                return undefined;
            }
            current = current[key];
        }
        
        return current;
    }

    /**
     * 更新Agent状态
     */
    updateAgentState(agentId, updates) {
        const currentState = this.state.agents.get(agentId) || {};
        const newState = { ...currentState, ...updates, lastUpdate: Date.now() };
        
        this.state.agents.set(agentId, newState);
        this.emitStateChange(`agents.${agentId}`, newState, currentState);
    }

    /**
     * 获取Agent状态
     */
    getAgentState(agentId) {
        return this.state.agents.get(agentId);
    }

    /**
     * 更新协商状态
     */
    updateNegotiationState(sessionId, updates) {
        const currentState = this.state.negotiations.get(sessionId) || {};
        const newState = { ...currentState, ...updates, lastUpdate: Date.now() };
        
        this.state.negotiations.set(sessionId, newState);
        this.emitStateChange(`negotiations.${sessionId}`, newState, currentState);
    }

    /**
     * 获取协商状态
     */
    getNegotiationState(sessionId) {
        return this.state.negotiations.get(sessionId);
    }

    /**
     * 更新动画状态
     */
    updateAnimationState(targetId, animationType, state) {
        const key = `${targetId}_${animationType}`;
        const currentState = this.state.animations.get(key) || {};
        const newState = { ...currentState, ...state, lastUpdate: Date.now() };
        
        this.state.animations.set(key, newState);
        this.emitStateChange(`animations.${key}`, newState, currentState);
    }

    /**
     * 获取动画状态
     */
    getAnimationState(targetId, animationType) {
        const key = `${targetId}_${animationType}`;
        return this.state.animations.get(key);
    }

    /**
     * 添加通知
     */
    addNotification(type, message, duration = 5000) {
        const notification = {
            id: Date.now(),
            type,
            message,
            timestamp: Date.now(),
            duration
        };
        
        this.state.ui.notifications.push(notification);
        this.emitStateChange('ui.notifications', this.state.ui.notifications);
        
        // 自动移除通知
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(notification.id);
            }, duration);
        }
        
        return notification.id;
    }

    /**
     * 移除通知
     */
    removeNotification(notificationId) {
        const index = this.state.ui.notifications.findIndex(n => n.id === notificationId);
        if (index > -1) {
            this.state.ui.notifications.splice(index, 1);
            this.emitStateChange('ui.notifications', this.state.ui.notifications);
        }
    }

    /**
     * 设置加载状态
     */
    setLoading(loading, message = '') {
        this.setState('system.loading', loading);
        if (loading && message) {
            this.addNotification('info', message, 0);
        }
    }

    /**
     * 设置UI面板
     */
    setActivePanel(panelName) {
        this.setState('ui.activePanel', panelName);
    }

    /**
     * 设置模态框状态
     */
    setModalOpen(open) {
        this.setState('ui.modalOpen', open);
    }

    /**
     * 监听状态变更
     */
    onStateChange(path, callback) {
        if (!this.stateListeners.has(path)) {
            this.stateListeners.set(path, []);
        }
        this.stateListeners.get(path).push(callback);
        
        // 返回取消监听函数
        return () => {
            const listeners = this.stateListeners.get(path);
            if (listeners) {
                const index = listeners.indexOf(callback);
                if (index > -1) {
                    listeners.splice(index, 1);
                }
            }
        };
    }

    /**
     * 触发状态变更事件
     */
    emitStateChange(path, newValue, oldValue) {
        // 触发精确路径监听器
        if (this.stateListeners.has(path)) {
            this.stateListeners.get(path).forEach(callback => {
                try {
                    callback(newValue, oldValue, path);
                } catch (error) {
                    console.error(`[StateManager] 状态监听器错误 (${path}):`, error);
                }
            });
        }
        
        // 触发通配符监听器 (例如 agents.* 监听所有Agent状态变更)
        const pathParts = path.split('.');
        for (let i = 1; i <= pathParts.length; i++) {
            const wildcardPath = pathParts.slice(0, i).join('.') + '.*';
            if (this.stateListeners.has(wildcardPath)) {
                this.stateListeners.get(wildcardPath).forEach(callback => {
                    try {
                        callback(newValue, oldValue, path);
                    } catch (error) {
                        console.error(`[StateManager] 通配符监听器错误 (${wildcardPath}):`, error);
                    }
                });
            }
        }
    }

    /**
     * 获取所有活跃的Agent
     */
    getActiveAgents() {
        const activeAgents = [];
        for (const [agentId, state] of this.state.agents) {
            if (state.status !== 'idle') {
                activeAgents.push({ id: agentId, ...state });
            }
        }
        return activeAgents;
    }

    /**
     * 获取所有活跃的协商
     */
    getActiveNegotiations() {
        const activeNegotiations = [];
        for (const [sessionId, state] of this.state.negotiations) {
            if (state.status === 'active') {
                activeNegotiations.push({ id: sessionId, ...state });
            }
        }
        return activeNegotiations;
    }

    /**
     * 重置状态
     */
    reset() {
        this.state.agents.clear();
        this.state.negotiations.clear();
        this.state.animations.clear();
        this.state.ui.notifications = [];
        this.setState('system.error', null);
        this.setState('system.loading', false);
        
        console.log('[StateManager] 状态已重置');
    }

    /**
     * 销毁状态管理器
     */
    destroy() {
        this.stateListeners.clear();
        this.reset();
        console.log('[StateManager] 已销毁');
    }
}

export default StateManager;
