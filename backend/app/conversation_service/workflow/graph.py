from functools import lru_cache
from typing import Union

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.conversation_service.workflow import (
    should_summarize_landlord_conversation,
    should_summarize_tenant_conversation,
    should_continue_landlord_conversation,
    should_continue_tenant_conversation,
    route_by_agent_type,
)
from app.conversation_service.workflow import (
    retriever_node,
    landlord_agent_node,
    tenant_agent_node,
    property_matching_node,
    viewing_feedback_analysis_node,
    summarize_conversation_node,
    connector_node,
)
from app.conversation_service.workflow import(
    LandlordState,
    TenantState,
)

@lru_cache(maxsize=1)
def create_landlord_workflow_graph():
    """Create workflow graph for landlord agents"""
    graph_builder = StateGraph(LandlordState)

    # Add all nodes
    graph_builder.add_node("landlord_agent_node", landlord_agent_node)
    graph_builder.add_node("property_matching_node", property_matching_node)
    graph_builder.add_node("retriever_node", retriever_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)
    graph_builder.add_node("connector_node", connector_node)
    
    # Define the flow
    graph_builder.add_edge(START, "landlord_agent_node")
    graph_builder.add_conditional_edges(
        "landlord_agent_node",
        tools_condition,
        {
            "tools": "retriever_node",
            END: "connector_node"
        }
    )
    graph_builder.add_edge("retriever_node", "landlord_agent_node")
    graph_builder.add_conditional_edges("connector_node", should_continue_landlord_conversation)
    graph_builder.add_conditional_edges("property_matching_node", should_summarize_landlord_conversation)
    graph_builder.add_edge("summarize_conversation_node", END)
    
    return graph_builder


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
    graph_builder.add_edge(START, "tenant_agent_node")
    graph_builder.add_conditional_edges(
        "tenant_agent_node",
        tools_condition,
        {
            "tools": "retriever_node",
            END: "connector_node"
        }
    )
    graph_builder.add_edge("retriever_node", "tenant_agent_node")
    graph_builder.add_conditional_edges("connector_node", should_continue_tenant_conversation)
    graph_builder.add_conditional_edges("property_matching_node", should_summarize_tenant_conversation)
    graph_builder.add_conditional_edges("viewing_feedback_analysis_node", should_summarize_tenant_conversation)
    graph_builder.add_edge("summarize_conversation_node", END)
    
    return graph_builder


@lru_cache(maxsize=1)  
def create_unified_workflow_graph():
    """Create a unified workflow graph that can handle both landlord and tenant states"""
    # For now, we'll use Union state type - this might need adjustment based on LangGraph capabilities
    # Alternative: create separate graphs and route externally
    graph_builder = StateGraph(Union[LandlordState, TenantState])

    # Add all nodes
    graph_builder.add_node("landlord_agent_node", landlord_agent_node)
    graph_builder.add_node("tenant_agent_node", tenant_agent_node)
    graph_builder.add_node("property_matching_node", property_matching_node)
    graph_builder.add_node("viewing_feedback_analysis_node", viewing_feedback_analysis_node)
    graph_builder.add_node("retriever_node", retriever_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)
    graph_builder.add_node("connector_node", connector_node)
    
    # Define the flow
    graph_builder.add_conditional_edges(START, route_by_agent_type)
    
    # Landlord flow
    graph_builder.add_conditional_edges(
        "landlord_agent_node",
        tools_condition,
        {
            "tools": "retriever_node",
            END: "connector_node"
        }
    )
    
    # Tenant flow  
    graph_builder.add_conditional_edges(
        "tenant_agent_node",
        tools_condition,
        {
            "tools": "retriever_node", 
            END: "connector_node"
        }
    )
    
    graph_builder.add_edge("retriever_node", "connector_node")
    graph_builder.add_conditional_edges("connector_node", route_by_agent_type)
    graph_builder.add_edge("property_matching_node", "connector_node")
    graph_builder.add_edge("viewing_feedback_analysis_node", "connector_node")
    graph_builder.add_edge("summarize_conversation_node", END)
    
    return graph_builder

# Compiled graphs for different agent types
landlord_graph = create_landlord_workflow_graph().compile()
tenant_graph = create_tenant_workflow_graph().compile()
unified_graph = create_unified_workflow_graph().compile()

# Default graph for LangGraph Studio (using landlord as default)
graph = landlord_graph
