"""
API Models for the Rental Agent System
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
# 导入现有的状态模型
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

# LLM分析的直接输出模型
class NegotiationStatusUpdate(BaseModel):
    """LLM分析协商结果并直接输出三个状态对象"""
    
    # 协商基本信息
    negotiation_successful: bool = Field(description="协商是否成功达成协议")
    confidence_score: float = Field(description="分析置信度 (0-1)", ge=0, le=1)
    
    # 三个状态对象 - 直接对应数据库模型
    tenant_rental_status: RentalStatus = Field(description="租客租赁状态")
    property_rental_status: PropertyRentalStatus = Field(description="房产租赁状态") 
    landlord_rental_status: LandlordRentalStatus = Field(description="房东租赁统计")