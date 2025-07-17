from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.conversation_service.tenant_workflow.edges import (
    should_summarize_tenant_conversation,
    should_continue_tenant_conversation,
    should_analyze_viewing_feedback
)
from app.conversation_service.tenant_workflow import (
    retriever_node,
    tenant_agent_node,
    viewing_feedback_analysis_node,
    summarize_conversation_node,
)
from app.conversation_service.tenant_workflow import TenantState


@lru_cache(maxsize=1)
def create_tenant_workflow_graph():
    """Create workflow graph for tenant agents"""
    graph_builder = StateGraph(TenantState)

    # Add all nodes
    graph_builder.add_node("tenant_agent_node", tenant_agent_node)
    graph_builder.add_node("viewing_feedback_analysis_node", viewing_feedback_analysis_node)
    graph_builder.add_node("retriever_node", retriever_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)
    
    graph_builder.set_entry_point('tenant_agent_node')
    # 首先检查是否需要进行房产匹配
    graph_builder.add_conditional_edges(
        'tenant_agent_node',
        should_continue_tenant_conversation,
        {
            'tools': 'retriever_node',
            'analyze_feedback': 'viewing_feedback_analysis_node',
            'summarize': 'summarize_conversation_node',
            'end': END
        }
    )

    # 工具节点执行完后回到租客代理节点
    graph_builder.add_edge("retriever_node", "tenant_agent_node")
    
    # 看房反馈分析节点
    graph_builder.add_conditional_edges(
        "viewing_feedback_analysis_node",
        should_analyze_viewing_feedback,
        {
            "continue": "tenant_agent_node",
            "summarize": "summarize_conversation_node"
        }
    )
    
    # 总结节点结束对话
    graph_builder.add_edge("summarize_conversation_node", END)
    
    return graph_builder


# Compiled graph for tenant workflow
tenant_graph = create_tenant_workflow_graph().compile()
