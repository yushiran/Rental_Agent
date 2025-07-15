from typing import List, Dict, Any, Optional
from langgraph.graph import MessagesState

from app.agents.models import TenantModel


class TenantState(MessagesState):
    # Tenant model containing all basic information
    tenant_model: TenantModel
    
    # Property matching
    properties: List[Dict[str, Any]]  # 可用于匹配的房产列表
    match_properties: bool  # 是否需要进行房产匹配
    matched_properties: List[Dict[str, Any]]  # 已经匹配的房产列表
    matched_landlord: Dict[str, Any]  # 匹配的房东信息
    match_score: float  # 匹配分数
    match_reasons: List[str]  # 匹配原因
    
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

    tenant_model = state.get("tenant_model")
    if tenant_model:
        budget_info = f"£{tenant_model.max_budget}/month"
        bedrooms_info = f"{tenant_model.min_bedrooms}-{tenant_model.max_bedrooms} bedrooms"
        tenant_name = tenant_model.name
        tenant_id = tenant_model.tenant_id
        email = tenant_model.email or "N/A"
        is_student = tenant_model.is_student
        has_pets = tenant_model.has_pets
    else:
        budget_info = "£0/month"
        bedrooms_info = "1-3 bedrooms"
        tenant_name = "Unknown"
        tenant_id = "Unknown"
        email = "N/A"
        is_student = False
        has_pets = False
    
    viewed_count = len(state.get("viewed_properties", []))
    interested_count = len(state.get("interested_properties", []))
    
    return f"""
TenantState(
    tenant_id={tenant_id},
    tenant_name={tenant_name},
    email={email},
    budget={budget_info},
    bedrooms={bedrooms_info},
    is_student={is_student},
    has_pets={has_pets},
    viewed_properties={viewed_count},
    interested_properties={interested_count},
    conversation={conversation}
)"""
