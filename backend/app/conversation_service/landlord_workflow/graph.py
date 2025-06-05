from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.conversation_service.landlord_workflow import (
    should_summarize_landlord_conversation,
    should_continue_landlord_conversation,
)
from app.conversation_service.landlord_workflow import (
    retriever_node,
    landlord_agent_node,
    property_matching_node,
    summarize_conversation_node,
    connector_node,
)
from app.conversation_service.landlord_workflow import LandlordState


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


# Compiled graph for landlord workflow
landlord_graph = create_landlord_workflow_graph().compile()
