"""
API Models for the Rental Agent System
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


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