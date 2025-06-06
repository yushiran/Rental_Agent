"""
Message routing service for multi-party conversations
"""
from typing import AsyncGenerator, Dict, Any, Optional
from loguru import logger

from app.conversation_service.generate_response import (
    get_tenant_streaming_response,
    get_landlord_streaming_response
)
from .models import ParticipantRole
from .negotiation_service import NegotiationService


class MessageRouter:
    """Routes messages to appropriate conversation services"""
    
    def __init__(self):
        self.negotiation_service = NegotiationService()
    
    async def route_message(
        self,
        message: str,
        participant_id: str,
        session_id: str,
        participant_role: ParticipantRole
    ) -> AsyncGenerator[str, None]:
        """Route message to appropriate service based on participant role"""
        try:
            # Get session context
            session = await self.negotiation_service.get_session(session_id)
            if not session:
                yield "Error: Session not found"
                return
            
            # Add session context to message
            context_message = await self._build_context_message(message, session, participant_id)
            
            # Route based on role
            if participant_role == ParticipantRole.TENANT:
                async for chunk in self._route_tenant_message(context_message, participant_id, session):
                    yield chunk
            elif participant_role == ParticipantRole.LANDLORD:
                async for chunk in self._route_landlord_message(context_message, participant_id, session):
                    yield chunk
            else:
                yield "Error: Unknown participant role"
                
        except Exception as e:
            logger.error(f"Error routing message: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def _build_context_message(self, message: str, session, participant_id: str) -> str:
        """Build message with session context"""
        # Get other participants
        other_participants = [
            p for p in session.participants 
            if p.participant_id != participant_id
        ]
        
        context_parts = [
            f"NEGOTIATION SESSION: {session.session_id}",
            f"PROPERTY: {session.context['property']['address']}",
            f"MONTHLY RENT: £{session.context['property']['monthly_rent']}",
            f"PARTICIPANTS: {', '.join([f'{p.name} ({p.role})' for p in other_participants])}",
            "",
            f"MESSAGE: {message}"
        ]
        
        return "\n".join(context_parts)
    
    async def _route_tenant_message(
        self, 
        message: str, 
        tenant_id: str, 
        session
    ) -> AsyncGenerator[str, None]:
        """Route message for tenant participant"""
        try:
            # Get tenant details from session context
            tenant_data = None
            for tenant in session.context.get("tenants", []):
                if tenant["tenant_id"] == tenant_id:
                    tenant_data = tenant
                    break
            
            if not tenant_data:
                yield "Error: Tenant data not found"
                return
            
            async for chunk in get_tenant_streaming_response(
                messages=message,
                tenant_id=tenant_id,
                tenant_name=tenant_data["name"],
                budget_info={
                    "max_budget": tenant_data["max_budget"],
                    "annual_income": tenant_data["annual_income"],
                    "has_guarantor": tenant_data["has_guarantor"]
                },
                preferences={
                    "min_bedrooms": tenant_data["min_bedrooms"],
                    "max_bedrooms": tenant_data["max_bedrooms"],
                    "preferred_locations": tenant_data["preferred_locations"],
                    "is_student": tenant_data["is_student"],
                    "has_pets": tenant_data["has_pets"],
                    "is_smoker": tenant_data["is_smoker"],
                    "num_occupants": tenant_data["num_occupants"]
                },
                new_thread=False
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in tenant message routing: {str(e)}")
            yield f"Error: Failed to process tenant message"
    
    async def _route_landlord_message(
        self, 
        message: str, 
        landlord_id: str, 
        session
    ) -> AsyncGenerator[str, None]:
        """Route message for landlord participant"""
        try:
            # Get landlord details from session context
            landlord_data = session.context.get("landlord")
            
            if not landlord_data:
                yield "Error: Landlord data not found"
                return
            
            async for chunk in get_landlord_streaming_response(
                messages=message,
                landlord_id=landlord_id,
                landlord_name=landlord_data["name"],
                properties=landlord_data["properties"],
                business_info={
                    "branch_name": landlord_data.get("branch_name", ""),
                    "phone": landlord_data.get("phone", ""),
                    "preferences": landlord_data.get("preferences", {})
                },
                new_thread=False
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in landlord message routing: {str(e)}")
            yield f"Error: Failed to process landlord message"
