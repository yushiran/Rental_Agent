# 🏠 Rental Agent: 多智能体租房协商系统

[🇺🇸 English](../../README.md) | 🇨🇳 中文版本

基于 LangGraph 的智能租房协商系统，实现租客与房东之间的自动化对话协商，并通过实时地图可视化展示协商过程。

## 🎯 项目概述

这是一个**多智能体对话系统**，使用 [LangGraph](https://github.com/langchain-ai/langgraph) 构建，专注于**模块化设计**、**代码清晰度**和**可重用性**。

### ✨ 核心特性

- 🤖 **智能协商**: 租客智能体自动寻找合适房东并进行价格协商
- 🗺️ **实时可视化**: 基于Google Maps的实时协商过程展示
- 💾 **状态管理**: MongoDB持久化存储对话状态和长期记忆
- 🔄 **流式处理**: 实时流式输出协商过程和中间状态
- 🎭 **角色扮演**: 不同性格的智能体角色，如理性型、情感型等
- 📊 **市场分析**: 集成英国租房市场数据分析功能

### 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │    Database     │
│   (Vue.js)      │◄──►│   (FastAPI)     │◄──►│   (MongoDB)     │
│  - 地图可视化    │    │  - LangGraph    │    │  - 对话状态     │
│  - 实时更新      │    │  - 智能体协调    │    │  - 长期记忆     │
│  - WebSocket    │    │  - API 服务     │    │  - 检查点管理   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 快速开始

### 前置要求

- Docker & Docker Compose
- 4GB+ 可用内存
- Google Maps API Key (可选，用于地图功能)

### 🔧 环境配置

1. **克隆项目**

```bash
git clone <repository-url>
cd Rental_Agent
```

2. **配置环境变量**

```bash
# 复制配置文件
cp backend/config/config.example.toml backend/config/config.toml

# 编辑配置文件，填入你的API密钥
vim backend/config/config.toml
```

3. **启动服务**

```bash
# 构建并启动所有服务
docker-compose up --build

# 后台运行
docker-compose up -d --build
```

### 📱 访问应用

服务启动后，你可以访问：

- **🎨 前端界面**: <http://localhost:3000>
  - 实时协商可视化
  - 智能体角色展示
  - 协商过程追踪

- **📚 API 文档**: <http://localhost:8000/docs>
  - FastAPI 自动生成的交互式文档
  - WebSocket 接口说明
  - 测试接口功能

- **🗄️ MongoDB**: localhost:27017
  - 数据库直接连接
  - 可使用 MongoDB Compass 等工具

## 💡 使用方法

### 1. 启动协商会话

**方法一：通过前端界面**

1. 打开 <http://localhost:3000>
2. 点击"开始协商"按钮
3. 观察地图上的智能体互动

**方法二：通过API**

```bash
# 初始化智能体数据
curl -X POST "http://localhost:8000/initialize" \
  -H "Content-Type: application/json" \
  -d '{
    "num_tenants": 3,
    "num_landlords": 5,
    "area": "London"
  }'

# 开始协商
curl -X POST "http://localhost:8000/start-negotiation" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_session_001"
  }'
```

### 2. 实时监控

**WebSocket 连接:**

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/demo_session_001');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('协商更新:', data);
};
```

**事件类型:**

- `agent_started`: 智能体开始响应
- `message_sent`: 发送对话消息
- `agent_thought`: 智能体内部思考
- `agreement_reached`: 达成协议
- `dialogue_ended`: 对话结束

### 3. 重置会话

```bash
# 清除所有对话记忆
curl -X POST "http://localhost:8000/reset-memory"
```

## 📁 项目结构

```
Rental_Agent/
├── 🐳 docker-compose.yml          # Docker 服务编排
├── 📚 README.md                   # 项目说明文档
├── backend/                       # 后端服务
│   ├── 🐳 Dockerfile             # 后端容器配置
│   ├── 📦 pyproject.toml         # Python 依赖管理
│   ├── app/                      # 应用核心代码
│   │   ├── 🤖 agents/            # 智能体定义
│   │   ├── 🌐 api_service/       # API 服务层
│   │   ├── 💬 conversation_service/ # 对话控制器
│   │   ├── 📊 data_analysis/     # 市场数据分析
│   │   ├── 💾 mongo/             # 数据库操作
│   │   └── 🛠️ utils/             # 工具函数
│   ├── config/                   # 配置文件
│   └── dataset/                  # 英国租房数据集
├── frontend/                     # 前端应用
│   ├── 🐳 Dockerfile            # 前端容器配置
│   ├── 📦 package.json          # Node.js 依赖
│   └── src/                     # 源代码
│       ├── 🗺️ maps/             # 地图相关组件
│       ├── 🌐 network/          # 网络通信
│       └── 🎨 components/       # UI 组件
└── docs/                        # 详细技术文档
    ├── 📋 markdown/             # 项目文档
    └── 📖 reference/            # 参考资料
```

## 🔧 开发指南

### 修改代码

```bash
# 开发模式启动（支持热重载）
docker-compose up

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 数据库管理

```bash
# 进入 MongoDB 容器
docker exec -it rental_mongodb mongosh

# 查看数据库
show dbs
use rental_agent_db
show collections
```

### 清理环境

```bash
# 停止所有服务
docker-compose down

# 清理数据卷（⚠️ 会删除所有数据）
docker-compose down --volumes

# 清理镜像
docker-compose down --rmi all
```

## 📊 技术栈

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 🧠 AI 框架 | LangGraph, LangChain | 0.4+ | 智能体编排与对话管理 |
| 🌐 后端 | FastAPI, Python | 3.13+ | REST API & WebSocket |
| 🎨 前端 | Vite, JavaScript | ES6+ | 实时可视化界面 |
| 💾 数据库 | MongoDB | 7.0 | 状态持久化存储 |
| 🗺️ 地图 | Google Maps API | - | 地理位置可视化 |
| 🐳 部署 | Docker, Docker Compose | - | 容器化部署 |

## 📖 详细文档

- **[📋 项目架构](../markdown/PROJECT_OVERVIEW.md)** - 深入了解系统设计
- **[📊 数据集说明](../markdown/DATASET_README.md)** - 英国租房数据详情
- **[🔌 API 文档](../markdown/API_Service_Technical_Documentation_Updated.md)** - 接口使用说明
- **[🤖 智能体设计](../markdown/agent_controller_design.md)** - Agent 架构解析
- **[🔧 LangGraph 集成](../markdown/LANGGRAPH_INTEGRATION.md)** - 工作流引擎说明

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](../../LICENSE) 文件了解详情。

## 🆘 常见问题

### Q: 容器启动失败？

A: 检查端口占用，确保 3000、8000、27017 端口未被占用。

### Q: 协商没有响应？

A: 检查 API 密钥配置，确保 OpenAI 或其他 LLM 服务可用。

### Q: 地图无法加载？

A: 确保 Google Maps API Key 已正确配置。

### Q: 数据丢失？

A: 检查 MongoDB 数据卷是否正确挂载。

---

**🎉 现在开始探索智能租房协商的世界吧！**
