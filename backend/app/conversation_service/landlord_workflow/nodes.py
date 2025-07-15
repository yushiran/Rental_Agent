from typing import Union
from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode
import json
from loguru import logger

from app.conversation_service.landlord_workflow import (
    get_landlord_agent_chain,
    get_rental_conversation_summary_chain,
)
from app.conversation_service.landlord_workflow import LandlordState
from app.conversation_service import tools
from app.config import config

retriever_node = ToolNode(tools)

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
        "summary": state.get("summary", "")
    }
    
    # Get the chain with properly formatted context
    landlord_chain = get_landlord_agent_chain(
        landlord_info=landlord_info,
        property_info=property_info,
        conversation_data=conversation_data
    )

    # Invoke the chain with just messages
    response = await landlord_chain.ainvoke(
        {
            "messages": state["messages"]
        },
        config,
    )
    
    return {"messages": response}


# Property matching functionality removed - tenants are now responsible for initiating matching


async def summarize_conversation_node(state: LandlordState):
    """Summarize landlord conversation and remove old messages"""
    # Prepare conversation data
    conversation_data = {
        "conversation_context": state.get("conversation_context", ""),
        "summary": state.get("summary", "")
    }
    
    summary_chain = get_rental_conversation_summary_chain(conversation_data)
    
    # Invoke with just messages - context is already provided in the chain
    response = await summary_chain.ainvoke(
        {
            "messages": state["messages"]
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
