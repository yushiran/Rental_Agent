from typing_extensions import Literal

from app.conversation_service.landlord_workflow.state import LandlordState
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

    return "__end__"  # 🔧 Return string directly instead of END constant


def should_continue_landlord_conversation(
    state: LandlordState,
) -> Literal["landlord_agent_node", "__end__"]:
    """Determine next step in landlord conversation flow"""
    messages = state["messages"]
    
    if not messages:
        return "__end__"  # 🔧 Return string instead of END constant
    
    # Continue with landlord agent by default - no property matching needed as tenants handle matching
    return "landlord_agent_node"
