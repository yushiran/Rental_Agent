"""
群体Agent沟通API - 简化版租房协商系统
专注于实现租客寻找房东并协商的核心功能
"""
from contextlib import asynccontextmanager
from typing import Dict, Optional, Set
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from opik.integrations.langchain import OpikTracer
from loguru import logger
from pydantic import BaseModel

from app.conversation_service.reset_conversation import reset_conversation_state
from app.utils.opik_utils import configure

from .group_negotiation import GroupNegotiationService

configure()


# 简化的API模型
class MessageRequest(BaseModel):
    """发送消息请求"""
    message: str
    sender_type: str = "tenant"  # tenant 或 landlord


class MessageResponse(BaseModel):
    """消息响应"""
    response: str
    session_id: str
    message_count: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    """处理应用启动和关闭事件"""
    logger.info("启动群体Agent沟通API")
    yield
    logger.info("关闭群体Agent沟通API")
    opik_tracer = OpikTracer()
    opik_tracer.flush()


# 创建 FastAPI 应用
app = FastAPI(
    title="群体Agent沟通API",
    description="租客和房东之间的智能协商系统",
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

# 初始化服务
group_service = GroupNegotiationService()


# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        logger.info(f"WebSocket连接建立，会话ID: {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket连接断开，会话ID: {session_id}")
    
    async def send_message_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.add(connection)
            
            # 清理断开的连接
            for connection in disconnected:
                self.active_connections[session_id].discard(connection)
    
    async def broadcast_to_all_sessions(self, message: dict):
        """广播消息到所有会话"""
        for session_id in list(self.active_connections.keys()):
            await self.send_message_to_session(session_id, message)

# 实例化连接管理器
manager = ConnectionManager()


@app.get("/")
async def root():
    """根端点"""
    return {
        "name": "群体Agent沟通API",
        "version": "1.0.0",
        "description": "租客寻找房东并协商的智能系统",
        "features": [
            "智能租客-房东匹配",
            "实时协商对话",
            "群体协商管理",
            "WebSocket实时通信"
        ]
    }


@app.post("/start-group-negotiation")
async def start_group_negotiation(max_tenants: int = 10):
    """
    启动群体协商
    
    这个端点会：
    1. 获取数据库中的所有租客
    2. 为每个租客匹配合适的房东和房产
    3. 开始协商会话
    """
    try:
        result = await group_service.start_group_negotiation(max_tenants=max_tenants)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        logger.info(f"成功启动群体协商: {result['successful_matches']} 个匹配")
        return result
        
    except Exception as e:
        logger.error(f"启动群体协商失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/start-auto-negotiation")
async def start_auto_negotiation(max_rounds: int = 5):
    """
    启动自动协商
    
    让所有活跃的协商会话自动进行多轮对话，无需用户干预
    """
    try:
        result = await group_service.start_auto_negotiation(max_rounds=max_rounds)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        logger.info(f"成功启动自动协商: {result.get('message', '')}")
        return result
        
    except Exception as e:
        logger.error(f"启动自动协商失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/start-auto-negotiation-live")
async def start_auto_negotiation_live(max_rounds: int = 5):
    """
    启动实时自动协商
    
    让所有活跃的协商会话实时进行多轮对话，通过WebSocket推送每一条消息
    """
    try:
        result = await group_service.start_auto_negotiation_live(max_rounds=max_rounds, websocket_manager=manager)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        logger.info(f"成功启动实时自动协商: {result.get('message', '')}")
        return result
        
    except Exception as e:
        logger.error(f"启动实时自动协商失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions")
async def get_all_sessions():
    """获取所有活跃的协商会话"""
    try:
        sessions = await group_service.get_all_active_sessions()
        return {
            "total_sessions": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"获取会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取特定协商会话的详细信息"""
    try:
        session = await group_service.get_session_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return session
    except Exception as e:
        logger.error(f"获取会话 {session_id} 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/{session_id}/message", response_model=MessageResponse)
async def send_message(session_id: str, request: MessageRequest):
    """向协商会话发送消息"""
    try:
        # 获取会话信息确定发送者ID
        session = await group_service.get_session_info(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 根据发送者类型确定发送者ID
        if request.sender_type == "tenant":
            sender_id = session["tenant_id"]
        else:
            sender_id = session["landlord_id"]
        
        result = await group_service.send_message_to_session(
            session_id=session_id,
            sender_id=sender_id,
            message=request.message,
            sender_type=request.sender_type
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return MessageResponse(
            response=result["response"],
            session_id=session_id,
            message_count=result["message_count"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulate-tenant-interests")
async def simulate_all_tenant_interests():
    """模拟所有租客表达对房产的兴趣"""
    try:
        results = await group_service.simulate_all_tenant_interests()
        
        successful = sum(1 for r in results if "error" not in r["result"])
        
        return {
            "total_sessions": len(results),
            "successful_simulations": successful,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"模拟租客兴趣失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_negotiation_stats():
    """获取协商统计信息"""
    try:
        stats = group_service.get_negotiation_stats()
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_negotiation(websocket: WebSocket, session_id: str):
    """WebSocket端点，用于实时协商通信"""
    await manager.connect(websocket, session_id)
    
    try:
        # 验证会话存在
        session = await group_service.get_session_info(session_id)
        if not session:
            await websocket.send_json({"error": "协商会话不存在"})
            return
        
        # 发送会话信息
        await websocket.send_json({
            "type": "session_info",
            "session_id": session_id,
            "tenant_name": session["tenant_name"],
            "landlord_name": session["landlord_name"],
            "property_address": session["property_address"],
            "monthly_rent": session["monthly_rent"],
            "match_score": session["match_score"],
            "status": session["status"]
        })
        
        while True:
            data = await websocket.receive_json()
            
            if "message" not in data or "sender_type" not in data:
                await websocket.send_json({
                    "error": "无效的消息格式。需要字段: 'message' 和 'sender_type'"
                })
                continue
            
            try:
                # 确定发送者ID
                if data["sender_type"] == "tenant":
                    sender_id = session["tenant_id"]
                else:
                    sender_id = session["landlord_id"]
                
                # 发送消息接收确认
                await websocket.send_json({
                    "type": "message_received",
                    "from": data["sender_type"],
                    "message": data["message"]
                })
                
                # 开始响应流
                await websocket.send_json({"type": "response_start"})
                
                # 发送消息并获取响应
                result = await group_service.send_message_to_session(
                    session_id=session_id,
                    sender_id=sender_id,
                    message=data["message"],
                    sender_type=data["sender_type"]
                )
                
                if "error" in result:
                    await websocket.send_json({
                        "type": "error",
                        "error": result["error"]
                    })
                else:
                    # 发送完整响应
                    await websocket.send_json({
                        "type": "response_complete",
                        "response": result["response"],
                        "message_count": result["message_count"]
                    })
                
            except Exception as e:
                logger.error(f"WebSocket消息处理错误: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "error": str(e)
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")


@app.post("/reset-memory")
async def reset_conversation():
    """重置对话状态"""
    try:
        result = await reset_conversation_state()
        logger.info("对话内存重置成功")
        return result
    except Exception as e:
        logger.error(f"重置内存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
