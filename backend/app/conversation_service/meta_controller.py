"""
Meta Controller Graph for Multi-Agent Conversations

This module implements a LangGraph-based controller that coordinates conversations
between tenant and landlord agents, with proper streaming support and termination logic.
"""
from typing import List, Dict, Any, TypedDict, Literal
import asyncio
import traceback
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

from app.config import config
from langgraph.graph import END, StateGraph
from loguru import logger

from app.conversation_service.tenant_workflow.graph import create_tenant_workflow_graph
from app.conversation_service.landlord_workflow.graph import create_landlord_workflow_graph


class MetaState(TypedDict):
    """State maintained by the meta-controller graph."""
    # Required fields - Basic conversation state
    session_id: str  # Unique identifier for the conversation session
    messages: List[Dict[str, Any]]  # Snapshot of message history
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
    # Optional fields - For group negotiations and session management
    match_score: float  # Match score between tenant and property
    match_reasons: List[str]  # Reasons for matching
    status: str  # Session status (active, completed, etc.)
    created_at: str  # Creation timestamp
    task: Any  # Associated async task, Any type to avoid circular imports


def tenant_graph_input_adapter(state: MetaState):
    """Adapt meta state to tenant graph input format."""
    from app.agents.models import TenantModel
    
    tenant_data = state["tenant_data"]
    
    # Create TenantModel from tenant_data
    tenant_model = TenantModel(
        tenant_id=tenant_data.get("tenant_id", ""),
        name=tenant_data.get("name", "Tenant"),
        email=tenant_data.get("email"),
        phone=tenant_data.get("phone"),
        annual_income=tenant_data.get("annual_income", 0),
        has_guarantor=tenant_data.get("has_guarantor", False),
        max_budget=tenant_data.get("max_budget", 0),
        min_bedrooms=tenant_data.get("min_bedrooms", 1),
        max_bedrooms=tenant_data.get("max_bedrooms", 3),
        preferred_locations=tenant_data.get("preferred_locations", []),
        is_student=tenant_data.get("is_student", False),
        has_pets=tenant_data.get("has_pets", False),
        is_smoker=tenant_data.get("is_smoker", False),
        num_occupants=tenant_data.get("num_occupants", 1)
    )
    
    return {
        "messages": state["messages"],
        "tenant_model": tenant_model,
        "conversation_context": tenant_data.get("conversation_context", ""),
        "summary": tenant_data.get("summary", ""),
        "search_criteria": tenant_data.get("search_criteria", {}),
        "viewed_properties": tenant_data.get("viewed_properties", []),
        "interested_properties": tenant_data.get("interested_properties", [])
    }


def tenant_graph_output_adapter(output: Dict[str, Any], state: MetaState):
    """Update meta state with tenant graph output."""
    # Update tenant data with any changes from the tenant model
    if "tenant_model" in output:
        tenant_model = output["tenant_model"]
        state["tenant_data"]["tenant_id"] = tenant_model.tenant_id
        state["tenant_data"]["name"] = tenant_model.name
        state["tenant_data"]["email"] = tenant_model.email
        state["tenant_data"]["phone"] = tenant_model.phone
        state["tenant_data"]["annual_income"] = tenant_model.annual_income
        state["tenant_data"]["has_guarantor"] = tenant_model.has_guarantor
        state["tenant_data"]["max_budget"] = tenant_model.max_budget
        state["tenant_data"]["min_bedrooms"] = tenant_model.min_bedrooms
        state["tenant_data"]["max_bedrooms"] = tenant_model.max_bedrooms
        state["tenant_data"]["preferred_locations"] = tenant_model.preferred_locations
        state["tenant_data"]["is_student"] = tenant_model.is_student
        state["tenant_data"]["has_pets"] = tenant_model.has_pets
        state["tenant_data"]["is_smoker"] = tenant_model.is_smoker
        state["tenant_data"]["num_occupants"] = tenant_model.num_occupants
    
    # Update conversation context and summary
    if "conversation_context" in output:
        state["tenant_data"]["conversation_context"] = output["conversation_context"]
    if "summary" in output:
        state["tenant_data"]["summary"] = output["summary"]
    
    # Update conversation history
    if "messages" in output and output["messages"]:
        last_message = output["messages"][-1]
        logger.debug(f"🔍 Tenant adapter - last_message type: {type(last_message)}")
        logger.debug(f"🔍 Tenant adapter - last_message content: {last_message}")
        
        # 🎯 修复：检查消息类型并正确处理
        if hasattr(last_message, 'content'):
            # 这是一个 AIMessage 对象
            content = last_message.content
        elif isinstance(last_message, dict):
            # 这是一个字典对象
            content = last_message.get("content", "")
        else:
            logger.error(f"🚨 Unknown message type in tenant adapter: {type(last_message)}")
            content = str(last_message)
        
        state["messages"].append({
            "role": "user",  # Use "ai" for LangChain compatibility
            "content": content
        })
    
    # Switch active agent
    state["active_agent"] = "landlord"
    return state


def landlord_graph_input_adapter(state: MetaState):
    """Adapt meta state to landlord graph input format."""
    from app.agents.models import LandlordModel, PropertyModel
    
    landlord_data = state["landlord_data"]
    
    # Convert property data to PropertyModel objects
    properties = []
    if state.get("property_data"):
        if isinstance(state["property_data"], dict):
            properties.append(PropertyModel.from_dict(state["property_data"]))
        elif isinstance(state["property_data"], list):
            for prop_data in state["property_data"]:
                if isinstance(prop_data, dict):
                    properties.append(PropertyModel.from_dict(prop_data))
    
    # Create LandlordModel from landlord_data
    landlord_model = LandlordModel(
        landlord_id=landlord_data.get("landlord_id", ""),
        name=landlord_data.get("name", "Landlord"),
        phone=landlord_data.get("phone"),
        branch_name=landlord_data.get("branch_name"),
        properties=properties,
        preferences=landlord_data.get("preferences", {})
    )
    
    return {
        "messages": state["messages"],
        "landlord_model": landlord_model,
        "conversation_context": landlord_data.get("conversation_context", ""),
        "summary": landlord_data.get("summary", ""),
        "current_property_focus": landlord_data.get("current_property_focus", None)
    }


def landlord_graph_output_adapter(output: Dict[str, Any], state: MetaState):
    """Update meta state with landlord graph output."""
    # Update landlord data with any changes from the landlord model
    if "landlord_model" in output:
        landlord_model = output["landlord_model"]
        state["landlord_data"]["landlord_id"] = landlord_model.landlord_id
        state["landlord_data"]["name"] = landlord_model.name
        state["landlord_data"]["phone"] = landlord_model.phone
        state["landlord_data"]["branch_name"] = landlord_model.branch_name
        state["landlord_data"]["preferences"] = landlord_model.preferences
        # Update properties in property_data if needed
        if landlord_model.properties:
            state["property_data"] = landlord_model.properties[0].model_dump()
    
    # Update conversation context and summary
    if "conversation_context" in output:
        state["landlord_data"]["conversation_context"] = output["conversation_context"]
    if "summary" in output:
        state["landlord_data"]["summary"] = output["summary"]
    if "current_property_focus" in output:
        state["landlord_data"]["current_property_focus"] = output["current_property_focus"]
    
    # Update conversation history
    if "messages" in output and output["messages"]:
        last_message = output["messages"][-1]
        logger.debug(f"🔍 Landlord adapter - last_message type: {type(last_message)}")
        logger.debug(f"🔍 Landlord adapter - last_message content: {last_message}")
        
        # 🎯 修复：检查消息类型并正确处理
        if hasattr(last_message, 'content'):
            # 这是一个 AIMessage 对象
            content = last_message.content
        elif isinstance(last_message, dict):
            # 这是一个字典对象
            content = last_message.get("content", "")
        else:
            logger.error(f"🚨 Unknown message type in landlord adapter: {type(last_message)}")
            content = str(last_message)
        
        state["messages"].append({
            "role": "assistant",  # Use "ai" for LangChain compatibility
            "content": content
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
    try:
        logger.debug(f"🔍 should_continue - state type: {type(state)}")
        logger.debug(f"🔍 should_continue - state keys: {state.keys() if isinstance(state, dict) else 'Not a dict'}")
        
        # 已经标记为终止的情况
        if state.get("is_terminated", False):
            return "end"

        # 检查消息列表
        messages = state.get("messages", [])
        logger.debug(f"🔍 should_continue - messages count: {len(messages)}")
        
        # 检查最大对话轮数
        if len(messages) > 50:
            state["is_terminated"] = True
            state["termination_reason"] = "max_turns_reached"
            return "end"
        
        # 需要至少3轮对话
        if len(messages) < 3:
            return "continue"
        
        # 获取最近两条消息以分析
        last_messages = messages[-3:]
        logger.debug(f"🔍 should_continue - analyzing last {len(last_messages)} messages")
        
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
        decline_count = 0
        for i, msg in enumerate(last_messages):
            logger.debug(f"🔍 should_continue - message {i} type: {type(msg)}")
            
            # 🎯 安全地获取消息内容
            if isinstance(msg, dict):
                content = msg.get("content", "")
            elif hasattr(msg, 'content'):
                content = msg.content
            else:
                logger.warning(f"🚨 Unknown message type in should_continue: {type(msg)}")
                content = str(msg)
            
            # 检查拒绝短语
            if any(phrase in content.lower() for phrase in decline_phrases):
                decline_count += 1
        
        # 如果最近三条消息中有两条或以上包含拒绝短语，终止对话
        if decline_count >= 2:
            state["is_terminated"] = True
            state["termination_reason"] = "mutual_rejection"
            return "end"
            
        # 检查是否一方做出明确拒绝，另一方回应了确认词
        for i in range(len(messages) - 1):
            curr_msg = messages[i]
            next_msg = messages[i + 1]
            
            # 🎯 安全地获取消息内容
            if isinstance(curr_msg, dict):
                curr_content = curr_msg.get("content", "")
            elif hasattr(curr_msg, 'content'):
                curr_content = curr_msg.content
            else:
                curr_content = str(curr_msg)
            
            if isinstance(next_msg, dict):
                next_content = next_msg.get("content", "")
            elif hasattr(next_msg, 'content'):
                next_content = next_msg.content
            else:
                next_content = str(next_msg)
            
            # 检查当前消息是否包含拒绝短语
            curr_has_decline = any(
                phrase in curr_content.lower() 
                for phrase in decline_phrases
            )
            
            # 下一条消息是否表示确认理解
            next_has_acknowledgment = any(
                word in next_content.lower() 
                for word in ["understand", "okay", "alright", "i see", "thank you", "best of luck"]
            )
            
            # 如果一方拒绝且另一方确认，终止对话
            if curr_has_decline and next_has_acknowledgment:
                state["is_terminated"] = True
                state["termination_reason"] = "rejection_acknowledged"
                return "end"
        
        # 默认继续对话
        return "continue"
        
    except Exception as e:
        logger.error(f"🚨 Error in should_continue: {str(e)}")
        import traceback
        logger.error(f"🚨 should_continue traceback: {traceback.format_exc()}")
        return "end"  # 出错时终止对话


def create_meta_controller_graph():
    """Create the meta controller graph that coordinates tenant and landlord agents."""
    controller = StateGraph(ExtendedMetaState)
    
    # Add conversation nodes
    controller.add_node("call_tenant", call_tenant)
    controller.add_node("call_landlord", call_landlord)
    
    # Set up the flow - tenant and landlord take turns
    controller.add_conditional_edges("call_tenant",
        should_continue, 
        {
            "continue": "call_landlord",
            "end": END
        }
    )
    
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
    """Stream conversation with state updates, supporting both matching and negotiation phases"""
    # Create a copy of the state to avoid modifying the original during iteration
    state_copy = {**initial_state}

    try:
        async for event in graph.astream(state_copy):
            logger.debug(f"🔍 Event received: {type(event)} - {event.keys()}")
            
            node_output = None
            # The event contains node output directly under the node name key
            if "call_tenant" in event:
                node_output = event["call_tenant"]
                logger.debug(f"🔍 Tenant node output type: {type(node_output)}")
            elif "call_landlord" in event:
                node_output = event["call_landlord"]
                logger.debug(f"🔍 Landlord node output type: {type(node_output)}")

            if node_output:
                logger.debug(f"🔍 Node output keys: {node_output.keys() if isinstance(node_output, dict) else 'Not a dict'}")
                
                initial_state.update(node_output)
                
                # Find the latest message to yield
                if "messages" in node_output and node_output["messages"]:
                    latest_message = node_output["messages"][-1]
                    logger.debug(f"🔍 Latest message type: {type(latest_message)}")
                    logger.debug(f"🔍 Latest message content preview: {str(latest_message)[:100]}")
                    
                    # 🎯 修复：安全地处理消息属性
                    if hasattr(latest_message, 'content'):
                        # 这是一个 AIMessage 对象
                        message_content = latest_message.content
                    elif isinstance(latest_message, dict):
                        # 这是一个字典对象
                        message_content = latest_message.get("content", "")
                    else:
                        logger.error(f"🚨 Unknown latest message type: {type(latest_message)}")
                        message_content = str(latest_message)
                    
                    # 安全地设置消息属性
                    if isinstance(latest_message, dict):
                        latest_message["active_agent"] = node_output.get("active_agent", "unknown")
                        latest_message['tenant_data'] = node_output.get("tenant_data", {})
                        latest_message['landlord_data'] = node_output.get("landlord_data", {})
                    else:
                        # 为非字典消息创建新的字典格式
                        latest_message = {
                            "role": "assistant" if "landlord" in str(type(latest_message)).lower() else "user",
                            "content": message_content,
                            "active_agent": node_output.get("active_agent", "unknown"),
                            "tenant_data": node_output.get("tenant_data", {}),
                            "landlord_data": node_output.get("landlord_data", {})
                        }
                    
                    # Log the conversation flow
                    agent_type = node_output.get("active_agent", "unknown")
                    logger.info(f"💬 Meta Controller: {agent_type} generated message: {message_content[:100]}...")
                    
                    # Execute callback if provided
                    if callback_fn:
                        try:
                            await callback_fn(latest_message)
                        except Exception as cb_error:
                            logger.error(f"🚨 Callback error: {str(cb_error)}")
                            logger.error(f"🚨 Message type passed to callback: {type(latest_message)}")
                    
                    yield latest_message
            
            # Handle end of conversation
            if isinstance(event, dict) and event.get("is_terminated", False):
                logger.info(f"Conversation terminated: {event.get('termination_reason', 'unknown reason')}")
                yield {"role": "system", "content": f"Conversation ended: {event.get('termination_reason', 'unknown reason')}"}
    
    except Exception as e:
        logger.error(f"🚨 Error in stream_conversation_with_state_update: {str(e)}")
        import traceback
        logger.error(f"🚨 Full traceback: {traceback.format_exc()}")
        raise

