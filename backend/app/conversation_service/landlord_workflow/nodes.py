from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode
from loguru import logger

from app.conversation_service.landlord_workflow import (
    get_landlord_agent_chain,
    get_rental_conversation_summary_chain,
)
from app.conversation_service.landlord_workflow import LandlordState
from app.conversation_service import landlord_tools
from app.config import config
from app.utils.RateLimitBackOff import invoke_chain_with_backoff

landlord_tools_node = ToolNode(landlord_tools)

async def landlord_agent_node(state: LandlordState, config: RunnableConfig):
    """Handle landlord agent conversations - responding to tenant inquiries about matched properties"""
    # Get landlord model from state
    landlord_model = state.get("landlord_model")
    if not landlord_model:
        raise ValueError("landlord_model is required in LandlordState")
    
    # Prepare structured data for the chain
    landlord_info = {
        "landlord_id": landlord_model.landlord_id,
        "name": landlord_model.name,
        "branch_name": landlord_model.branch_name,
        "phone": landlord_model.phone,
        "properties": [prop.model_dump() for prop in landlord_model.properties],
        "preferences": landlord_model.preferences
    }
    
    property_info = {
        "address": state.get("current_property_focus", "")
    }
    
    conversation_data = {
        "conversation_context": state.get("conversation_context", ""),
        "summary": state.get("summary", ""),
        "negotiation_round": state.get("negotiation_round", 1)
    }
    
    # Get the chain with properly formatted context
    landlord_chain = get_landlord_agent_chain(
        landlord_info=landlord_info,
        property_info=property_info,
        conversation_data=conversation_data
    )

    # Invoke the chain with just messages
    response = await invoke_chain_with_backoff(
        landlord_chain,
        {"messages": state["messages"]},
        config,
    )
    
    return {"messages": response}


# Property matching functionality removed - tenants are now responsible for initiating matching


async def summarize_conversation_node(state: LandlordState):
    """Summarize landlord conversation and remove old messages"""
    # 🎯 修复：只使用纯文本消息进行摘要，避免tool_calls问题
    original_messages = state.get("messages", [])
    text_only_messages = []
    
    # 提取纯文本消息，跳过包含tool_calls的消息
    for msg in original_messages:
        if hasattr(msg, 'role') and hasattr(msg, 'content'):
            if msg.role in ['user', 'system'] or (msg.role == 'assistant' and not hasattr(msg, 'tool_calls')):
                if msg.content and isinstance(msg.content, str):
                    text_only_messages.append(msg)
    
    logger.info(f"🧹 Using {len(text_only_messages)} text-only messages for summary (from {len(original_messages)} total)")
    
    # Prepare conversation data
    conversation_data = {
        "conversation_context": state.get("conversation_context", ""),
        "summary": state.get("summary", "")
    }
    
    summary_chain = get_rental_conversation_summary_chain(conversation_data)
    
    # 🎯 使用纯文本消息进行摘要
    response = await invoke_chain_with_backoff(
        summary_chain,
        {"messages": text_only_messages},
    )

    # Get the number of messages to keep after summary from config
    messages_after_summary = 5
    if config.agents and config.agents.total_messages_after_summary:
        messages_after_summary = config.agents.total_messages_after_summary

    delete_messages = [
        RemoveMessage(id=m.id)
        for m in state["messages"][: -messages_after_summary]
    ]
    return {"summary": response.content, "messages": delete_messages}
