# Agent Sandbox - 租房协商模拟前端

基于 **Agent Sandbox Dialogue World** 概念设计的高效、模块化、可复用的多智能体租房协商可视化系统。

## 🎯 设计特点

### 核心架构
- **GameCore**: 游戏核心管理器，协调所有系统组件
- **StateManager**: 统一的状态管理，响应式状态更新
- **AgentManager**: 智能体行为和视觉效果管理
- **NetworkManager**: 网络通信和WebSocket管理
- **Agent Objects**: 面向对象的智能体实现

### 代码特色
- ✅ **高度模块化**: 每个组件职责清晰，可独立测试和复用
- ✅ **事件驱动**: 基于事件系统的组件间通信
- ✅ **类型安全**: 清晰的接口定义和错误处理
- ✅ **响应式**: 实时状态更新和视觉反馈
- ✅ **可扩展**: 易于添加新的智能体类型和行为

## 🚀 快速开始

### 环境要求
- Node.js >= 16.0.0
- 后端服务运行在 `http://localhost:8000`

### 安装和运行
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

### 构建生产版本
```bash
# 构建
npm run build

# 预览构建结果
npm run preview
```

## 📁 项目结构

```
frontend/
├── src/
│   ├── core/                    # 核心系统
│   │   ├── GameCore.js         # 游戏核心管理器
│   │   ├── StateManager.js     # 状态管理器
│   │   └── AgentManager.js     # 智能体管理器
│   ├── network/                # 网络通信
│   │   └── NetworkManager.js   # 网络管理器
│   ├── objects/                # 游戏对象
│   │   ├── BaseAgent.js        # 基础智能体类
│   │   ├── TenantAgent.js      # 租客智能体
│   │   └── LandlordAgent.js    # 房东智能体
│   ├── scenes/                 # Phaser场景
│   │   ├── MainScene.js        # 主场景
│   │   └── UIScene.js          # UI场景
│   └── main.js                 # 应用入口
├── public/
│   └── favicon.svg             # 网站图标
├── index.html                  # HTML模板
├── package.json               # 项目配置
└── vite.config.js             # Vite配置
```

## 🎮 系统功能

### 核心功能
1. **系统初始化**: 生成租客、房东和房产数据
2. **智能体可视化**: 租客和房东的实时可视化展示
3. **协商模拟**: 多智能体间的动态协商过程
4. **实时通信**: WebSocket实时消息传输
5. **状态管理**: 统一的应用状态管理

### 交互功能
- 🖱️ **点击交互**: 点击智能体查看详细信息
- 💬 **对话气泡**: 实时显示智能体对话内容
- 💭 **思考气泡**: 显示智能体内部思考过程
- 📊 **状态面板**: 实时显示系统状态和统计信息
- 🎛️ **控制面板**: 系统控制和参数调整

## 🔧 技术栈

### 前端技术
- **Phaser 3**: 游戏引擎和可视化
- **Vite**: 构建工具和开发服务器
- **ES6 Modules**: 模块化架构
- **WebSocket**: 实时通信
- **CSS3**: 现代样式和动画

### 后端集成
- **LangGraph**: 多智能体协商引擎
- **FastAPI**: 后端API服务
- **MongoDB**: 状态持久化
- **WebSocket**: 实时事件流

## 📡 API集成

### HTTP接口
- `POST /initialize`: 初始化系统数据
- `POST /start-negotiation`: 启动协商流程
- `POST /reset-memory`: 重置系统记忆

### WebSocket事件
- `agent_started`: 智能体开始行动
- `message_sent`: 智能体发送消息
- `agent_thought`: 智能体思考
- `negotiation_completed`: 协商完成

## 🎨 可视化特性

### 智能体表现
- **租客** (🟢): 主动搜索和协商
- **房东** (🔵): 响应式协商参与
- **动画效果**: 说话、思考、移动、情绪变化
- **状态指示**: 实时状态文本显示

### 场景元素
- **城市背景**: 简约的像素风城市天际线
- **连接线**: 协商中的智能体连接可视化
- **特效系统**: 成功/失败动画效果

## 🔄 状态管理

### 状态层次
```javascript
state: {
    system: {           // 系统状态
        initialized: boolean,
        loading: boolean,
        networkStatus: string
    },
    agents: Map,        // 智能体状态
    negotiations: Map,  // 协商状态
    animations: Map,    // 动画状态
    ui: {              // UI状态
        activePanel: string,
        notifications: Array
    }
}
```

### 事件流
1. **用户操作** → UI事件
2. **UI事件** → GameCore处理
3. **网络请求** → 后端API
4. **WebSocket消息** → 状态更新
5. **状态变更** → 视觉更新

## 🔧 开发指南

### 添加新的智能体类型
1. 继承 `BaseAgent` 类
2. 实现特定的视觉和行为逻辑
3. 在 `AgentManager` 中注册处理器
4. 更新状态管理逻辑

### 扩展网络事件
1. 在 `NetworkManager` 中添加事件处理
2. 在 `AgentManager` 中实现视觉响应
3. 更新状态管理器的监听器

### 自定义UI组件
1. 在 `UIScene` 中添加UI元素
2. 实现事件处理逻辑
3. 连接到状态管理系统

## 🐛 调试工具

### 浏览器控制台
```javascript
// 获取游戏实例
window.app.getPhaserGame()

// 获取游戏核心
window.app.getGameCore()

// 更新状态显示
window.app.updateStatus('自定义状态', 'info')

// 检查后端连接
window.app.checkBackendConnection()
```

### 开发模式
- Vite热重载
- Source Maps支持
- 详细的控制台日志
- 错误边界处理

## 🚀 性能优化

### 前端优化
- 代码分割 (Phaser单独打包)
- 资源懒加载
- 状态更新防抖
- 动画性能优化

### 网络优化
- WebSocket连接池
- 心跳机制
- 自动重连
- 消息队列

## 📈 未来扩展

### 计划功能
- 🎵 音效系统
- 🎮 键盘快捷键
- 📱 移动端适配
- 🌍 多语言支持
- 📊 数据可视化图表

### 架构扩展
- 插件系统
- 主题系统
- 配置热重载
- 性能监控

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 保持代码风格一致
4. 添加适当的注释和文档
5. 测试新功能
6. 提交Pull Request

## 📄 许可证

MIT License - 详见 LICENSE 文件
