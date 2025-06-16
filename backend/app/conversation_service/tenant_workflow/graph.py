from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.conversation_service.tenant_workflow import (
    should_summarize_tenant_conversation,
    should_continue_tenant_conversation,
    should_do_property_matching,
)
from app.conversation_service.tenant_workflow import (
    retriever_node,
    tenant_agent_node,
    property_matching_node,
    viewing_feedback_analysis_node,
    summarize_conversation_node,
    connector_node,
)
from app.conversation_service.tenant_workflow import TenantState


@lru_cache(maxsize=1)
def create_tenant_workflow_graph():
    """Create workflow graph for tenant agents"""
    graph_builder = StateGraph(TenantState)

    # Add all nodes
    graph_builder.add_node("tenant_agent_node", tenant_agent_node)
    graph_builder.add_node("property_matching_node", property_matching_node)
    graph_builder.add_node("viewing_feedback_analysis_node", viewing_feedback_analysis_node)
    graph_builder.add_node("retriever_node", retriever_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)
    graph_builder.add_node("connector_node", connector_node)
    
    # Define the flow
    # 首先检查是否需要进行房产匹配
    graph_builder.add_conditional_edges(
        START,
        should_do_property_matching,
        {
            "property_matching": "property_matching_node",
            "conversation": "tenant_agent_node"
        }
    )
    
    # 从匹配节点到会话节点
    graph_builder.add_edge("property_matching_node", "tenant_agent_node")
    
    # 会话节点可能需要使用工具
    graph_builder.add_conditional_edges(
        "tenant_agent_node",
        tools_condition,
        {
            "tools": "retriever_node",
            END: END
        }
    )
    
    graph_builder.add_edge("retriever_node", "tenant_agent_node")
    graph_builder.add_conditional_edges("viewing_feedback_analysis_node", should_summarize_tenant_conversation)
    graph_builder.add_edge("summarize_conversation_node", END)
    
    return graph_builder


# Compiled graph for tenant workflow
tenant_graph = create_tenant_workflow_graph().compile()
