"""
Complete Multi-Party Rental Negotiation API
Integrates all services and endpoints
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from opik.integrations.langchain import OpikTracer
from loguru import logger

from app.conversation_service.reset_conversation import reset_conversation_state
from app.utils.opik_utils import configure

from .models import (
    ChatMessage, StreamChatMessage, NegotiationRequest, JoinNegotiationRequest,
    NegotiationResponse, MessageResponse, StreamingResponse, ParticipantRole
)
from .negotiation_service import NegotiationService
from .message_router import MessageRouter

configure()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    logger.info("Starting Multi-Party Rental Negotiation API")
    yield
    logger.info("Shutting down Multi-Party Rental Negotiation API")
    opik_tracer = OpikTracer()
    opik_tracer.flush()


# Create FastAPI app
app = FastAPI(
    title="Multi-Party Rental Negotiation API",
    description="Advanced API for managing rental negotiations between multiple landlords and tenants",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
negotiation_service = NegotiationService()
message_router = MessageRouter()


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Multi-Party Rental Negotiation API",
        "version": "2.0.0",
        "description": "API for managing rental negotiations between multiple parties",
        "features": [
            "Multi-party negotiations",
            "Real-time WebSocket communication", 
            "Market analyst integration",
            "Session management",
            "Analytics and monitoring"
        ]
    }


@app.post("/negotiation/create", response_model=NegotiationResponse)
async def create_negotiation(request: NegotiationRequest):
    """Create a new multi-party negotiation session"""
    try:
        session = await negotiation_service.create_negotiation_session(
            property_id=request.property_id,
            tenant_ids=request.tenant_ids,
            landlord_id=request.landlord_id
        )
        
        logger.info(f"Created negotiation session {session.session_id}")
        
        return NegotiationResponse(
            session_id=session.session_id,
            status=session.status.value,
            message="Negotiation session created successfully",
            participants=session.participants
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create negotiation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create negotiation session")


@app.post("/negotiation/{session_id}/join", response_model=NegotiationResponse)
async def join_negotiation(session_id: str, request: JoinNegotiationRequest):
    """Join an existing negotiation session"""
    try:
        # In a real application, determine role from authentication context
        # For now, assume tenant role
        role = ParticipantRole.TENANT
        
        success = await negotiation_service.add_participant(
            session_id=session_id,
            participant_id=request.participant_id,
            role=role
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or failed to join")
        
        session = await negotiation_service.get_session(session_id)
        
        logger.info(f"Participant {request.participant_id} joined session {session_id}")
        
        return NegotiationResponse(
            session_id=session.session_id,
            status=session.status.value,
            message="Successfully joined negotiation",
            participants=session.participants
        )
        
    except Exception as e:
        logger.error(f"Failed to join negotiation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/negotiation/{session_id}")
async def get_negotiation(session_id: str):
    """Get negotiation session details"""
    try:
        session = await negotiation_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Negotiation session not found")
        
        return session
        
    except Exception as e:
        logger.error(f"Failed to get negotiation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/participant/{participant_id}/negotiations")
async def get_participant_negotiations(participant_id: str):
    """Get all active negotiations for a participant"""
    try:
        sessions = await negotiation_service.get_active_sessions_for_participant(participant_id)
        return {"sessions": sessions}
        
    except Exception as e:
        logger.error(f"Failed to get participant negotiations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(chat_message: ChatMessage):
    """Simple chat endpoint (legacy support)"""
    try:
        return {
            "response": f"Received message from {chat_message.participant_id}: {chat_message.message}",
            "note": "This is a legacy endpoint. Use WebSocket endpoints for real-time communication."
        }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/negotiation/{session_id}")
async def websocket_negotiation(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time negotiation"""
    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")
    
    try:
        # Verify session exists
        session = await negotiation_service.get_session(session_id)
        if not session:
            await websocket.send_json({"error": "Negotiation session not found"})
            return
        
        # Send session info
        await websocket.send_json({
            "type": "session_info",
            "session_id": session_id,
            "participants": [
                {"id": p.participant_id, "name": p.name, "role": p.role}
                for p in session.participants
            ],
            "property": session.context.get("property", {}),
            "status": session.status.value
        })
        
        while True:
            data = await websocket.receive_json()
            
            if "message" not in data or "participant_id" not in data:
                await websocket.send_json({
                    "error": "Invalid message format. Required fields: 'message' and 'participant_id'"
                })
                continue
            
            try:
                # Get participant role
                participant_role = None
                participant_name = None
                for participant in session.participants:
                    if participant.participant_id == data["participant_id"]:
                        participant_role = participant.role
                        participant_name = participant.name
                        break
                
                if not participant_role:
                    await websocket.send_json({"error": "Participant not found in session"})
                    continue
                
                # Send message info
                await websocket.send_json({
                    "type": "message_received",
                    "from": participant_name,
                    "role": participant_role,
                    "message": data["message"]
                })
                
                # Send initial streaming indicator
                await websocket.send_json({"type": "response_start", "streaming": True})
                
                # Stream response
                full_response = ""
                async for chunk in message_router.route_message(
                    message=data["message"],
                    participant_id=data["participant_id"],
                    session_id=session_id,
                    participant_role=ParticipantRole(participant_role)
                ):
                    full_response += chunk
                    await websocket.send_json({
                        "type": "response_chunk",
                        "chunk": chunk
                    })
                
                # Send final response
                await websocket.send_json({
                    "type": "response_complete",
                    "response": full_response,
                    "streaming": False,
                    "participant_id": data["participant_id"]
                })
                
            except Exception as e:
                logger.error(f"Error in websocket message processing: {str(e)}")
                await websocket.send_json({
                    "type": "error", 
                    "error": str(e)
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Legacy WebSocket endpoint for backward compatibility"""
    await websocket.accept()
    
    try:
        await websocket.send_json({
            "type": "info",
            "message": "Connected to legacy chat endpoint. Consider using /ws/negotiation/{session_id} for full features."
        })
        
        while True:
            data = await websocket.receive_json()
            
            if "message" not in data or "participant_id" not in data:
                await websocket.send_json({
                    "error": "Invalid message format. Required fields: 'message' and 'participant_id'"
                })
                continue
            
            # Simple echo response for legacy support
            await websocket.send_json({
                "response": f"Legacy endpoint: {data['message']}",
                "streaming": False
            })
    
    except WebSocketDisconnect:
        pass


@app.post("/reset-memory")
async def reset_conversation():
    """Resets the conversation state. It deletes the two collections needed for keeping LangGraph state in MongoDB.

    Raises:
        HTTPException: If there is an error resetting the conversation state.
    Returns:
        dict: A dictionary containing the result of the reset operation.
    """
    try:
        result = await reset_conversation_state()
        logger.info("Conversation memory reset successfully")
        return result
    except Exception as e:
        logger.error(f"Failed to reset memory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
