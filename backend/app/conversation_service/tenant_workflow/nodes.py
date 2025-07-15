from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode
import json
from loguru import logger

from app.conversation_service.tenant_workflow import (
    get_tenant_agent_chain,
    get_property_matching_chain,
    get_viewing_feedback_analysis_chain,
    get_rental_conversation_summary_chain,
)
from app.conversation_service.tenant_workflow import TenantState
from app.conversation_service import tools
from app.config import config

retriever_node = ToolNode(tools)


async def tenant_agent_node(state: TenantState, config: RunnableConfig):
    """Handle tenant agent conversations"""
    # Get tenant model from state
    tenant_model = state.get("tenant_model")
    if not tenant_model:
        raise ValueError("tenant_model is required in TenantState")
    
    # Prepare structured data for the chain
    tenant_info = {
        "tenant_id": tenant_model.tenant_id,
        "name": tenant_model.name,
        "email": tenant_model.email,
        "phone": tenant_model.phone,
        "annual_income": tenant_model.annual_income,
        "has_guarantor": tenant_model.has_guarantor,
        "max_budget": tenant_model.max_budget,
        "min_bedrooms": tenant_model.min_bedrooms,
        "max_bedrooms": tenant_model.max_bedrooms,
        "preferred_locations": tenant_model.preferred_locations,
        "is_student": tenant_model.is_student,
        "has_pets": tenant_model.has_pets,
        "is_smoker": tenant_model.is_smoker,
        "num_occupants": tenant_model.num_occupants,
        "search_criteria": state.get("search_criteria", {}),
        "viewed_properties": state.get("viewed_properties", []),
        "interested_properties": state.get("interested_properties", [])
    }
    
    conversation_data = {
        "conversation_context": state.get("conversation_context", ""),
        "summary": state.get("summary", "")
    }
    
    # Get the chain with properly formatted context
    tenant_chain = get_tenant_agent_chain(
        tenant_info=tenant_info,
        conversation_data=conversation_data
    )

    # Debug: Print the formatted prompt before invoking
    context_data = {**tenant_info, **conversation_data}
    
    # Invoke the chain with just messages
    response = await tenant_chain.ainvoke(
        {
            "messages": state["messages"]
        },
        config,
    )
    
    return {"messages": response}


async def property_matching_node(state: TenantState, config: RunnableConfig):
    """Handle property matching analysis for tenant"""
    # 获取所有可用的房产
    available_properties = state.get("properties", [])
    
    if not available_properties:
        # 如果没有可用房产，返回一条消息说明情况
        no_properties_msg = "非常抱歉，目前没有可用的房产可以匹配。请稍后再试或修改您的搜索条件。"
        return {
            "messages": [{"role": "assistant", "content": no_properties_msg}],
            "matched_properties": [],
            "match_score": 0,
            "match_reasons": ["没有可用房产"],
            "matched_landlord": {}
        }
    
    # Get tenant model from state
    tenant_model = state.get("tenant_model")
    if not tenant_model:
        raise ValueError("tenant_model is required in TenantState")
    
    # Prepare structured data for the chain
    tenant_info = {
        "max_budget": tenant_model.max_budget,
        "min_bedrooms": tenant_model.min_bedrooms,
        "max_bedrooms": tenant_model.max_bedrooms,
        "preferred_locations": tenant_model.preferred_locations,
        "is_student": tenant_model.is_student,
        "has_pets": tenant_model.has_pets,
        "is_smoker": tenant_model.is_smoker,
        "num_occupants": tenant_model.num_occupants,
        "has_guarantor": tenant_model.has_guarantor
    }
    
    # Get the chain with properly formatted context
    matching_chain = get_property_matching_chain(
        tenant_info=tenant_info,
        properties=available_properties
    )
    
    # Invoke the chain
    response = await matching_chain.ainvoke({}, config)
    
    # Process the matching results (implement your logic)
    # ...
    
    return {
        "messages": [{"role": "assistant", "content": response}],
        "matched_properties": available_properties[:1],  # For example, take the first property
        "match_score": 75,  # Example score
        "match_reasons": ["Budget compatible", "Location match"],
        "matched_landlord": {"id": "L123", "name": "Example Landlord"}
    }


async def viewing_feedback_analysis_node(state: TenantState, config: RunnableConfig):
    """Handle property viewing feedback analysis"""
    # Get the latest message which should contain viewing feedback
    latest_message = state["messages"][-1] if state["messages"] else None
    
    # Get tenant model from state
    tenant_model = state.get("tenant_model")
    if not tenant_model:
        raise ValueError("tenant_model is required in TenantState")
    
    # Prepare viewing info
    viewing_info = {
        "property_address": state.get("current_property_focus", "Not specified"),
        "viewing_date": state.get("viewing_date", "Not specified"),
        "attendees": [tenant_model.name]
    }
    
    # Prepare feedback data
    feedback_data = {
        "tenant_feedback": latest_message.content if latest_message else "",
        "interests": state.get("interests", "None specified"),
        "concerns": state.get("concerns", "None specified"),
        "questions": state.get("questions", "None specified")
    }
    
    # Get the chain with properly formatted context
    feedback_chain = get_viewing_feedback_analysis_chain(
        viewing_info=viewing_info,
        feedback_data=feedback_data
    )
    
    # Debug: Print the formatted prompt before invoking
    context_data = {**viewing_info, **feedback_data}
    # await debug_print_prompt(feedback_chain, context_data, state["messages"])
    
    # Invoke the chain with empty message (context is already provided in the chain)
    response = await feedback_chain.ainvoke({}, config)
    
    return {"messages": response}


async def summarize_conversation_node(state: TenantState):
    """Summarize tenant conversation and remove old messages"""
    # Prepare conversation data
    conversation_data = {
        "conversation_context": state.get("conversation_context", ""),
        "summary": state.get("summary", "")
    }
    
    summary_chain = get_rental_conversation_summary_chain(conversation_data)

    # Debug: Print the formatted prompt before invoking
    # await debug_print_prompt(summary_chain, conversation_data, state["messages"])
    
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


async def connector_node(state: TenantState):
    """Connector node for tenant workflow routing"""
    return {}
