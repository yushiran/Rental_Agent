"""
Multi-Agent Communication API - Simplified Rental Negotiation System
Focused on implementing core functionality for tenant-landlord search and negotiation
"""
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
import json
import uuid
import time
import random
from typing import List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from opik.integrations.langchain import OpikTracer
from loguru import logger
from pydantic import BaseModel

from app.conversation_service.reset_conversation import reset_conversation_state
from app.utils.opik_utils import configure
from app.mongo import initialize_database
from app.config import config
from app.api_service.models import StartNegotiationRequest, InitializeRequest

from .group_negotiation import GroupNegotiationService
from .websocket import ConnectionManager
from app.agents.agents_factory import AgentDataInitializer
from app.data_analysis.market_analyzer_api import analysis_router
from app.config import NEGOTIATION_ROUND

configure()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    logger.info("Starting Multi-Agent Communication API")

    # Initialize database
    await initialize_database()

    yield
    logger.info("Shutting down Multi-Agent Communication API")
    opik_tracer = OpikTracer()
    opik_tracer.flush()

# Create FastAPI application
app = FastAPI(
    title="Multi-Agent Communication API",
    description="Intelligent negotiation system between tenants and landlords",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate connection manager
manager = ConnectionManager()
# Initialize Agent factory
agent_factory = AgentDataInitializer()

app.include_router(analysis_router)

# Initialize service (pass WebSocket manager)
group_service = GroupNegotiationService(websocket_manager=manager)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Multi-Agent Communication API",
        "version": "1.0.0",
        "description": "Intelligent system for tenant-landlord search and negotiation",
        "features": [
            "Intelligent tenant-landlord matching",
            "Real-time negotiation dialogue",
            "Group negotiation management",
            "WebSocket real-time communication",
            "LangGraph streaming Agent controller"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "rental-agent-backend"
    }

@app.get("/config")
async def get_config():
    """
    Get configuration information needed by frontend
    
    Returns:
        dict: Configuration information including Google Maps API key
    """
    try:
        if not config.google_maps or not config.google_maps.api_key:
            raise HTTPException(status_code=500, detail="Google Maps API key not configured")
        
        return {
            "google_maps_api_key": config.google_maps.api_key
        }
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")



@app.post("/initialize")
async def initialize_system(request: InitializeRequest):
    """
    Initialize system - Generate tenants and map data
    
    Args:
        tenant_count: Number of tenants to generate
        reset_data: Whether to reset existing data
    
    Returns:
        - tenants: Generated tenant list
        - properties: Property data (for map display)
        - landlords: Landlord data
        - map_data: Map visualization data
    """
    try:
        logger.info(f"Starting system initialization: tenant_count={request.tenant_count}, reset_data={request.reset_data}")
        

        await agent_factory.clear_all_data()
        logger.info("Cleared existing data")
        
        # Check if data already exists
        existing_properties = await agent_factory.get_properties_count()
        existing_landlords = await agent_factory.get_landlords_count()
        
        # If no property and landlord data, initialize basic data first
        if existing_properties == 0 or existing_landlords == 0:
            logger.info("Initializing property and landlord data...")
            await agent_factory.initialize_properties_and_landlords()
        
        # Generate specified number of tenants
        logger.info(f"Generating {request.tenant_count} tenants...")
        tenants = await agent_factory.generate_tenants(request.tenant_count)
        
        # Get all property data for map display
        properties = await agent_factory.get_all_properties()
        landlords = await agent_factory.get_all_landlords()
        
        # Prepare map data
        map_data = []
        for prop in properties:
            # Safely get monthly rent
            try:
                # If there's a price field, manually calculate monthly rent
                price_info = prop.get("price", {})
                if isinstance(price_info, dict) and price_info:
                    amount = price_info.get("amount", 0)
                    frequency = price_info.get("frequency", "monthly")
                    
                    if frequency == 'weekly':
                        monthly_rent = int(amount * 52 / 12)
                    elif frequency == 'yearly':
                        monthly_rent = int(amount / 12)
                    else:
                        monthly_rent = int(amount)
                else:
                    # If no price field, use default value
                    monthly_rent = 2000
            except Exception as e:
                logger.warning(f"Error calculating monthly rent for property {prop.get('property_id', 'unknown')}: {e}")
                monthly_rent = 2000
            
            map_data.append({
                "id": prop.get("property_id", "unknown"),
                "latitude": prop.get("location", {}).get("latitude", 51.5074),
                "longitude": prop.get("location", {}).get("longitude", -0.1278),
                "address": prop.get("display_address", "Unknown Address"),
                "price": monthly_rent,
                "bedrooms": prop.get("bedrooms", 1),
                "property_type": prop.get("property_sub_type", "Unknown"),
                "landlord_id": prop.get("landlord_id", "unknown")
            })
        
        result = {
            "message": "System initialization successful",
            "data": {
                "tenants": tenants,
                "tenants_count": len(tenants),
                "properties": properties,
                "properties_count": len(properties),
                "landlords": landlords,
                "landlords_count": len(landlords),
                "map_data": map_data
            },
            "status": "initialized"
        }
        
        logger.info(f"System initialization completed: {len(tenants)} tenants, {len(properties)} properties, {len(landlords)} landlords")
        return result
        
    except Exception as e:
        logger.error(f"System initialization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

    
@app.post("/start-negotiation")
async def start_negotiation(request: StartNegotiationRequest):
    """
    Start negotiation process - Based on generated tenants, start negotiation using actual tenant and landlord names
    
    Args:
        tenant_ids: List of tenant IDs to participate in negotiation, if empty uses all tenants
    
    Returns:
        - Created negotiation session information, including actual agent names
        - WebSocket connection information
    """
    global NEGOTIATION_ROUND
    NEGOTIATION_ROUND += 1  # Increment each time called
    try:
        logger.info(f"Starting negotiation process, tenant IDs: {request.tenant_ids}")
        
        # Get all initialized tenant and landlord data
        all_tenants = await group_service._get_all_tenants()
        all_landlords = await group_service._get_all_landlords()

        if not all_tenants or not all_landlords:
            raise HTTPException(status_code=400, detail="No available tenant or landlord data, please call initialization API first")
        
        # Get valid tenants
        participating_tenants = []
        for tenant_id in request.tenant_ids:
            tenant_data = await group_service._get_tenant_by_id(tenant_id)
            if tenant_data and tenant_data.rental_status.is_rented is False:
                participating_tenants.append(tenant_data)
            else:
                logger.warning(f"Tenant {tenant_id} does not exist, skipping")
        
        if not participating_tenants:
            raise HTTPException(status_code=400, detail="No valid tenants found")
        
        # Create negotiation sessions - create one session for each tenant
        sessions = []
        total_sessions = len(participating_tenants)  # Create session for each participating tenant
        
        for i in range(total_sessions):
            tenant = participating_tenants[i]
            
            # Use GroupNegotiationService to find best property match
            best_match = await group_service.find_best_property_for_tenant(tenant.tenant_id)
            
            if not best_match:
                logger.warning(f"No suitable property found for tenant {tenant.name}, skipping session creation")
                continue
            else:
                # Use GroupNegotiationService to create formal negotiation session
                negotiation_session = await group_service.create_negotiation_session(tenant, best_match)
                if negotiation_session:
                    session_data = negotiation_session
                else:
                    logger.error(f"Failed to create negotiation session for tenant {tenant.name}")
                    session_id = f"session_{uuid.uuid4().hex[:8]}_{int(time.time())}"
                    session_data = {
                        "session_id": session_id,
                        "tenant_name": tenant.name,
                        "landlord_name": best_match.get("landlord_name", "unknown landlord"),
                        "property_address": best_match.get("display_address", "Unknown Address"),
                        "status": "error",
                        "created_at": datetime.now().isoformat(),
                        "negotiation_round": NEGOTIATION_ROUND
                    }
            
            sessions.append(session_data)
            
            # Send initialization message to WebSocket
            try:
                tenant_name = tenant.get("name") if isinstance(tenant, dict) else tenant.name
                landlord_name = session_data.get("landlord_name", "unknown landlord")
                await manager.send_message_to_session(session_data["session_id"], {
                    "type": "negotiation_started",
                    "session_id": session_data["session_id"],
                    "message": f"Negotiation started: {tenant_name} is negotiating with {landlord_name}",
                    "session_info": session_data,
                    "timestamp": datetime.now().isoformat()
                })
                
                
            except Exception as ws_error:
                logger.warning(f"WebSocket message sending failed {session_data['session_id']}: {ws_error}")

        result = {
            "message": "Negotiation process started successfully",
            "total_sessions": len(sessions),
            "sessions": sessions,
            "websocket_info": {
                "endpoint": f"/ws/{session_data['session_id']}",
                "description": "Connect to WebSocket to receive real-time negotiation messages"
            }
        }
        
        logger.info(f"Negotiation process started successfully: {len(sessions)} sessions, using actual agent names")
        return result
        
    except Exception as e:
        logger.error(f"Failed to start negotiation process: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start negotiation: {str(e)}")

@app.get("/sessions")
async def get_all_sessions():
    """Get all negotiation sessions"""
    try:
        sessions = await group_service.get_all_active_sessions()
        return {
            "total_sessions": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Failed to get sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get detailed information for a specific negotiation session"""
    try:
        session = await group_service.get_session_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session does not exist")
        
        # Special handling: Check if WebSocket connection exists, if so inform frontend to maintain connection
        has_websocket = session_id in manager.active_connections
        
        # Return session information and WebSocket connection status
        response_data = {
            **session,
            "websocket_status": {
                "has_active_connection": has_websocket,
                "connection_count": len(manager.active_connections.get(session_id, set())),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return response_data
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get negotiation system statistics"""
    try:
        stats = group_service.get_negotiation_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_negotiation(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time negotiation communication and streaming message push"""
    await manager.connect(websocket, session_id)
    
    try:
        # Send connection success message
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket connection established",
            "timestamp": datetime.now().isoformat()
        })
        
        # If it's a specific session, verify session exists and send session information
        if session_id != "global":
            session = await group_service.get_session_info(session_id)
            if session:
                await websocket.send_json({
                    "type": "session_info",
                    "session_id": session_id,
                    "tenant_name": session["tenant_name"],
                    "landlord_name": session["landlord_name"],
                    "property_address": session["property_address"],
                    "monthly_rent": session["monthly_rent"],
                    "match_score": session["match_score"],
                    "status": session["status"],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Send additional confirmation message to ensure frontend knows WebSocket connection is working properly
                await websocket.send_json({
                    "type": "websocket_ready",
                    "message": "Real-time conversation ready, dialogue will continue",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Send session history messages
                if session.get("messages"):
                    await websocket.send_json({
                        "type": "history",
                        "messages": session["messages"],
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Keep connection active, listen for messages
        ping_counter = 0
        while True:
            try:
                # Use shorter timeout to enable periodic heartbeat sending
                data = await asyncio.wait_for(websocket.receive_json(), timeout=15)
                
                # Handle heartbeat
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong", 
                        "timestamp": datetime.now().isoformat()
                    })
                    ping_counter += 1
                    # Send session status update every 5 heartbeats
                    if ping_counter % 5 == 0:
                        await websocket.send_json({
                            "type": "connection_status",
                            "status": "active",
                            "session_id": session_id,
                            "timestamp": datetime.now().isoformat()
                        })
                    continue
                
                # Handle other message types
                await websocket.send_json({
                    "type": "message_received",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
                
            except asyncio.TimeoutError:
                # Send active heartbeat on timeout to maintain connection
                try:
                    await websocket.send_json({
                        "type": "server_ping", 
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.debug(f"Heartbeat sending failed, connection may be disconnected: {str(e)}")
                    break
            
            except Exception as e:
                if isinstance(e, WebSocketDisconnect):
                    logger.debug(f"WebSocket client disconnected: {str(e)}")
                else:
                    logger.debug(f"WebSocket message processing error: {str(e)}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        manager.disconnect(websocket, session_id)


@app.post("/reset-memory")
async def reset_conversation():
    """Reset conversation state"""
    try:
        result = await reset_conversation_state()
        logger.info("Conversation memory reset successfully")
        return result
    except Exception as e:
        logger.error(f"Memory reset failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
