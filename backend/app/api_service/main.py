"""
群体Agent沟通API - 简化版租房协商系统
专注于实现租客寻找房东并协商的核心功能
"""
from contextlib import asynccontextmanager
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from opik.integrations.langchain import OpikTracer
from loguru import logger
from pydantic import BaseModel

from app.conversation_service.reset_conversation import reset_conversation_state
from app.utils.opik_utils import configure

from .group_negotiation import GroupNegotiationService
from .websocket import ConnectionManager

configure()

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


@app.post("/start-auto-negotiation-live")
async def start_auto_negotiation_live(max_tenants: int = 10):
    """
    启动实时自动协商
    
    1. 生成指定数量的租客
    2. 为每个租客匹配房东和房产
    3. 开始实时协商，通过WebSocket推送每一条消息
    4. 无限轮次，持续对话直到手动停止
    """
    try:
        # 首先启动群体协商创建会话
        negotiation_result = await group_service.start_group_negotiation(max_tenants=max_tenants)
        
        if "error" in negotiation_result:
            raise HTTPException(status_code=400, detail=negotiation_result["error"])
        
        # 然后启动实时协商（无轮次限制）
        # 启动为异步任务，避免阻塞API响应
        manager.start_background_task(
            group_service.start_auto_negotiation_live,
            websocket_manager=manager
        )
        
        # 合并结果
        final_result = {
            "message": "成功启动实时自动协商",
            "tenants_generated": negotiation_result.get('successful_matches', 0),
            "active_sessions": len(negotiation_result.get('sessions', [])),
            "unlimited_rounds": True
        }
        
        logger.info(f"成功启动实时自动协商: {final_result}")
        return final_result
        
        logger.info(f"成功启动实时自动协商: {final_result}")
        return final_result
        
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





@app.websocket("/ws/{session_id}")
async def websocket_negotiation(websocket: WebSocket, session_id: str):
    """WebSocket端点，用于实时协商通信和流式消息推送"""
    await manager.connect(websocket, session_id)
    
    try:
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "WebSocket连接已建立"
        })
        
        # 如果是具体会话，验证会话存在并发送会话信息
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
                    "status": session["status"]
                })
        
        # 保持连接活跃，监听消息
        while True:
            try:
                # 接收客户端消息（可用于心跳检测或手动消息发送）
                data = await websocket.receive_json()
                
                # 处理心跳
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                
                # 处理其他消息类型（如果需要）
                await websocket.send_json({
                    "type": "message_received",
                    "data": data
                })
                
            except Exception as e:
                logger.debug(f"WebSocket消息处理: {str(e)}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket断开连接: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")
    finally:
        manager.disconnect(websocket, session_id)


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


@app.post("/stop-auto-negotiation")
async def stop_auto_negotiation():
    """
    停止自动协商
    
    取消当前运行的自动协商任务
    """
    try:
        # 通过WebSocket广播停止消息
        await manager.broadcast_to_all_sessions({
            "type": "auto_negotiation_stopped",
            "message": "自动协商已停止",
            "timestamp": datetime.now().isoformat()
        })
        
        # 取消任务在WebSocket连接管理器中处理
        manager.cancel_all_tasks()
        
        return {"message": "自动协商已停止"}
    except Exception as e:
        logger.error(f"停止自动协商失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
