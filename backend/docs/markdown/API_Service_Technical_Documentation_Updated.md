# API Service 技术文档 (无分析师版本)

## 概述

API Service 是租赁协商系统的核心服务层，提供多方租赁协商的 RESTful API 和 WebSocket 实时通信功能。该服务支持房东和租客之间的多方协商，并提供完整的会话管理和消息路由功能。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    API Service Layer                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    main.py  │  │   admin.py  │  │   message_router.py │  │
│  │  (FastAPI)  │  │   (Admin)   │  │   (Message Routing) │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐  ┌─────────────────────┐   │
│  │    negotiation_service.py   │  │      models.py      │   │
│  │    (Core Business Logic)    │  │   (Data Models)     │   │
│  └─────────────────────────────┘  └─────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                utils.py (Utilities)                     │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 核心功能

- **多方协商管理**: 支持房东和多个租客之间的协商
- **实时通信**: 基于 WebSocket 的实时消息交换
- **会话管理**: 完整的协商会话生命周期管理
- **RESTful API**: 标准的 REST 接口设计
- **数据持久化**: MongoDB 数据存储
- **错误处理**: 完善的异常处理机制

## 核心组件

### 1. main.py - 主要 API 应用

**职责**: FastAPI 应用的主入口，定义所有 HTTP 和 WebSocket 端点

**主要功能**:
- 创建协商会话
- 管理参与者加入
- WebSocket 实时通信
- 会话信息查询

**关键端点**:

#### REST API 端点
- `POST /negotiation/create` - 创建新的协商会话
- `POST /negotiation/{session_id}/join` - 加入现有协商会话
- `GET /negotiation/{session_id}` - 获取协商会话详情
- `GET /participant/{participant_id}/negotiations` - 获取参与者的活跃协商
- `POST /reset-memory` - 重置对话记忆

#### WebSocket 端点
- `WS /ws/negotiation/{session_id}` - 主要协商 WebSocket 连接
- `WS /ws/chat` - 传统聊天 WebSocket 连接（向后兼容）

### 2. models.py - 数据模型定义

**核心数据模型**:

```python
# 参与者角色
class ParticipantRole(str, Enum):
    TENANT = "tenant"
    LANDLORD = "landlord"

# 协商状态
class NegotiationStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# 协商会话
class NegotiationSession(BaseModel):
    session_id: str
    property_id: str
    participants: List[ParticipantInfo]
    status: NegotiationStatus
    created_at: str
    updated_at: str
    context: Dict[str, Any]
```

### 3. negotiation_service.py - 核心业务逻辑

**职责**: 管理协商会话的完整生命周期

**主要方法**:

#### `create_negotiation_session()`
- 验证参与者存在性
- 创建参与者列表（房东、租客）
- 生成唯一会话 ID
- 保存到数据库

#### `get_session()`
- 根据会话 ID 获取会话信息
- 返回完整的会话状态

#### `add_participant()`
- 向现有会话添加新参与者
- 验证参与者身份
- 更新会话状态

#### `get_active_sessions_for_participant()`
- 获取参与者的所有活跃会话
- 支持多会话并发

### 4. message_router.py - 消息路由服务

**职责**: 根据参与者角色路由消息到相应的对话服务

**路由逻辑**:
- **租客消息**: 路由到 `get_tenant_streaming_response()`
- **房东消息**: 路由到 `get_landlord_streaming_response()`

**上下文构建**:
- 会话信息
- 房产详情
- 参与者信息
- 协商历史

### 5. admin.py - 管理端点

**职责**: 提供系统管理和分析功能

**功能**:
- 获取示例参与者数据
- 创建演示协商会话
- 会话分析统计
- 热门房产统计
- 系统健康检查

### 6. utils.py - 工具函数

**主要工具类**:

#### `ParticipantUtils`
- 查找合适的租客
- 获取示例参与者
- 创建演示数据

#### `NegotiationAnalytics`
- 会话统计分析
- 热门房产分析
- 参与者活跃度分析

## 数据流

### 1. 协商会话创建流程

```
[客户端] --POST--> [main.py] --验证--> [negotiation_service.py]
    │                               │
    └── 创建会话请求                   └── 验证参与者 & 房产
                                      │
                                      └── 保存到 MongoDB
                                      │
                                      └── 返回会话信息
```

### 2. WebSocket 实时通信流程

```
[客户端] --WebSocket--> [main.py] --消息--> [message_router.py]
    │                              │
    └── 发送消息                     └── 根据角色路由
                                    │
                                    ├── 租客: tenant_streaming_response
                                    └── 房东: landlord_streaming_response
                                    │
                                    └── 流式返回响应
```

## 数据库设计

### MongoDB 集合

1. **negotiation_sessions**
   - 存储协商会话信息
   - 索引: session_id, participants.participant_id

2. **landlords**
   - 房东信息
   - 索引: landlord_id

3. **tenants**
   - 租客信息
   - 索引: tenant_id

4. **properties**
   - 房产信息
   - 索引: property_id

## API 规范

### 创建协商会话

```http
POST /negotiation/create
Content-Type: application/json

{
  "property_id": "prop_123",
  "tenant_ids": ["tenant_1", "tenant_2"],
  "landlord_id": "landlord_1"
}
```

**响应**:
```json
{
  "session_id": "uuid-generated",
  "status": "active",
  "message": "Negotiation session created successfully",
  "participants": [
    {
      "participant_id": "landlord_1",
      "role": "landlord",
      "name": "John Smith",
      "is_active": true
    },
    {
      "participant_id": "tenant_1",
      "role": "tenant",
      "name": "Alice Johnson",
      "is_active": true
    }
  ]
}
```

### WebSocket 通信

**连接**: `ws://localhost:8000/ws/negotiation/{session_id}`

**消息格式**:
```json
{
  "message": "I'm interested in this property",
  "participant_id": "tenant_1"
}
```

**响应流式格式**:
```json
{"type": "response_start", "streaming": true}
{"type": "response_chunk", "chunk": "Hello"}
{"type": "response_chunk", "chunk": ", I understand"}
{"type": "response_complete", "response": "Hello, I understand your interest.", "streaming": false}
```

## 错误处理

### HTTP 错误码
- `400`: 请求参数错误
- `404`: 资源未找到（会话、参与者、房产）
- `500`: 服务器内部错误

### WebSocket 错误
```json
{
  "type": "error",
  "error": "Session not found"
}
```

## 性能特性

### 1. 异步处理
- 所有数据库操作使用 `async/await`
- WebSocket 支持并发连接
- 流式响应减少延迟

### 2. 可扩展性
- 无状态设计
- 数据库连接池
- 支持水平扩展

### 3. 监控和日志
- Loguru 结构化日志
- Opik 追踪集成
- 错误监控和报告

## 安全特性

### 1. 输入验证
- Pydantic 模型验证
- 参数类型检查
- SQL 注入防护

### 2. 会话管理
- UUID 会话 ID
- 参与者身份验证
- 会话状态控制

## 部署配置

### 环境变量
```env
MONGODB_URL=mongodb://localhost:27017
OPIK_API_KEY=your_opik_key
LOG_LEVEL=INFO
```

### Docker 部署
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "app.api_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 测试策略

### 1. 单元测试
- 模型验证测试
- 业务逻辑测试
- 工具函数测试

### 2. 集成测试
- API 端点测试
- WebSocket 连接测试
- 数据库交互测试

### 3. 性能测试
- 并发用户测试
- 响应时间测试
- 内存使用测试

## 故障排除

### 常见问题

1. **WebSocket 连接失败**
   - 检查会话 ID 有效性
   - 验证网络连接
   - 查看服务器日志

2. **协商创建失败**
   - 验证参与者存在
   - 检查房产信息
   - 确认数据库连接

3. **消息路由错误**
   - 检查参与者角色
   - 验证会话状态
   - 查看错误日志

### 日志分析
```bash
# 查看协商创建日志
grep "Created negotiation session" logs/app.log

# 查看 WebSocket 连接日志
grep "WebSocket connected" logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log
```

## 版本历史

- **v2.0.0**: 多方协商支持（房东和租客），WebSocket 实时通信
- **v1.0.0**: 基础 REST API，单方协商

---

*本文档最后更新：2025年6月6日*
