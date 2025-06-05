from typing_extensions import Literal

from langgraph.graph import END

from app.conversation_service.tenant_workflow.state import TenantState
from app.config import config


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
