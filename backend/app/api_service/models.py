"""
API models for multi-party rental negotiations
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ParticipantRole(str, Enum):
    """Participant roles in the negotiation"""
    TENANT = "tenant"
    LANDLORD = "landlord"


class ParticipantInfo(BaseModel):
    """Basic participant information"""
    participant_id: str
    role: ParticipantRole
    name: str
    is_active: bool = True


class NegotiationStatus(str, Enum):
    """Negotiation status enum"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PropertyInfo(BaseModel):
    """Property information for negotiation"""
    property_id: str
    address: str
    monthly_rent: float
    bedrooms: int
    property_type: str
    landlord_id: str


class NegotiationSession(BaseModel):
    """Negotiation session data structure"""
    session_id: str
    property_id: str
    participants: List[ParticipantInfo]
    status: NegotiationStatus = NegotiationStatus.PENDING
    created_at: str
    updated_at: str
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Chat message for negotiation"""
    message: str
    participant_id: str
    session_id: Optional[str] = None


class StreamChatMessage(BaseModel):
    """Streaming chat message"""
    message: str
    participant_id: str
    session_id: str


class NegotiationRequest(BaseModel):
    """Request to start a new negotiation"""
    property_id: str
    tenant_ids: List[str]
    landlord_id: str


class JoinNegotiationRequest(BaseModel):
    """Request to join an existing negotiation"""
    session_id: str
    participant_id: str


class NegotiationResponse(BaseModel):
    """Response from negotiation operations"""
    session_id: str
    status: str
    message: str
    participants: List[ParticipantInfo]


class MessageResponse(BaseModel):
    """Response from message operations"""
    response: str
    participant_id: str
    session_id: str


class StreamingResponse(BaseModel):
    """Response for streaming operations"""
    chunk: Optional[str] = None
    response: Optional[str] = None
    streaming: bool
    error: Optional[str] = None
