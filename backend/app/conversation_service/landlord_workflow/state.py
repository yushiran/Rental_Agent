from typing import List, Dict, Any, Optional
from langgraph.graph import MessagesState

from app.agents.models import LandlordModel


class LandlordState(MessagesState):
    # Landlord model containing all basic information
    landlord_model: LandlordModel
    
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

    landlord_model = state.get("landlord_model")
    if landlord_model:
        properties_info = f"{len(landlord_model.properties)} properties available"
        landlord_name = landlord_model.name
        landlord_id = landlord_model.landlord_id
        branch_name = landlord_model.branch_name or "N/A"
        phone = landlord_model.phone or "N/A"
    else:
        properties_info = "0 properties available"
        landlord_name = "Unknown"
        landlord_id = "Unknown"
        branch_name = "N/A"
        phone = "N/A"
        
    current_focus = state.get("current_property_focus", "None")
    
    return f"""
LandlordState(
    landlord_id={landlord_id},
    landlord_name={landlord_name},
    branch_name={branch_name},
    phone={phone},
    properties={properties_info},
    current_property_focus={current_focus}, 
    conversation={conversation}
)"""
