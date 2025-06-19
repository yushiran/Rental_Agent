"""
Meta Controller Graph for Multi-Agent Conversations

This module implements a LangGraph-based controller that coordinates conversations
between tenant and landlord agents, with proper streaming support and termination logic.
"""
from typing import List, Dict, Any, TypedDict, Literal
import asyncio
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

from app.config import config
from langgraph.graph import END, StateGraph
from loguru import logger

from app.conversation_service.tenant_workflow.graph import create_tenant_workflow_graph
from app.conversation_service.landlord_workflow.graph import create_landlord_workflow_graph


class MetaState(TypedDict):
    """State maintained by the meta-controller graph."""
    # 必需字段 - 基本对话状态
    session_id: str  # Unique identifier for the conversation session
    messages: List[Dict[str, Any]]  # 历史消息的快照
    active_agent: Literal["tenant", "landlord"]
    tenant_data: Dict[str, Any]
    landlord_data: Dict[str, Any]
    property_data: Dict[str, Any]
    is_terminated: bool
    termination_reason: str


class ExtendedMetaState(MetaState, total=False):
    """
    Extended state with additional optional fields for group negotiations.
    Inherits required fields from MetaState and adds optional fields.
    """
    # 可选字段 - 用于群组协商和会话管理
    match_score: float  # 匹配分数
    match_reasons: List[str]  # 匹配原因
    status: str  # 会话状态 (active, completed, etc.)
    created_at: str  # 创建时间
    task: Any  # 关联的异步任务，使用Any以避免循环导入


def tenant_graph_input_adapter(state: MetaState):
    """Adapt meta state to tenant graph input format."""
    tenant_data = state["tenant_data"]
    return {
        "messages": state["messages"],
        "tenant_id": tenant_data.get("tenant_id", ""),
        "tenant_name": tenant_data.get("name", "Tenant"),
        "annual_income": tenant_data.get("annual_income", 0),
        "max_budget": tenant_data.get("max_budget", 0),
        "has_guarantor": tenant_data.get("has_guarantor", False),
        "min_bedrooms": tenant_data.get("min_bedrooms", 1),
        "max_bedrooms": tenant_data.get("max_bedrooms", 3),
        "preferred_locations": tenant_data.get("preferred_locations", []),
        "is_student": tenant_data.get("is_student", False),
        "has_pets": tenant_data.get("has_pets", False),
        "is_smoker": tenant_data.get("is_smoker", False),
        "num_occupants": tenant_data.get("num_occupants", 1),
        "conversation_context": tenant_data.get("conversation_context", ""),
        "summary": tenant_data.get("summary", ""),
        "search_criteria": tenant_data.get("search_criteria", {}),
        "viewed_properties": tenant_data.get("viewed_properties", []),
        "interested_properties": tenant_data.get("interested_properties", [])
    }


def tenant_graph_output_adapter(output: Dict[str, Any], state: MetaState):
    """Update meta state with tenant graph output."""
    # Update tenant data with any changes from the graph
    if "tenant_name" in output:
        state["tenant_data"]["name"] = output["tenant_name"]
    if "conversation_context" in output:
        state["tenant_data"]["conversation_context"] = output["conversation_context"]
    if "summary" in output:
        state["tenant_data"]["summary"] = output["summary"]
    
    # Update conversation history
    if "messages" in output and output["messages"]:
        last_message = output["messages"][-1]
        state["messages"].append({
            "role": "user",  # Use "ai" for LangChain compatibility
            "content": last_message.content
        })
    
    # Switch active agent
    state["active_agent"] = "landlord"
    return state


def landlord_graph_input_adapter(state: MetaState):
    """Adapt meta state to landlord graph input format."""
    return {
        "messages": state["messages"],
        "landlord_id": state["landlord_data"].get("landlord_id", ""),
        "landlord_name": state["landlord_data"].get("name", "Landlord"),
        "properties": [state["property_data"]] if state["property_data"] else [],
        "conversation_context": state["landlord_data"].get("conversation_context", ""),
        "summary": state["landlord_data"].get("summary", ""),
        "current_property_focus": state["landlord_data"].get("current_property_focus", None),
        "tenant_requirements": state["landlord_data"].get("tenant_requirements", {}),
        "branch_name": state["landlord_data"].get("branch_name", ""),
        "preferences": state["landlord_data"].get("preferences", {})
    }


def landlord_graph_output_adapter(output: Dict[str, Any], state: MetaState):
    """Update meta state with landlord graph output."""
    # Update landlord data with any changes from the graph
    if "landlord_name" in output:
        state["landlord_data"]["name"] = output["landlord_name"]
    if "conversation_context" in output:
        state["landlord_data"]["conversation_context"] = output["conversation_context"]
    if "summary" in output:
        state["landlord_data"]["summary"] = output["summary"]
    
    # Update conversation history
    if "messages" in output and output["messages"]:
        last_message = output["messages"][-1]
        state["messages"].append({
            "role": "assistant",  # Use "ai" for LangChain compatibility
            "content": last_message.content
        })
    
    # Switch active agent
    state["active_agent"] = "tenant"
    return state


async def call_tenant(state: MetaState) -> MetaState:
    """Call tenant agent graph and process results."""
    async with AsyncMongoDBSaver.from_conn_string(
        conn_string=config.mongodb.connection_string,
        db_name=config.mongodb.database,
        checkpoint_collection_name=config.mongodb.mongo_state_checkpoint_collection,
        writes_collection_name=config.mongodb.mongo_state_writes_collection,
    ) as checkpointer:
        graph = create_tenant_workflow_graph()
        tenant_graph = graph.compile(checkpointer=checkpointer)
    intermediate = await tenant_graph.ainvoke(tenant_graph_input_adapter(state))
    return tenant_graph_output_adapter(intermediate, state)


async def call_landlord(state: MetaState) -> MetaState:
    """Call landlord agent graph and process results."""
    async with AsyncMongoDBSaver.from_conn_string(
        conn_string=config.mongodb.connection_string,
        db_name=config.mongodb.database,
        checkpoint_collection_name=config.mongodb.mongo_state_checkpoint_collection,
        writes_collection_name=config.mongodb.mongo_state_writes_collection,
    ) as checkpointer:
        graph = create_landlord_workflow_graph()
        landlord_graph = graph.compile(checkpointer=checkpointer)
    intermediate = await landlord_graph.ainvoke(landlord_graph_input_adapter(state))
    return landlord_graph_output_adapter(intermediate, state)

def should_continue(state: MetaState) -> str:
    """确定对话是否应继续或终止。"""
    # 已经标记为终止的情况
    if state.get("is_terminated", False):
        return "end"

    # 检查最大对话轮数
    if len(state["messages"]) > 20:
        state["is_terminated"] = True
        state["termination_reason"] = "max_turns_reached"
        return "end"
    
    # 需要至少3轮对话
    if len(state["messages"]) < 3:
        return "continue"
    
    # 获取最近两条消息以分析
    last_messages = state["messages"][-3:]
    
    # 拒绝信号词组 - 非常明确的短语
    decline_phrases = [
        "i must decline this property",
        "i must decline your application", 
        "i've decided to look for other options",
        "i've decided to pursue other applicants",
        "i cannot proceed with this rental",
        "i cannot proceed with your rental request"
    ]
    
    # 计数看看连续几条消息中包含拒绝短语的数量
    decline_count = sum(
        1 for msg in last_messages 
        if any(phrase in msg.get("content", "").lower() for phrase in decline_phrases)
    )
    
    # 如果最近三条消息中有两条或以上包含拒绝短语，终止对话
    if decline_count >= 2:
        state["is_terminated"] = True
        state["termination_reason"] = "mutual_rejection"
        return "end"
        
    # 检查是否一方做出明确拒绝，另一方回应了确认词
    for i in range(len(state["messages"]) - 1):
        curr_msg = state["messages"][i]
        next_msg = state["messages"][i + 1]
        
        # 检查当前消息是否包含拒绝短语
        curr_has_decline = any(
            phrase in curr_msg.get("content", "").lower() 
            for phrase in decline_phrases
        )
        
        # 下一条消息是否表示确认理解
        next_has_acknowledgment = any(
            word in next_msg.get("content", "").lower() 
            for word in ["understand", "okay", "alright", "i see", "thank you", "best of luck"]
        )
        
        # 如果一方拒绝且另一方确认，终止对话
        if curr_has_decline and next_has_acknowledgment:
            state["is_terminated"] = True
            state["termination_reason"] = "rejection_acknowledged"
            return "end"
    
    # 默认继续对话
    return "continue"


def create_meta_controller_graph():
    """Create the meta controller graph that coordinates tenant and landlord agents."""
    controller = StateGraph(ExtendedMetaState)
    
    # Add conversation nodes
    controller.add_node("call_tenant", call_tenant)
    controller.add_node("call_landlord", call_landlord)
    
    # Set up the flow - tenant and landlord take turns
    controller.add_conditional_edges("call_tenant", should_continue, {
        "continue": "call_landlord",
        "end": END
    })
    
    controller.add_conditional_edges("call_landlord", should_continue, {
        "continue": "call_tenant",
        "end": END
    })
    
    # Set entry point based on who starts the conversation (typically the tenant)
    controller.set_entry_point("call_tenant")
    
    return controller


# Create and compile the meta controller graph
meta_controller_graph = create_meta_controller_graph().compile()

async def stream_conversation_with_state_update(initial_state: ExtendedMetaState, callback_fn=None, graph=meta_controller_graph):
# Create a copy of the state to avoid modifying the original during iteration
    state_copy = {**initial_state}

    async for event in graph.astream(state_copy):
        logger.debug(f"Event received: {type(event)}")
        
        # The event contains node output directly under the node name key
        if "call_tenant" in event:
            node_output = event["call_tenant"]
        elif "call_landlord" in event:
            node_output = event["call_landlord"]

        initial_state.update(node_output)
        # Find the latest message to yield
        if "messages" in node_output and node_output["messages"]:
            latest_message = node_output["messages"][-1]
            latest_message["active_agent"] = node_output["active_agent"]
            # Execute callback if provided
            if callback_fn:
                await callback_fn(latest_message)
            yield latest_message
        
        # Handle end of conversation
        if event.get("is_terminated", False):
            logger.info(f"Conversation terminated: {event.get('termination_reason', 'unknown reason')}")
            yield {"role": "system", "content": f"Conversation ended: {event.get('termination_reason', 'unknown reason')}"}

