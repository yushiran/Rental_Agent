from typing import Union
from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode

from app.conversation_service.landlord_workflow import (
    get_landlord_agent_chain,
    get_property_matching_chain,
    get_rental_conversation_summary_chain,
)
from app.conversation_service.landlord_workflow import LandlordState
from app.conversation_service import tools
from app.config import config

retriever_node = ToolNode(tools)


async def landlord_agent_node(state: LandlordState, config: RunnableConfig):
    """Handle landlord agent conversations"""
    summary = state.get("summary", "")
    landlord_chain = get_landlord_agent_chain()

    response = await landlord_chain.ainvoke(
        {
            "messages": state["messages"],
            "landlord_id": state.get("landlord_id", ""),
            "landlord_name": state.get("landlord_name", ""),
            "branch_name": state.get("branch_name", ""),
            "phone": state.get("phone", ""),
            "properties": state.get("properties", []),
            "preferences": state.get("preferences", {}),
            "conversation_context": state.get("conversation_context", ""),
            "current_property_focus": state.get("current_property_focus", ""),
            "tenant_requirements": state.get("tenant_requirements", {}),
            "summary": summary,
        },
        config,
    )
    
    return {"messages": response}


async def property_matching_node(state: LandlordState, config: RunnableConfig):
    """Handle property matching analysis for landlord"""
    matching_chain = get_property_matching_chain()

    response = await matching_chain.ainvoke(
        {
            "properties": state.get("properties", []),
            "tenant_requirements": state.get("tenant_requirements", {}),
        },
        config,
    )
    
    return {"messages": response}


async def summarize_conversation_node(state: LandlordState):
    """Summarize landlord conversation and remove old messages"""
    summary = state.get("summary", "")
    summary_chain = get_rental_conversation_summary_chain(summary)

    response = await summary_chain.ainvoke(
        {
            "messages": state["messages"],
            "conversation_context": state.get("conversation_context", ""),
            "summary": summary,
        }
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


async def connector_node(state: LandlordState):
    """Connector node for landlord workflow routing"""
    return {}
