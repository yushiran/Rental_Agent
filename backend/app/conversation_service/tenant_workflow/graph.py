from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.conversation_service.tenant_workflow.edges import (
    should_continue_tenant_conversation,
)
from app.conversation_service.tenant_workflow import (
    tenant_tools_node,
    tenant_agent_node,
    summarize_conversation_node,
)
from app.conversation_service.tenant_workflow import TenantState


@lru_cache(maxsize=1)
def create_tenant_workflow_graph():
    """Create workflow graph for tenant agents"""
    graph_builder = StateGraph(TenantState)

    # Add all nodes
    graph_builder.add_node("tenant_agent_node", tenant_agent_node)
    # graph_builder.add_node("viewing_feedback_analysis_node", viewing_feedback_analysis_node)
    graph_builder.add_node("tenant_tools_node", tenant_tools_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)
    
    graph_builder.set_entry_point('tenant_agent_node')
    # First check if property matching is needed
    graph_builder.add_conditional_edges(
        'tenant_agent_node',
        should_continue_tenant_conversation,
        {
            'tools': 'tenant_tools_node',
            # 'analyze_feedback': 'viewing_feedback_analysis_node',
            'summarize': 'summarize_conversation_node',
            'end': END  # Use END constant
        }
    )

    # After tool node execution, return to tenant agent node
    graph_builder.add_edge("tenant_tools_node", "tenant_agent_node")
    
    # Summary node ends the conversation
    graph_builder.add_edge("summarize_conversation_node", END)
    
    return graph_builder


# Compiled graph for tenant workflow
tenant_graph = create_tenant_workflow_graph().compile()
