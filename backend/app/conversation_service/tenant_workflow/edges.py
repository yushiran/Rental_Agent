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


def should_do_property_matching(state: TenantState) -> Literal["property_matching", "conversation"]:
    """判断是否需要进行房产匹配
    
    检查当前会话是否需要进行房产匹配:
    1. 如果明确要求进行匹配，则执行匹配
    2. 如果有可用房产但没有匹配的房产，则执行匹配
    3. 如果没有匹配过房产，则执行匹配
    4. 如果已经完成匹配，则直接进入会话
    
    这确保了租客始终先匹配房产，再与房东对话。
    """
    # 检查是否有明确的匹配请求
    matching_requested = state.get("match_properties", False)
    
    # 检查是否已经有匹配的房产
    has_matched_properties = len(state.get("matched_properties", [])) > 0
    
    # 检查是否有可用房产进行匹配
    available_properties = state.get("properties", [])
    has_available_properties = len(available_properties) > 0
    
    # 如果有明确的匹配请求，或者有可用房产但没有匹配结果，则进行匹配
    if matching_requested or (has_available_properties and not has_matched_properties):
        return "property_matching"
    
    # 否则直接进行对话
    return "conversation"
