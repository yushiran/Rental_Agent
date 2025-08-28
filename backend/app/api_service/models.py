"""
API Models for the Rental Agent System
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
# Import existing status models
from app.agents.models.tenant_model import RentalStatus
from app.agents.models.property_model import PropertyRentalStatus
from app.agents.models.landlord_model import LandlordRentalStatus


class StartSessionRequest(BaseModel):
    """Request model for starting a negotiation session"""
    max_tenants: Optional[int] = 1


class StartSessionResponse(BaseModel):
    """Response model for starting a negotiation session"""
    message: str
    active_sessions: int
    session_ids: List[str]


class SessionInfo(BaseModel):
    """Model for session information"""
    session_id: str
    tenant_name: str
    landlord_name: str
    property_address: str
    monthly_rent: float
    match_score: float
    match_reasons: List[str]
    status: str
    created_at: str
    websocket_status: Optional[Dict[str, Any]] = None


class NegotiationStats(BaseModel):
    """Model for negotiation statistics"""
    active_sessions: int
    completed_sessions: int
    total_sessions: int
    total_messages: int
    average_messages_per_session: float
    average_match_score: float


class ResetMemoryResponse(BaseModel):
    """Response model for memory reset"""
    message: str
    status: str


class WebSocketMessage(BaseModel):
    """Base model for WebSocket messages"""
    type: str
    timestamp: str
    session_id: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class PingMessage(BaseModel):
    """Ping message for WebSocket heartbeat"""
    type: str = "ping"


class SendMessageRequest(BaseModel):
    """Request to send a message via WebSocket"""
    type: str = "send_message"
    message: str
    sender_type: str  # "tenant" or "landlord"

class StartNegotiationRequest(BaseModel):
    tenant_ids: List[str] = []

class InitializeRequest(BaseModel):
    tenant_count: int = 3
    reset_data: bool = False

# LLM analysis direct output model
class NegotiationStatusUpdate(BaseModel):
    """LLM analyzes negotiation results and directly outputs three status objects"""
    
    # Basic negotiation information
    negotiation_successful: bool = Field(description="Whether negotiation successfully reached an agreement")
    confidence_score: float = Field(description="Analysis confidence score (0-1)", ge=0, le=1)
    
    # Three status objects - directly corresponding to database models
    tenant_rental_status: RentalStatus = Field(description="Tenant rental status")
    property_rental_status: PropertyRentalStatus = Field(description="Property rental status") 
    landlord_rental_status: LandlordRentalStatus = Field(description="Landlord rental statistics")