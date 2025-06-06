"""
Core service for managing rental negotiations between multiple parties
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from loguru import logger

from app.mongo import MongoClientWrapper
from app.agents.models import LandlordModel, TenantModel, PropertyModel
from .models import (
    NegotiationSession, ParticipantInfo, ParticipantRole, 
    NegotiationStatus, PropertyInfo
)


class NegotiationService:
    """Service for managing multi-party rental negotiations"""
    
    def __init__(self):
        self.sessions_db = MongoClientWrapper(
            model=NegotiationSession,
            collection_name="negotiation_sessions"
        )
        self.landlords_db = MongoClientWrapper(
            model=LandlordModel,
            collection_name="landlords"
        )
        self.tenants_db = MongoClientWrapper(
            model=TenantModel,
            collection_name="tenants"
        )
        self.properties_db = MongoClientWrapper(
            model=PropertyModel,
            collection_name="properties"
        )
    
    async def create_negotiation_session(
        self,
        property_id: str,
        tenant_ids: List[str],
        landlord_id: str
    ) -> NegotiationSession:
        """Create a new negotiation session"""
        try:
            # Validate participants exist
            landlord = await self._get_landlord(landlord_id)
            tenants = await self._get_tenants(tenant_ids)
            property_info = await self._get_property(property_id, landlord_id)
            
            # Create participants list
            participants = []
            
            # Add landlord
            participants.append(ParticipantInfo(
                participant_id=landlord_id,
                role=ParticipantRole.LANDLORD,
                name=landlord.name
            ))
            
            # Add tenants
            for tenant in tenants:
                participants.append(ParticipantInfo(
                    participant_id=tenant.tenant_id,
                    role=ParticipantRole.TENANT,
                    name=tenant.name
                ))
            
            # Create session
            session_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            session = NegotiationSession(
                session_id=session_id,
                property_id=property_id,
                participants=participants,
                status=NegotiationStatus.ACTIVE,
                created_at=now,
                updated_at=now,
                context={
                    "property": property_info.dict(),
                    "landlord": landlord.to_dict(),
                    "tenants": [t.to_dict() for t in tenants]
                }
            )
            
            # Save to database
            self.sessions_db.ingest_document(session.dict())
            logger.info(f"Created negotiation session {session_id} for property {property_id}")
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to create negotiation session: {str(e)}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get negotiation session by ID"""
        try:
            result = self.sessions_db.fetch_documents(limit=10, query={"session_id": session_id})
            if result:
                return NegotiationSession(**result[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            return None
    
    async def update_session_status(self, session_id: str, status: NegotiationStatus) -> bool:
        """Update session status"""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat()
            }
            result = self.sessions_db.update_document(
                {"session_id": session_id}, 
                {"$set": update_data}
            )
            return result is not None
        except Exception as e:
            logger.error(f"Failed to update session status: {str(e)}")
            return False
    
    async def add_participant(
        self, 
        session_id: str, 
        participant_id: str, 
        role: ParticipantRole
    ) -> bool:
        """Add a participant to an existing session"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
            
            # Get participant details
            if role == ParticipantRole.LANDLORD:
                participant = await self._get_landlord(participant_id)
                name = participant.name
            elif role == ParticipantRole.TENANT:
                participant = await self._get_tenant(participant_id)
                name = participant.name
            else:
                name = "Market Analyst"
            
            # Add to participants
            new_participant = ParticipantInfo(
                participant_id=participant_id,
                role=role,
                name=name
            )
            
            session.participants.append(new_participant)
            session.updated_at = datetime.utcnow().isoformat()
            
            # Update in database
            self.sessions_db.update_document(
                {"session_id": session_id},
                {"$set": session.dict()}
            )
            
            logger.info(f"Added participant {participant_id} to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add participant: {str(e)}")
            return False
    
    async def get_active_sessions_for_participant(self, participant_id: str) -> List[NegotiationSession]:
        """Get all active sessions for a participant"""
        try:
            query = {
                "participants.participant_id": participant_id,
                "status": {"$in": [NegotiationStatus.ACTIVE.value, NegotiationStatus.PENDING.value]}
            }
            results = self.sessions_db.fetch_documents(limit=10,query=query)
            return [NegotiationSession(**result) for result in results]
        except Exception as e:
            logger.error(f"Failed to get active sessions: {str(e)}")
            return []
    
    async def _get_landlord(self, landlord_id: str) -> LandlordModel:
        """Get landlord by ID"""
        result = self.landlords_db.fetch_documents(limit=10,query={"landlord_id": landlord_id})
        if not result:
            raise ValueError(f"Landlord {landlord_id} not found")
        return LandlordModel.from_dict(result[0])
    
    async def _get_tenant(self, tenant_id: str) -> TenantModel:
        """Get tenant by ID"""
        result = self.tenants_db.fetch_documents(limit=10,query={"tenant_id": tenant_id})
        if not result:
            raise ValueError(f"Tenant {tenant_id} not found")
        return TenantModel.from_dict(result[0])
    
    async def _get_tenants(self, tenant_ids: List[str]) -> List[TenantModel]:
        """Get multiple tenants by IDs"""
        tenants = []
        for tenant_id in tenant_ids:
            tenant = await self._get_tenant(tenant_id)
            tenants.append(tenant)
        return tenants
    
    async def _get_property(self, property_id: str, landlord_id: str) -> PropertyInfo:
        """Get property information"""
        # First try to get from properties collection
        result = self.properties_db.fetch_documents(limit=10,query={"property_id": property_id})
        if result:
            prop_data = result[0]
            return PropertyInfo(
                property_id=property_id,
                address=prop_data.get("full_address", "Unknown"),
                monthly_rent=prop_data.get("monthly_rent", 0),
                bedrooms=prop_data.get("bedrooms", 1),
                property_type=prop_data.get("property_sub_type", "Unknown"),
                landlord_id=landlord_id
            )
        
        # Fallback: get from landlord's properties
        landlord = await self._get_landlord(landlord_id)
        for prop in landlord.properties:
            if prop.property_id == property_id:
                return PropertyInfo(
                    property_id=property_id,
                    address=prop.full_address,
                    monthly_rent=prop.monthly_rent,
                    bedrooms=prop.bedrooms,
                    property_type=prop.property_sub_type,
                    landlord_id=landlord_id
                )
        
        raise ValueError(f"Property {property_id} not found for landlord {landlord_id}")
