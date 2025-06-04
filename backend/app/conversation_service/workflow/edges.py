from typing_extensions import Literal
from typing import Union

from langgraph.graph import END

from app.conversation_service.workflow.state import LandlordState, TenantState
from app.config import config


def should_summarize_landlord_conversation(
    state: LandlordState,
) -> Literal["summarize_conversation_node", "__end__"]:
    """Determine if landlord conversation should be summarized based on message count"""
    messages = state["messages"]
    
    # Get the summary trigger threshold from config, default to 30 if not configured
    summary_trigger = 30
    if config.agents and config.agents.total_messages_summary_trigger:
        summary_trigger = config.agents.total_messages_summary_trigger

    if len(messages) > summary_trigger:
        return "summarize_conversation_node"

    return END


def should_summarize_tenant_conversation(
    state: TenantState,
) -> Literal["summarize_conversation_node", "__end__"]:
    """Determine if tenant conversation should be summarized based on message count"""
    messages = state["messages"]
    
    # Get the summary trigger threshold from config, default to 30 if not configured
    summary_trigger = 30
    if config.agents and config.agents.total_messages_summary_trigger:
        summary_trigger = config.agents.total_messages_summary_trigger

    if len(messages) > summary_trigger:
        return "summarize_conversation_node"

    return END


def should_continue_landlord_conversation(
    state: LandlordState,
) -> Literal["landlord_agent_node", "property_matching_node", "__end__"]:
    """Determine next step in landlord conversation flow"""
    messages = state["messages"]
    
    if not messages:
        return END
    
    last_message = messages[-1]
    
    # If tenant requirements are being discussed, go to property matching
    if ("tenant" in last_message.content.lower() or 
        "requirement" in last_message.content.lower() or
        "match" in last_message.content.lower()):
        return "property_matching_node"
    
    # Continue with landlord agent by default
    return "landlord_agent_node"


def should_continue_tenant_conversation(
    state: TenantState,
) -> Literal["tenant_agent_node", "property_matching_node", "viewing_feedback_analysis_node", "__end__"]:
    """Determine next step in tenant conversation flow"""
    messages = state["messages"]
    
    if not messages:
        return END
    
    last_message = messages[-1]
    content_lower = last_message.content.lower()
    
    # If discussing viewing feedback
    if ("viewing" in content_lower or "visited" in content_lower or "feedback" in content_lower):
        return "viewing_feedback_analysis_node"
    
    # If looking for property matches
    if ("search" in content_lower or "find" in content_lower or "property" in content_lower):
        return "property_matching_node"
    
    # Continue with tenant agent by default
    return "tenant_agent_node"


def route_by_agent_type(
    state: Union[LandlordState, TenantState],
) -> Literal["landlord_agent_node", "tenant_agent_node", "__end__"]:
    """Route to appropriate agent based on state type"""
    if isinstance(state, LandlordState):
        return "landlord_agent_node"
    elif isinstance(state, TenantState):
        return "tenant_agent_node"
    else:
        return END