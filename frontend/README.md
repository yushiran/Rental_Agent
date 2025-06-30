# Rental Agent Maps Frontend

基于 Google Maps 的多智能体租房协商可视化系统

## 🗺️ 功能特性

- **Google Maps 集成**: 使用真实地图展示智能体位置和房产信息
- **实时协商可视化**: 通过地图标记和对话气泡展示智能体对话过程  
- **多智能体支持**: 支持多个租客和房东智能体同时在地图上交互
- **WebSocket 通信**: 与后端实时同步协商状态和消息
- **响应式设计**: 适配桌面和移动设备

## 🏗️ 架构组件

### 地图模块 (`/src/maps/`)

- **MapManager**: Google Maps 核心管理器
- **GoogleMapsLoader**: 动态加载 Google Maps API  
- **AgentMapController**: 智能体地图控制器

### 网络模块 (`/src/network/`)

- **NetworkManager**: HTTP请求和WebSocket连接管理

### 主应用 (`/src/main.js`)

- **RentalAgentApp**: 应用主控制器，协调各模块工作

## 🚀 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置 Google Maps API (可选)

编辑 `src/main.js` 中的配置：

```javascript
const config = {
    apiKey: 'YOUR_GOOGLE_MAPS_API_KEY', // 可选，不填写将使用免费版本
    backendUrl: 'http://localhost:8000',
    mapContainer: 'map'
};
```

### 3. 启动开发服务器

```bash
npm run dev
```

### 4. 构建生产版本

```bash
npm run build
```

## 📡 与后端通信

### REST API 接口

- `POST /start-session`: 开始协商会话
- `POST /reset-memory`: 重置记忆状态

### WebSocket 事件

- `agent_started`: 智能体开始行动
- `message_sent`: 发送消息
- `agent_thought`: 智能体思考
- `negotiation_update`: 协商进度更新
- `agreement_reached`: 达成协议
- `dialogue_ended`: 对话结束

## 🎮 用户交互

### 主要功能

1. **开始协商**: 点击"开始协商"按钮启动新的协商会话
2. **重置会话**: 清除当前会话状态，重新开始
3. **查看日志**: 实时查看协商过程中的所有事件
4. **地图交互**: 点击地图上的智能体和房产标记查看详细信息

### 地图元素

- **蓝色标记**: 租客智能体
- **红色标记**: 房东智能体
- **房屋图标**: 可租房产
- **对话气泡**: 实时显示智能体对话内容

## 🔧 自定义配置

### 地图样式

在 `MapManager.js` 的 `getMapStyles()` 方法中自定义地图外观。

### 智能体位置

在 `AgentMapController.js` 中修改 `agentPositions` 和 `propertyPositions` 数组来调整默认位置。

### UI 主题

在 `index.html` 的 `<style>` 部分自定义颜色和布局。

## 📱 响应式支持

系统支持桌面和移动设备：

- 桌面：侧边栏 + 地图布局
- 移动：堆叠布局，控制面板在上方

## 🔒 安全考虑

- Google Maps API Key 应该设置域名限制
- 生产环境请配置 HTTPS
- WebSocket 连接支持自动重连机制

## 🔍 调试模式

打开浏览器开发者工具查看详细日志：

- `[RentalAgentApp]`: 应用主逻辑
- `[MapManager]`: 地图操作
- `[NetworkManager]`: 网络通信
- `[AgentMapController]`: 智能体控制

## 📈 性能优化

- 地图标记使用对象池管理
- WebSocket 连接带心跳检测
- 日志条数自动限制避免内存泄漏
- 响应式图片和矢量图标
