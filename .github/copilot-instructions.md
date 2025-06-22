# 本项目后端部分使用python进行编写，前端部分基于Godot框架，如果我在对话中出现认知错误或者任何想法错误请狠狠批评我
永远保证代码的清晰性、可读性和可复用性，以及高效性。

## 📌 项目概览

本项目实现了一个基于 [LangGraph](https://github.com/langchain-ai/langgraph) 的**多智能体对话系统**，强调**模块化设计**、**代码清晰性**与**可复用性**。

每个智能体（如 TenantAgent、LandlordAgent）都被实现为一个独立的 LangGraph。一个控制器图（Controller Graph）协调它们之间的轮流对话，用于房屋租赁协商。

所有对话会话均由**租客端主动发起**，先通过**匹配节点**筛选合适的房东后再开始对话。

## 🎯 设计亮点

- **租客主动发起协商**
  - 每个会话从 TenantAgent 触发的 matching 节点开始。
  - 该节点会根据内部配置或检索机制选择一个 LandlordAgent。
  - 然后正式进入租客与房东之间的动态对话循环。

- **Agent 即图的架构**
  - TenantAgent 和 LandlordAgent 都是完整的 LangGraph，拥有自己的节点集合（如 summarize、retrieve、reason、reflect）。
  - 每个图都可以独立复用与测试。

- **控制器图**
  - 独立的调度 LangGraph 负责轮流控制、智能体切换、结束条件判断等逻辑。
  - 包含如达成一致或一方拒绝继续对话等终止条件。

## 💾 基于 MongoDB 的记忆与状态管理

### 短期记忆
- **检查点**（MONGO_STATE_CHECKPOINT_COLLECTION）：对当前对话状态的完整快照，用于容错与恢复。
- **增量写入**（MONGO_STATE_WRITES_COLLECTION）：每个节点执行后记录的状态变更，提高性能。

### 长期记忆
- 各智能体特定的长期知识保存在 MONGO_LONG_TERM_MEMORY_COLLECTION 中。

### 状态管理
由 AsyncMongoDBSaver 实现，功能包括：
- 初始检查点创建
- 每轮对话后的增量写入
- 基于最新有效检查点 + 写入记录恢复状态
- 支持通过 /reset-memory 接口进行无状态重置

## 🔁 流式支持

控制器图提供 astream_events() 接口，可用于将中间事件（如消息、状态转移）流式传输至前端或日志系统。

这使得多智能体之间的对话过程可在实时中进行观测与反馈。

## 🧱 技术栈

- [LangGraph](https://github.com/langchain-ai/langgraph) — 用于建模智能体与流程
- LangChain — 用于记忆管理、工具调度与 LLM 接入
- MongoDB — 管理短期和长期记忆的持久化
- FastAPI — 提供会话启动、流式传输和记忆重置等 API
- Docker — 项目容器化部署
- 可选支持：WebSocket / SSE — 用于前端的实时数据流传输

---
## 🎮 前端沙盒交互（Godot 实现）

本项目的前端采用 [Godot Engine](https://godotengine.org/) 实现，构建了一个像素风格的沙盒世界，用于可视化多智能体租房对话的全过程。

### 👥 核心交互逻辑（非玩家控制）

- 用户点击按钮启动一轮模拟，系统从租客智能体（TenantAgent）发起协商流程
- 多位房东智能体（LandlordAgent）作为静态角色分布在地图中，系统根据匹配逻辑自动选择对象并发起对话
- 对话过程以 **浮动气泡 + 表情图标** 的方式实时展示，体现角色状态与情绪（如满意 😊、困惑 🤔、拒绝 😠）
- 整个协商流程由 LangGraph 控制器驱动，用户可以全程旁观系统自主协商的全过程
- 若成功达成协议，双方将自动移动到“签约区”并触发签约动画；否则显示谈判失败的反馈动画

### 🔌 通信机制

Godot 通过 HTTP 和 WebSocket 与后端 `LangGraph Controller` 进行实时通信：

- 使用 REST API 触发初始匹配、状态重置等控制指令
- 使用 WebSocket 接收后端流式事件：  
  `agent_started`、`message_sent`、`agent_thought`、`agreement_reached` 等

### 🧩 项目结构建议

```bash
frontend/
├── scenes/
│   ├── Main.tscn              # 主场景（包含地图、角色、UI）
│   ├── Character.tscn         # 租客角色（可移动）
│   └── Landlord.tscn          # 房东角色（交互对象）
├── scripts/
│   ├── Main.gd                # 全局控制逻辑
│   ├── Character.gd           # 玩家控制脚本
│   └── WebSocketClient.gd     # 后端通信模块
├── assets/
│   ├── tilesets/              # 像素地图素材
│   ├── characters/            # 角色动画帧
│   └── ui/                    # 表情贴图、气泡框等
└── project.godot              # Godot 配置文件
