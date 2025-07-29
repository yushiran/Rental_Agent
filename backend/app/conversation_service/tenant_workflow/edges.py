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

def should_continue_tenant_conversation(state: TenantState) -> Literal["tools", "analyze_feedback", "summarize", "end"]:
    """
    决定租客对话的下一步行为
    """
    messages = state.get("messages", [])
    if not messages:
        return "end"
    
    latest_message = messages[-1]
    
    # 🎯 修复：安全地获取消息内容
    if hasattr(latest_message, 'content'):
        # 这是一个 AIMessage/HumanMessage 对象
        content = latest_message.content.lower()
    elif isinstance(latest_message, dict):
        # 这是一个字典对象
        content = latest_message.get("content", "").lower()
    else:
        # 未知类型，转换为字符串
        content = str(latest_message).lower()
    
    # 检查是否需要使用工具（检索信息）
    if any(keyword in content for keyword in ["search", "find", "look up", "检索", "查找"]):
        return "tools"
    
    # # 检查是否包含看房反馈
    # if any(keyword in content for keyword in ["viewing", "visit", "看房", "参观", "feedback"]):
    #     return "analyze_feedback"
    
    # 检查是否需要总结对话
    if len(messages) > 10 or any(keyword in content for keyword in ["summarize", "总结", "结束"]):
        return "summarize"
    
    # 检查是否结束对话
    if any(keyword in content for keyword in ["goodbye", "bye", "再见", "结束"]):
        return "end"
    
    return "end"


def should_analyze_viewing_feedback(state: TenantState) -> Literal["continue", "connect", "summarize"]:
    """
    决定看房反馈分析后的下一步
    """
    # 检查分析结果
    analysis_result = state.get("viewing_analysis", {})
    
    if analysis_result.get("should_summarize"):
        return "summarize"
    else:
        return "continue"
