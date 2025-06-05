from typing import List, Dict, Any, Optional
from langgraph.graph import MessagesState


class TenantState(MessagesState):
    # Tenant basic information
    tenant_id: str
    tenant_name: str
    email: Optional[str]
    phone: Optional[str]
    
    # Financial information
    annual_income: float
    has_guarantor: bool
    max_budget: float
    
    # Property preferences
    min_bedrooms: int
    max_bedrooms: int
    preferred_locations: List[Dict[str, float]]
    
    # Personal circumstances
    is_student: bool
    has_pets: bool
    is_smoker: bool
    num_occupants: int
    
    # Conversation management
    conversation_context: str
    summary: str
    search_criteria: Dict[str, Any]
    viewed_properties: List[str]
    interested_properties: List[str]


def tenant_state_to_str(state: TenantState) -> str:
    """Convert TenantState to string representation for logging/debugging."""
    if "summary" in state and bool(state["summary"]):
        conversation = state["summary"]
    elif "messages" in state and bool(state["messages"]):
        conversation = f"Messages: {len(state['messages'])} total"
    else:
        conversation = "No conversation history"

    budget_info = f"£{state.get('max_budget', 0)}/month"
    bedrooms_info = f"{state.get('min_bedrooms', 1)}-{state.get('max_bedrooms', 3)} bedrooms"
    viewed_count = len(state.get("viewed_properties", []))
    interested_count = len(state.get("interested_properties", []))
    
    return f"""
TenantState(
    tenant_id={state.get("tenant_id", "Unknown")},
    tenant_name={state.get("tenant_name", "Unknown")},
    email={state.get("email", "N/A")},
    budget={budget_info},
    bedrooms={bedrooms_info},
    is_student={state.get("is_student", False)},
    has_pets={state.get("has_pets", False)},
    viewed_properties={viewed_count},
    interested_properties={interested_count},
    conversation={conversation}
)"""
