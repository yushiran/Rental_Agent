from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio

from ..agents import RentalAgentManager, Property
from ..config import LLMSettings
from .websocket_handler import WebSocketHandler
from loguru import logger


# Pydantic model definitions
class TenantCreateRequest(BaseModel):
    name: str
    budget: float
    preferred_areas: List[str]
    requirements: Dict[str, Any]


class LandlordCreateRequest(BaseModel):
    name: str
    properties: List[Dict[str, Any]]
    pricing_strategy: str = "market_based"
    tenant_preferences: Optional[Dict[str, Any]] = None


class PropertyRequest(BaseModel):
    id: str
    address: str
    price: float
    property_type: str
    bedrooms: int
    bathrooms: int
    area: float
    amenities: List[str]
    available_date: str
    description: str
    landlord_id: str


class ConversationStartRequest(BaseModel):
    tenant_name: str
    landlord_name: str
    analyst_name: str
    property_id: str
    max_rounds: int = 20


class MessageRequest(BaseModel):
    conversation_id: str
    message: str
    sender: str = "User"


class ScenarioRequest(BaseModel):
    tenant: Dict[str, Any]
    landlord: Dict[str, Any]
    property: Dict[str, Any]


class RentalAPI:
    """Rental System API Service"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        self.app = FastAPI(
            title="Intelligent Rental Agent System",
            description="Multi-Agent rental system API based on AutoGen",
            version="1.0.0"
        )
        
        # 配置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 初始化管理器
        self.agent_manager = RentalAgentManager(llm_config)
        self.websocket_handler = WebSocketHandler()
        
        # 注册路由
        self._register_routes()
        
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.get("/")
        async def root():
            return {
                "message": "租房智能Agent系统API",
                "version": "1.0.0",
                "status": "running"
            }
            
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
            
        # Agent管理相关API
        @self.app.post("/agents/tenant")
        async def create_tenant(request: TenantCreateRequest):
            """创建租客Agent"""
            try:
                tenant = self.agent_manager.create_tenant(
                    name=request.name,
                    budget=request.budget,
                    preferred_areas=request.preferred_areas,
                    requirements=request.requirements
                )
                return {
                    "status": "success",
                    "agent_name": tenant.name,
                    "agent_type": "tenant",
                    "message": f"租客Agent '{tenant.name}' 创建成功"
                }
            except Exception as e:
                logger.error(f"Error creating tenant: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/agents/landlord")
        async def create_landlord(request: LandlordCreateRequest):
            """创建房主Agent"""
            try:
                # 转换属性列表
                properties = [Property(**prop) for prop in request.properties]
                
                landlord = self.agent_manager.create_landlord(
                    name=request.name,
                    properties=properties,
                    pricing_strategy=request.pricing_strategy,
                    tenant_preferences=request.tenant_preferences
                )
                return {
                    "status": "success",
                    "agent_name": landlord.name,
                    "agent_type": "landlord",
                    "properties_count": len(properties),
                    "message": f"房主Agent '{landlord.name}' 创建成功"
                }
            except Exception as e:
                logger.error(f"Error creating landlord: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/agents/analyst")
        async def create_analyst(name: str = "市场分析师"):
            """创建市场分析师Agent"""
            try:
                analyst = self.agent_manager.create_market_analyst(name=name)
                return {
                    "status": "success",
                    "agent_name": analyst.name,
                    "agent_type": "market_analyst",
                    "message": f"市场分析师Agent '{analyst.name}' 创建成功"
                }
            except Exception as e:
                logger.error(f"Error creating analyst: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/agents/{agent_name}")
        async def get_agent_info(agent_name: str):
            """获取Agent信息"""
            try:
                info = self.agent_manager.get_agent_info(agent_name)
                if "error" in info:
                    raise HTTPException(status_code=404, detail=info["error"])
                return info
            except Exception as e:
                logger.error(f"Error getting agent info: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/agents")
        async def list_agents():
            """获取所有Agent列表"""
            try:
                agents = []
                for name, agent in self.agent_manager.agents.items():
                    agents.append({
                        "name": name,
                        "role": agent.profile.role,
                        "type": type(agent).__name__
                    })
                return {"agents": agents, "count": len(agents)}
            except Exception as e:
                logger.error(f"Error listing agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/agents/{agent_name}/properties")
        async def get_agent_properties(agent_name: str):
            """获取房主Agent的房源列表"""
            try:
                agent = self.agent_manager.agents.get(agent_name)
                if not agent:
                    raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
                    
                if not hasattr(agent, 'properties'):
                    raise HTTPException(status_code=400, detail=f"Agent {agent_name} is not a landlord")
                    
                properties = []
                for prop_id, prop in agent.properties.items():
                    properties.append({
                        "id": prop.id,
                        "address": prop.address,
                        "price": prop.price,
                        "property_type": prop.property_type,
                        "bedrooms": prop.bedrooms,
                        "bathrooms": prop.bathrooms,
                        "area": prop.area,
                        "amenities": prop.amenities,
                        "description": prop.description
                    })
                    
                return {"properties": properties, "count": len(properties)}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting agent properties: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # 对话管理相关API
        @self.app.post("/conversations/start")
        async def start_conversation(request: ConversationStartRequest):
            """开始租房对话"""
            try:
                conversation_id = self.agent_manager.start_rental_conversation(
                    tenant_name=request.tenant_name,
                    landlord_name=request.landlord_name,
                    analyst_name=request.analyst_name,
                    property_id=request.property_id,
                    max_rounds=request.max_rounds
                )
                
                # 通知WebSocket客户端
                await self.websocket_handler.broadcast_message({
                    "type": "conversation_started",
                    "conversation_id": conversation_id,
                    "participants": [request.tenant_name, request.landlord_name, request.analyst_name]
                })
                
                return {
                    "status": "success",
                    "conversation_id": conversation_id,
                    "message": "对话已开始"
                }
            except Exception as e:
                logger.error(f"Error starting conversation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.post("/conversations/message")
        async def send_message(request: MessageRequest):
            """发送消息到对话"""
            try:
                response = self.agent_manager.send_message(
                    conversation_id=request.conversation_id,
                    message=request.message,
                    sender=request.sender
                )
                
                # 通知WebSocket客户端
                await self.websocket_handler.broadcast_message({
                    "type": "new_message",
                    "conversation_id": request.conversation_id,
                    "message": request.message,
                    "sender": request.sender,
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "status": "success",
                    "response": response
                }
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/conversations/{conversation_id}/messages")
        async def get_conversation_messages(conversation_id: str):
            """获取对话消息"""
            try:
                messages = self.agent_manager.get_conversation_messages(conversation_id)
                return {
                    "conversation_id": conversation_id,
                    "messages": messages,
                    "count": len(messages)
                }
            except Exception as e:
                logger.error(f"Error getting messages: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.delete("/conversations/{conversation_id}")
        async def end_conversation(conversation_id: str):
            """结束对话"""
            try:
                result = self.agent_manager.end_conversation(conversation_id)
                
                # 通知WebSocket客户端
                await self.websocket_handler.broadcast_message({
                    "type": "conversation_ended",
                    "conversation_id": conversation_id
                })
                
                return result
            except Exception as e:
                logger.error(f"Error ending conversation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/conversations")
        async def list_conversations():
            """获取所有对话"""
            try:
                conversations = self.agent_manager.get_all_conversations()
                return {
                    "conversations": conversations,
                    "count": len(conversations)
                }
            except Exception as e:
                logger.error(f"Error listing conversations: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # 场景模拟API
        @self.app.post("/scenarios/simulate")
        async def simulate_scenario(request: ScenarioRequest):
            """模拟租房场景"""
            try:
                result = self.agent_manager.simulate_rental_scenario({
                    "tenant": request.tenant,
                    "landlord": request.landlord,
                    "property": request.property
                })
                
                # 通知WebSocket客户端
                await self.websocket_handler.broadcast_message({
                    "type": "scenario_started",
                    "scenario_id": result["scenario_id"],
                    "conversation_id": result["conversation_id"]
                })
                
                return {
                    "status": "success",
                    "result": result,
                    "message": "场景模拟已开始"
                }
            except Exception as e:
                logger.error(f"Error simulating scenario: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        # WebSocket端点
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket连接端点"""
            await self.websocket_handler.connect(websocket, client_id)
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # 处理来自客户端的消息
                    await self.websocket_handler.handle_client_message(
                        client_id, message, self.agent_manager
                    )
                    
            except WebSocketDisconnect:
                await self.websocket_handler.disconnect(client_id)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await self.websocket_handler.disconnect(client_id)
                
    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app
