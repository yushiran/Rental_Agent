from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.conversation_service.landlord_workflow import (
    should_summarize_landlord_conversation,
)
from app.conversation_service.landlord_workflow import (
    landlord_tools_node,
    landlord_agent_node,
    summarize_conversation_node,
)
from app.conversation_service.landlord_workflow import LandlordState


@lru_cache(maxsize=1)
def create_landlord_workflow_graph():
    """Create workflow graph for landlord agents"""
    graph_builder = StateGraph(LandlordState)

    # Add all nodes
    graph_builder.add_node("landlord_agent_node", landlord_agent_node)
    graph_builder.add_node("landlord_tools_node", landlord_tools_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)
    
    # Define the flow
    graph_builder.add_edge(START, "landlord_agent_node")
    graph_builder.add_conditional_edges(
        "landlord_agent_node",
        tools_condition,
        {
            "tools": "landlord_tools_node",
            END: END
        }
    )
    graph_builder.add_edge("landlord_tools_node", "landlord_agent_node")
    
    # 🎯 修复：conditional_edges 需要正确映射 END 常量
    graph_builder.add_conditional_edges(
        "landlord_agent_node", 
        should_summarize_landlord_conversation,
        {
            "summarize_conversation_node": "summarize_conversation_node",
            "__end__": END  # 🔧 匹配函数返回的字符串值
        }
    )
    graph_builder.add_edge("summarize_conversation_node", END)

    return graph_builder


# Compiled graph for landlord workflow
landlord_graph = create_landlord_workflow_graph().compile()
