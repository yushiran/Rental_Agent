 **最佳实践文档**

* 多 Agent 架构
* 对话轮次控制
* 条件终止机制
* ✅ 流式输出（Streaming）方案：包括两种主流方式

---

# 🧠 多 Agent 对话控制 + 流式输出：LangGraph 最佳实践指南

---

## 🧩 目录

1. [项目架构概述](#项目架构概述)
2. [状态设计](#状态设计)
3. [Agent 子图设计](#agent-子图设计)
4. [Meta Controller Graph 调度器](#meta-controller-graph-调度器)
5. [终止逻辑设计](#终止逻辑设计)
6. [流式输出实现方案](#流式输出实现方案)
7. [完整执行流程](#完整执行流程)
8. [补充建议](#补充建议)

---

## 📐 项目架构概述

```text
Meta Controller Graph
    ├── tenant_agent_graph (LangGraph 子图)
    └── landlord_agent_graph (LangGraph 子图)
```

* 每个 agent 是一个独立的 LangGraph 图，含有 `summarize`、`retrieval` 等多个节点。
* Controller 图控制两者轮流对话，并判断是否终止。
* 所有历史信息保存在共享状态中。

---

## 🧾 状态设计

```python
class MetaState(TypedDict):
    history: List[dict]          # [{"role": "tenant", "content": "..."}, ...]
    active_agent: str            # 当前要说话的 agent："tenant" or "landlord"
```

---

## 🤖 Agent 子图设计（以 tenant 为例）

```python
# tenant_agent_graph = GraphRunnable

def tenant_graph_input_adapter(state: MetaState):
    return {"history": state["history"]}

def tenant_graph_output_adapter(output: dict, state: MetaState):
    state["history"] = output["history"]
    state["active_agent"] = "landlord"
    return state

def call_tenant(state: MetaState) -> MetaState:
    intermediate = tenant_agent_graph.invoke(tenant_graph_input_adapter(state))
    return tenant_graph_output_adapter(intermediate, state)
```

landlord 同理，只是角色相反。

---

## 🔄 Meta Controller Graph 调度器

```python
controller = StateGraph()

controller.add_node("call_tenant", call_tenant)
controller.add_node("call_landlord", call_landlord)

def should_continue(state: MetaState) -> str:
    last_msg = state["history"][-1]["content"].lower()
    if any(keyword in last_msg for keyword in ["agreement", "stop", "not interested"]):
        return "end"
    return "continue"

controller.add_conditional_edges("call_tenant", should_continue, {
    "continue": "call_landlord",
    "end": END
})

controller.add_conditional_edges("call_landlord", should_continue, {
    "continue": "call_tenant",
    "end": END
})

controller.set_entry_point("call_tenant")
meta_graph = controller.compile()
```

---

## 🛑 终止逻辑设计建议

* **关键词规则匹配（如上）**：适合轻量级对话；
* **调用小型分类 LLM 判断对话语气是否为终止意图**；
* **引入 conversation summarizer 检查是否达成协议**。

---

## 📡 流式输出实现方案

LangGraph 支持 **逐步骤回调**，你可以通过监听 `stream` 事件来实现对话过程的流式展示。

### ✅ 方法 1：LangGraph 的 `stream` 模式（推荐）

```python
for event in meta_graph.stream(initial_state):
    if event.type == "on_node_end":
        node_output = event.output
        if "history" in node_output:
            latest = node_output["history"][-1]
            print(f"{latest['role']}: {latest['content']}")
```

> ✔️ 这种方式每执行一个节点，就能拿到其输出，实时打印或发送前端。

---

### ✅ 方法 2：Agent 子图内部手动调用 callback（可选）

若你想更细粒度掌控流式输出（比如 summarize 阶段、retrieval 阶段也流式）：

在 agent 的各节点中添加：

```python
def retrieval_node(state):
    documents = do_retrieval(state)
    yield {"event": "retrieval_complete", "documents": documents}
    return {"retrieved": documents}
```

然后在 `meta_graph.stream()` 中监听：

```python
for event in meta_graph.stream(initial_state):
    if hasattr(event, 'event') and event.event == "retrieval_complete":
        print("🔍 Retrieved Docs:", event.documents)
```

---

## ✅ 完整执行流程示意

```python
initial_state = {
    "history": [{"role": "tenant", "content": "Hi, I’m looking for a 2-bed flat."}],
    "active_agent": "tenant"
}

for step in meta_graph.stream(initial_state):
    if step.type == "on_node_end":
        node_output = step.output
        if "history" in node_output:
            latest = node_output["history"][-1]
            print(f"🗣️ {latest['role']}: {latest['content']}")
```

> 输出样例：

```text
🗣️ tenant: Hi, I’m looking for a 2-bed flat.
🗣️ landlord: Sure, I have one available in Camden.
🗣️ tenant: Great, what’s the rent?
...
```

---

## 🧠 补充建议

| 目标        | 技术路线                             |
| --------- | -------------------------------- |
| 支持多个角色加入  | Controller graph 添加中介 agent 调度节点 |
| 多轮结构优化    | 状态中记录轮次 `turn_count`             |
| 持久记录与分析   | 将 `history` 写入 MongoDB 或 SQLite  |
| Web前端流式显示 | 结合 WebSocket 推送每次对话内容到 UI        |

---

如需我为你生成一个可直接运行的多 agent LangGraph 对话框架（含流式输出），或封装一个 StreamManager 来打印可读性更强的输出，请告诉我。也欢迎你分享你的两个子图结构，我可以帮你整合进 controller graph。
