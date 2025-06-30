import Phaser from 'phaser';
import MainScene from './scenes/MainScene.js';
import UIScene from './scenes/UIScene.js';
import GameCore from './core/GameCore.js';

/**
 * Agent Sandbox - 租房协商模拟前端
 * 基于Phaser 3构建的多智能体可视化系统
 */

// 游戏配置
const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    parent: 'game',
    pixelArt: false,
    antialias: true,
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { y: 0 },
            debug: false
        }
    },
    scene: [MainScene, UIScene],
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH
    }
};

// 全局变量
let phaserGame = null;
let gameCore = null;

/**
 * 应用初始化
 */
async function initializeApp() {
    console.log('[App] 应用初始化开始...');
    
    try {
        // 检查后端连接
        await checkBackendConnection();
        
        // 初始化Phaser游戏
        phaserGame = new Phaser.Game(config);
        
        // 设置全局引用
        window.phaserGame = phaserGame;
        
        // 更新状态
        updateStatus('应用已初始化', 'success');
        
        console.log('[App] 应用初始化完成');
        
    } catch (error) {
        console.error('[App] 应用初始化失败:', error);
        updateStatus('初始化失败: ' + error.message, 'error');
    }
}

/**
 * 检查后端连接
 */
async function checkBackendConnection() {
    const statusElement = document.getElementById('status');
    
    try {
        updateStatus('正在连接后端...', 'info');
        
        const response = await fetch('http://localhost:8000/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateStatus('后端连接成功', 'success');
            console.log('[App] 后端连接成功:', data);
            return true;
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
    } catch (error) {
        updateStatus('后端连接失败', 'error');
        console.error('[App] 后端连接失败:', error);
        throw error;
    }
}

/**
 * 更新状态显示
 */
function updateStatus(message, type = 'info') {
    const statusElement = document.getElementById('status');
    if (statusElement) {
        statusElement.textContent = `状态: ${message}`;
        
        // 设置颜色
        const colors = {
            success: '#27ae60',
            error: '#e74c3c',
            warning: '#f39c12',
            info: '#3498db'
        };
        
        statusElement.style.color = colors[type] || '#2c3e50';
    }
    
    console.log(`[App] 状态更新: ${message}`);
}

/**
 * 设置HTML控制按钮事件
 */
function setupHTMLControls() {
    // 初始化按钮
    const initBtn = document.getElementById('initialize-btn');
    if (initBtn) {
        initBtn.addEventListener('click', async () => {
            try {
                updateStatus('正在初始化系统...', 'info');
                
                const response = await fetch('http://localhost:8000/initialize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tenant_count: 3,
                        reset_data: false
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    updateStatus(`系统初始化成功: ${data.data.tenants_count}个租客, ${data.data.landlords_count}个房东`, 'success');
                    
                    // 通知游戏场景
                    if (phaserGame) {
                        const mainScene = phaserGame.scene.getScene('MainScene');
                        if (mainScene && mainScene.gameCore) {
                            mainScene.gameCore.emit('system:data_loaded', data.data);
                        }
                    }
                } else {
                    throw new Error(`初始化失败: ${response.statusText}`);
                }
                
            } catch (error) {
                updateStatus('初始化失败: ' + error.message, 'error');
                console.error('[App] 初始化失败:', error);
            }
        });
    }
    
    // 开始协商按钮
    const startBtn = document.getElementById('start-btn');
    if (startBtn) {
        startBtn.addEventListener('click', async () => {
            try {
                updateStatus('正在启动协商...', 'info');
                
                const response = await fetch('http://localhost:8000/start-negotiation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tenant_ids: []
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    updateStatus(`协商已启动: ${data.total_sessions}个会话`, 'success');
                    
                    // 通知游戏场景
                    if (phaserGame) {
                        const mainScene = phaserGame.scene.getScene('MainScene');
                        if (mainScene && mainScene.gameCore) {
                            mainScene.gameCore.emit('negotiation:started', data);
                        }
                    }
                } else {
                    throw new Error(`启动协商失败: ${response.statusText}`);
                }
                
            } catch (error) {
                updateStatus('启动协商失败: ' + error.message, 'error');
                console.error('[App] 启动协商失败:', error);
            }
        });
    }
    
    // 重置按钮
    const resetBtn = document.getElementById('reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', async () => {
            try {
                updateStatus('正在重置记忆...', 'info');
                
                const response = await fetch('http://localhost:8000/reset-memory', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    updateStatus('记忆已重置', 'success');
                    
                    // 通知游戏场景
                    if (phaserGame) {
                        const mainScene = phaserGame.scene.getScene('MainScene');
                        if (mainScene && mainScene.gameCore) {
                            mainScene.gameCore.emit('system:memory_reset');
                        }
                    }
                } else {
                    throw new Error(`重置失败: ${response.statusText}`);
                }
                
            } catch (error) {
                updateStatus('重置失败: ' + error.message, 'error');
                console.error('[App] 重置失败:', error);
            }
        });
    }
}

/**
 * 应用启动入口
 */
window.addEventListener('load', async () => {
    console.log('[App] 页面加载完成，开始初始化应用...');
    
    // 设置HTML控制按钮
    setupHTMLControls();
    
    // 初始化应用
    await initializeApp();
});

/**
 * 错误处理
 */
window.addEventListener('error', (event) => {
    console.error('[App] 全局错误:', event.error);
    updateStatus('应用错误: ' + event.error.message, 'error');
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('[App] 未处理的Promise拒绝:', event.reason);
    updateStatus('Promise错误: ' + event.reason, 'error');
});

// 导出全局函数供调试使用
window.app = {
    getPhaserGame: () => phaserGame,
    getGameCore: () => {
        if (phaserGame) {
            const mainScene = phaserGame.scene.getScene('MainScene');
            return mainScene?.gameCore;
        }
        return null;
    },
    updateStatus,
    checkBackendConnection
};
