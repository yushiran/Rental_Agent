from typing import List, Dict, Any, Optional
from langgraph.graph import MessagesState


class LandlordState(MessagesState):
    # Landlord basic information
    landlord_id: str
    landlord_name: str
    branch_name: Optional[str]
    phone: Optional[str]
    
    # Property and business information
    properties: List[Dict[str, Any]]  # Properties owned/managed by this landlord
    preferences: Dict[str, Any]  # Landlord preferences (e.g., payment terms, lease duration)
    
    # Conversation management
    conversation_context: str
    summary: str
    current_property_focus: Optional[str]  # Currently discussed property (already matched by tenant)


def landlord_state_to_str(state: LandlordState) -> str:
    """Convert LandlordState to string representation for logging/debugging."""
    if "summary" in state and bool(state["summary"]):
        conversation = state["summary"]
    elif "messages" in state and bool(state["messages"]):
        conversation = f"Messages: {len(state['messages'])} total"
    else:
        conversation = "No conversation history"

    properties_info = f"{len(state.get('properties', []))} properties available"
    current_focus = state.get("current_property_focus", "None")
    
    return f"""
LandlordState(
    landlord_id={state.get("landlord_id", "Unknown")},
    landlord_name={state.get("landlord_name", "Unknown")},
    branch_name={state.get("branch_name", "N/A")},
    phone={state.get("phone", "N/A")},
    properties={properties_info},
    current_property_focus={current_focus}, 
    conversation={conversation}
)"""
