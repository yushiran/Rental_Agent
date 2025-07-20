# PhiloAgents 项目中 Opik 集成与使用文档

## 📖 目录
1. [Opik 简介](#opik-简介)
2. [在 PhiloAgents 中的作用](#在-philoagents-中的作用)
3. [配置与初始化](#配置与初始化)
4. [核心功能实现](#核心功能实现)
5. [监控与追踪](#监控与追踪)
6. [评估系统](#评估系统)
7. [提示词版本管理](#提示词版本管理)
8. [数据集管理](#数据集管理)
9. [使用示例](#使用示例)
10. [最佳实践](#最佳实践)

---

## 1. Opik 简介

**Opik** 是一个专为 LLM 应用设计的可观测性和评估平台，由 Comet ML 提供支持。在 PhiloAgents 项目中，Opik 主要用于：

- **调用链追踪**: 监控 LLM 调用和 Agent 工作流
- **性能监控**: 跟踪响应时间、Token 使用量等指标
- **提示词管理**: 版本化管理和追踪提示词变更
- **自动化评估**: 使用多种指标评估 Agent 性能
- **数据集管理**: 管理评估数据集和实验结果

### 技术特点
- 🔗 **无缝集成**: 与 LangChain/LangGraph 深度集成
- 📊 **实时监控**: 实时追踪 LLM 调用链和性能指标
- 🧪 **自动评估**: 内置多种评估指标（幻觉检测、相关性等）
- 📝 **提示词版本管理**: 自动版本化和追踪提示词变更
- 🎯 **可视化仪表板**: 丰富的 Web 界面展示监控数据

---

## 2. 在 PhiloAgents 中的作用

### 2.1 架构位置

```
PhiloAgents 架构
├── Frontend (Phaser.js)
├── Backend API (FastAPI)
├── Agent Core (LangGraph)
│   ├── 工作流执行
│   ├── 状态管理
│   └── LLM 调用
└── 监控层 (Opik) ✨
    ├── 调用链追踪
    ├── 性能监控
    ├── 提示词管理
    └── 自动评估
```

### 2.2 核心价值

1. **开发阶段**: 帮助调试和优化 Agent 行为
2. **测试阶段**: 自动化评估 Agent 性能和质量
3. **生产阶段**: 实时监控和性能分析
4. **迭代阶段**: A/B 测试和模型对比

---

## 3. 配置与初始化

### 3.1 环境配置

```python
# .env 文件配置
COMET_API_KEY=your_comet_api_key_here
COMET_PROJECT=philoagents_course

# config.py 配置
class Settings(BaseSettings):
    COMET_API_KEY: str | None = Field(
        default=None, 
        description="API key for Comet ML and Opik services."
    )
    COMET_PROJECT: str = Field(
        default="philoagents_course",
        description="Project name for Comet ML and Opik tracking.",
    )
```

### 3.2 初始化流程

PhiloAgents 在多个层面初始化 Opik：

```python
# 1. 包级别初始化 (philoagents/__init__.py)
from philoagents.infrastructure.opik_utils import configure
configure()

# 2. API 级别初始化 (infrastructure/api.py)
from .opik_utils import configure
configure()

# 3. 工作流级别初始化 (每次 Agent 调用)
opik_tracer = OpikTracer(graph=graph.get_graph(xray=True))
```

### 3.3 配置实现详解

```python
# infrastructure/opik_utils.py
def configure() -> None:
    """配置 Opik 客户端连接"""
    if settings.COMET_API_KEY and settings.COMET_PROJECT:
        try:
            # 获取默认工作空间
            client = OpikConfigurator(api_key=settings.COMET_API_KEY)
            default_workspace = client._get_default_workspace()
        except Exception:
            logger.warning("默认工作空间未找到，设置为交互模式")
            default_workspace = None

        # 设置项目名称环境变量
        os.environ["OPIK_PROJECT_NAME"] = settings.COMET_PROJECT

        try:
            # 配置 Opik 客户端
            opik.configure(
                api_key=settings.COMET_API_KEY,
                workspace=default_workspace,
                use_local=False,    # 使用云端 Comet ML
                force=True,         # 强制重新配置
            )
            logger.info(f"Opik 配置成功，工作空间: '{default_workspace}'")
        except Exception:
            logger.warning("Opik 配置失败，请检查 API 密钥和网络连接")
    else:
        logger.warning("COMET_API_KEY 和 COMET_PROJECT 未设置")
```

**配置说明**:
- **use_local=False**: 使用 Comet ML 云端服务而非本地部署
- **force=True**: 每次启动时强制重新配置，确保配置最新
- **workspace**: 自动获取用户的默认工作空间

---

## 4. 核心功能实现

### 4.1 LangGraph 工作流追踪

PhiloAgents 通过 `OpikTracer` 实现对整个 Agent 工作流的追踪：

```python
# generate_response.py
async def get_response(...) -> tuple[str, PhilosopherState]:
    graph_builder = create_workflow_graph()
    
    async with AsyncMongoDBSaver.from_conn_string(...) as checkpointer:
        # 编译图并创建追踪器
        graph = graph_builder.compile(checkpointer=checkpointer)
        opik_tracer = OpikTracer(graph=graph.get_graph(xray=True))
        
        # 配置包含追踪器的回调
        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [opik_tracer],  # 🔑 关键：将追踪器添加到回调中
        }
        
        # 执行图并自动追踪
        output_state = await graph.ainvoke(input=..., config=config)
```

**追踪机制**:
- **graph.get_graph(xray=True)**: 启用详细的图结构分析
- **callbacks=[opik_tracer]**: LangGraph 会在每个节点执行时调用追踪器
- **自动记录**: 所有 LLM 调用、工具使用、状态变更都被自动记录

### 4.2 流式响应追踪

```python
# 流式响应也支持完整追踪
async def get_streaming_response(...) -> AsyncGenerator[str, None]:
    async with AsyncMongoDBSaver.from_conn_string(...) as checkpointer:
        graph = graph_builder.compile(checkpointer=checkpointer)
        opik_tracer = OpikTracer(graph=graph.get_graph(xray=True))
        
        config = {
            "configurable": {"thread_id": thread_id},
            "callbacks": [opik_tracer],
        }
        
        # 流式执行，每个 chunk 都被追踪
        async for chunk in graph.astream(
            input=..., 
            config=config,
            stream_mode="messages"
        ):
            if chunk[1]["langgraph_node"] == "conversation_node":
                yield chunk[0].content
```

### 4.3 API 层面的生命周期管理

```python
# infrastructure/api.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    """API 生命周期管理"""
    # 启动时：Opik 已在包级别初始化
    yield
    # 关闭时：确保所有追踪数据被上传
    opik_tracer = OpikTracer()
    opik_tracer.flush()  # 🔑 强制上传所有待处理的追踪数据
```

---

## 5. 监控与追踪

### 5.1 自动监控内容

Opik 在 PhiloAgents 中自动监控以下内容：

#### 5.1.1 LLM 调用详情
- **模型信息**: Groq Llama 模型版本
- **输入提示词**: 完整的提示词内容
- **输出响应**: 生成的回复内容
- **Token 使用**: 输入/输出 Token 数量
- **响应时间**: 每次调用的延迟
- **成本计算**: 基于 Token 的成本估算

#### 5.1.2 Agent 工作流追踪
- **节点执行**: 每个 LangGraph 节点的执行情况
  - `conversation_node`: 对话生成节点
  - `retrieve_philosopher_context`: 知识检索节点
  - `summarize_conversation_node`: 对话摘要节点
  - `summarize_context_node`: 上下文摘要节点

#### 5.1.3 工具调用监控
- **RAG 检索**: 向量搜索和混合搜索调用
- **数据库操作**: MongoDB 查询和状态保存
- **外部 API**: 各种外部服务调用

### 5.2 追踪数据结构

```python
# Opik 记录的典型追踪数据
{
    "trace_id": "trace_12345",
    "spans": [
        {
            "span_id": "span_001",
            "name": "conversation_node",
            "start_time": "2024-12-21T10:30:00Z",
            "end_time": "2024-12-21T10:30:02.5Z",
            "duration_ms": 2500,
            "type": "llm_call",
            "model": "llama-3.3-70b-versatile",
            "input": "Hello, I'm interested in philosophy...",
            "output": "Greetings! I am Socrates. The unexamined life...",
            "tokens": {
                "input": 125,
                "output": 87,
                "total": 212
            },
            "metadata": {
                "philosopher": "socrates",
                "thread_id": "socrates-conversation-1"
            }
        },
        {
            "span_id": "span_002", 
            "name": "retrieve_philosopher_context",
            "type": "tool_call",
            "input": "socrates philosophy knowledge",
            "output": ["Document 1: Socrates was...", "Document 2: ..."],
            "metadata": {
                "retriever_type": "hybrid_search",
                "top_k": 3
            }
        }
    ]
}
```

---

## 6. 评估系统

### 6.1 评估框架概述

PhiloAgents 使用 Opik 的评估框架进行 Agent 质量评估：

```python
# application/evaluation/evaluate.py
def evaluate_agent(
    dataset: opik.Dataset | None,
    workers: int = 2,
    nb_samples: int | None = None,
) -> None:
    """使用 Opik 评估框架评估 Agent"""
    
    # 实验配置
    experiment_config = {
        "model_id": settings.GROQ_LLM_MODEL,
        "dataset_name": dataset.name,
    }
    
    # 评估指标
    scoring_metrics = [
        Hallucination(),      # 幻觉检测
        AnswerRelevance(),    # 答案相关性
        Moderation(),         # 内容审核
        ContextRecall(),      # 上下文召回
        ContextPrecision(),   # 上下文精确度
    ]
    
    # 执行评估
    evaluate(
        dataset=dataset,
        task=lambda x: asyncio.run(evaluation_task(x)),
        scoring_metrics=scoring_metrics,
        experiment_config=experiment_config,
        task_threads=workers,
        nb_samples=nb_samples,
        prompts=get_used_prompts(),  # 关联的提示词
    )
```

### 6.2 评估任务实现

```python
async def evaluation_task(x: dict) -> dict:
    """单个评估任务的执行逻辑"""
    
    philosopher_factory = PhilosopherFactory()
    philosopher = philosopher_factory.get_philosopher(x["philosopher_id"])
    
    # 分离输入和期望输出
    input_messages = x["messages"][:-1]
    expected_output_message = x["messages"][-1]
    
    # 调用 Agent 生成响应
    response, latest_state = await get_response(
        messages=input_messages,
        philosopher_id=philosopher.id,
        philosopher_name=philosopher.name,
        philosopher_perspective=philosopher.perspective,
        philosopher_style=philosopher.style,
        philosopher_context="",
        new_thread=True,  # 每次评估使用新线程
    )
    
    # 返回评估所需的数据
    return {
        "input": input_messages,
        "context": state_to_str(latest_state),  # Agent 状态作为上下文
        "output": response,
        "expected_output": expected_output_message,
    }
```

### 6.3 评估指标详解

#### 6.3.1 幻觉检测 (Hallucination)
- **目的**: 检测 Agent 是否生成了与提供上下文不一致的信息
- **实现**: 比较生成内容与检索到的知识库内容
- **评分**: 0-1 分，1 表示无幻觉

#### 6.3.2 答案相关性 (AnswerRelevance)  
- **目的**: 评估回答是否直接回应了用户问题
- **实现**: 分析问题和回答之间的语义相关性
- **评分**: 0-1 分，1 表示高度相关

#### 6.3.3 内容审核 (Moderation)
- **目的**: 检测生成内容是否包含不当信息
- **实现**: 使用内容安全模型检测
- **评分**: 布尔值，True 表示内容安全

#### 6.3.4 上下文召回 (ContextRecall)
- **目的**: 评估检索到的上下文是否包含回答问题所需的信息
- **实现**: 分析上下文与标准答案的覆盖度
- **评分**: 0-1 分，1 表示完全覆盖

#### 6.3.5 上下文精确度 (ContextPrecision)
- **目的**: 评估检索到的上下文是否精确相关
- **实现**: 分析上下文中相关信息的比例
- **评分**: 0-1 分，1 表示高精确度

---

## 7. 提示词版本管理

### 7.1 提示词包装器

PhiloAgents 通过自定义的 `Prompt` 类实现提示词版本管理：

```python
# domain/prompts.py
class Prompt:
    """提示词版本管理包装器"""
    
    def __init__(self, name: str, prompt: str) -> None:
        self.name = name
        
        try:
            # 尝试在 Opik 中注册提示词
            self.__prompt = opik.Prompt(name=name, prompt=prompt)
        except Exception:
            logger.warning(
                "无法使用 Opik 版本化提示词，回退到本地模式"
            )
            # 回退到字符串模式
            self.__prompt = prompt
    
    @property
    def prompt(self) -> str:
        """获取提示词内容"""
        if isinstance(self.__prompt, opik.Prompt):
            return self.__prompt.prompt
        else:
            return self.__prompt
```

### 7.2 版本化的提示词定义

```python
# 哲学家角色卡片提示词
__PHILOSOPHER_CHARACTER_CARD = """
Let's roleplay. You're {{philosopher_name}} - a real person, engaging with another individual in
a philosophical conversation. Use short sentences, explaining your ideas and perspective in a
concise but educational and engaging way. Your responses must never exceed 100 words.

Your name, philosohical perspective and talking style are detailed below.

---

Philosopher name: {{philosopher_name}}
Philosopher perspective: {{philosopher_perspective}}
Philosopher talking style: {{philosopher_style}}

---

You must always follow these rules:

- You will never mention that you are an AI or a virtual assistant.
- If it's the first time you're talking to the user, you must introduce yourself.
- Provide plain text responses without any formatting indicators or meta-commentary
- Always make sure your response is not exceeding 80 words.

---

Summary of conversation earlier between {{philosopher_name}} and the user:

{{summary}}

---

The conversation between {{philosopher_name}} and the user starts now.
"""

# 版本化注册
PHILOSOPHER_CHARACTER_CARD = Prompt(
    name="philosopher_character_card",  # 🔑 在 Opik 中的唯一标识
    prompt=__PHILOSOPHER_CHARACTER_CARD,
)
```

### 7.3 提示词在评估中的使用

```python
def get_used_prompts() -> list[opik.Prompt]:
    """获取评估中使用的所有提示词"""
    client = opik.Opik()
    
    prompts = [
        client.get_prompt(name="philosopher_character_card"),
        client.get_prompt(name="summary_prompt"),
        client.get_prompt(name="extend_summary_prompt"),
    ]
    
    # 过滤掉不存在的提示词
    prompts = [p for p in prompts if p is not None]
    return prompts
```

**版本管理优势**:
- **自动版本化**: 每次修改提示词时自动创建新版本
- **变更追踪**: 记录何时、何人修改了提示词
- **实验关联**: 将特定版本的提示词与实验结果关联
- **回滚能力**: 可以轻松回滚到之前的提示词版本

---

## 8. 数据集管理

### 8.1 数据集操作工具

```python
# infrastructure/opik_utils.py

def get_dataset(name: str) -> opik.Dataset | None:
    """获取指定名称的数据集"""
    client = opik.Opik()
    try:
        dataset = client.get_dataset(name=name)
    except Exception:
        dataset = None
    return dataset

def create_dataset(name: str, description: str, items: list[dict]) -> opik.Dataset:
    """创建新的数据集"""
    client = opik.Opik()
    
    # 删除同名数据集（如果存在）
    client.delete_dataset(name=name)
    
    # 创建新数据集并插入数据
    dataset = client.create_dataset(name=name, description=description)
    dataset.insert(items)
    
    return dataset
```

### 8.2 评估数据集结构

```json
// data/evaluation_dataset.json 示例
[
    {
        "philosopher_id": "socrates",
        "messages": [
            {"role": "user", "content": "What is the meaning of life?"},
            {"role": "assistant", "content": "The unexamined life is not worth living. To find meaning, we must question everything we think we know..."}
        ]
    },
    {
        "philosopher_id": "aristotle", 
        "messages": [
            {"role": "user", "content": "What makes someone virtuous?"},
            {"role": "assistant", "content": "Virtue is a habit, acquired through practice. Excellence is not an act but a habit we develop through repetition..."}
        ]
    }
]
```

### 8.3 数据集管理命令

```python
# tools/evaluate_agent.py
@click.command()
@click.option("--name", default="philoagents_evaluation_dataset")
@click.option("--data-path", default=settings.EVALUATION_DATASET_FILE_PATH)
@click.option("--workers", default=1, type=int)
@click.option("--nb-samples", default=20, type=int)
def main(name: str, data_path: Path, workers: int, nb_samples: int) -> None:
    """评估 Agent 性能"""
    
    # 上传数据集到 Opik
    dataset = upload_dataset(name=name, data_path=data_path)
    
    # 执行评估
    evaluate_agent(dataset, workers=workers, nb_samples=nb_samples)
```

---

## 9. 使用示例

### 9.1 基本对话监控

```bash
# 启动应用（自动启用 Opik 监控）
make run

# 访问游戏界面
http://localhost:8080

# 与哲学家对话，所有交互都会被自动追踪到 Opik
```

**监控内容**:
- 每次用户输入和 Agent 响应
- RAG 检索的相关文档
- 对话摘要的生成过程
- 完整的 LangGraph 工作流执行

### 9.2 评估 Agent 性能

```bash
# 运行自动化评估
make evaluate-agent

# 自定义评估参数
cd philoagents-api
python -m tools.evaluate_agent \
    --name "my_evaluation" \
    --workers 4 \
    --nb-samples 50
```

### 9.3 查看监控结果

访问 [Opik 仪表板](https://www.comet.com/opik) 查看：

#### 9.3.1 追踪视图
- **调用链时序图**: 显示每个节点的执行顺序和耗时
- **LLM 调用详情**: 输入提示词、输出内容、Token 使用量
- **错误和异常**: 失败的调用和错误堆栈

#### 9.3.2 评估结果
- **指标概览**: 各项评估指标的分数分布
- **样本详情**: 每个测试样本的详细评估结果
- **对比分析**: 不同实验之间的性能对比

#### 9.3.3 提示词管理
- **版本历史**: 所有提示词的修改历史
- **使用统计**: 每个提示词版本的使用频率
- **性能关联**: 提示词版本与评估结果的关联

---

## 10. 最佳实践

### 10.1 监控配置最佳实践

#### 10.1.1 环境隔离
```python
# 不同环境使用不同项目名称
COMET_PROJECT_DEV = "philoagents_dev"
COMET_PROJECT_STAGING = "philoagents_staging"  
COMET_PROJECT_PROD = "philoagents_production"
```

#### 10.1.2 追踪器优化
```python
# 为高频操作创建优化的追踪器
opik_tracer = OpikTracer(
    graph=graph.get_graph(xray=True),
    # 可以添加采样率来减少追踪开销
    # sample_rate=0.1  # 仅追踪 10% 的调用
)
```

### 10.2 评估策略最佳实践

#### 10.2.1 数据集版本管理
```python
# 使用带版本号的数据集名称
dataset_name = f"philoagents_eval_v{datetime.now().strftime('%Y%m%d')}"
dataset = create_dataset(dataset_name, "Daily evaluation dataset", items)
```

#### 10.2.2 分层评估
```python
# 不同类型的评估使用不同的数据集
basic_eval = get_dataset("philoagents_basic_functionality")  # 基础功能
edge_cases = get_dataset("philoagents_edge_cases")          # 边界情况
stress_test = get_dataset("philoagents_stress_test")        # 压力测试
```

### 10.3 性能优化最佳实践

#### 10.3.1 异步处理
```python
# 使用异步评估避免阻塞主流程
async def async_evaluation_task(x: dict) -> dict:
    # 评估逻辑
    pass

# 批量异步执行
tasks = [async_evaluation_task(item) for item in dataset]
results = await asyncio.gather(*tasks)
```

#### 10.3.2 错误处理
```python
# 优雅处理 Opik 连接错误
def safe_opik_operation(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Opik operation failed: {e}")
            return None
    return wrapper
```

### 10.4 调试技巧

#### 10.4.1 本地调试模式
```python
# 开发时可以禁用 Opik 来加快迭代
if os.getenv("DEBUG_MODE") == "true":
    config = {"configurable": {"thread_id": thread_id}}
else:
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": [opik_tracer],
    }
```

#### 10.4.2 详细日志记录
```python
# 结合 Opik 追踪和本地日志
logger.info(f"Starting evaluation with trace_id: {opik_tracer.trace_id}")
logger.info(f"Dataset size: {len(dataset.items)}")
logger.info(f"Evaluation metrics: {[m.__class__.__name__ for m in metrics]}")
```

---

## 11. 故障排除

### 11.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Opik 配置失败 | API Key 错误或网络问题 | 检查 `COMET_API_KEY` 是否正确 |
| 追踪数据丢失 | 应用异常退出 | 确保调用 `opik_tracer.flush()` |
| 评估速度慢 | 并发度不足 | 增加 `workers` 参数 |
| 提示词版本丢失 | Opik 连接问题 | 检查网络和认证配置 |

### 11.2 调试命令

```bash
# 检查 Opik 连接状态
python -c "import opik; print(opik.Opik().get_workspace())"

# 验证数据集上传
python -c "from philoagents.infrastructure.opik_utils import get_dataset; print(get_dataset('philoagents_evaluation_dataset'))"

# 测试评估流程
cd philoagents-api
python -m tools.evaluate_agent --nb-samples 1 --workers 1
```

---

## 12. 总结

PhiloAgents 项目中的 Opik 集成展示了现代 LLM 应用监控和评估的最佳实践：

### 12.1 技术亮点

1. **无侵入监控**: 通过 LangGraph 回调机制实现零代码侵入的监控
2. **全链路追踪**: 从用户输入到 Agent 响应的完整调用链追踪
3. **自动化评估**: 多维度指标的自动化质量评估
4. **版本化管理**: 提示词和数据集的完整版本控制

### 12.2 实际价值

1. **开发效率**: 快速定位性能瓶颈和问题根因
2. **质量保证**: 持续监控和评估确保 Agent 质量
3. **迭代优化**: 基于数据驱动的模型和提示词优化
4. **生产监控**: 实时了解生产环境中的 Agent 表现

### 12.3 扩展建议

1. **自定义指标**: 根据业务需求开发专门的评估指标
2. **A/B 测试**: 利用 Opik 进行模型版本的 A/B 测试
3. **告警系统**: 基于监控数据设置性能告警
4. **成本优化**: 通过 Token 使用分析优化成本

这套 Opik 集成方案不仅适用于 PhiloAgents，也可以作为其他 LLM 应用的监控和评估参考架构。

---

**文档版本**: v1.0  
**最后更新**: 2024年12月21日  
**相关链接**:
- [Opik 官方文档](https://www.comet.com/docs/opik/)
- [Comet ML 平台](https://www.comet.com/)
- [PhiloAgents GitHub](https://github.com/philoagents/philoagents)
