"""
群体Agent沟通API - 简化版租房协商系统
专注于实现租客寻找房东并协商的核心功能
"""
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
import json
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

from .group_negotiation import GroupNegotiationService
from .websocket import ConnectionManager
from app.agents.agents_factory import AgentDataInitializer

configure()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """处理应用启动和关闭事件"""
    logger.info("启动群体Agent沟通API")

    # 初始化数据库
    await initialize_database()
    # await start_auto_negotiation_live(max_tenants=3)

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

# 实例化连接管理器
manager = ConnectionManager()
# 初始化Agent工厂
agent_factory = AgentDataInitializer()
# 初始化服务（传入WebSocket管理器）
group_service = GroupNegotiationService(websocket_manager=manager)

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
            "WebSocket实时通信",
            "LangGraph流式Agent控制器"
        ]
    }

@app.get("/config")
async def get_config():
    """
    获取前端需要的配置信息
    
    Returns:
        dict: 包含Google Maps API密钥等配置信息
    """
    try:
        if not config.google_maps or not config.google_maps.api_key:
            raise HTTPException(status_code=500, detail="Google Maps API密钥未配置")
        
        return {
            "google_maps_api_key": config.google_maps.api_key
        }
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

class InitializeRequest(BaseModel):
    tenant_count: int = 3
    reset_data: bool = False

@app.post("/initialize")
async def initialize_system(request: InitializeRequest):
    """
    初始化系统 - 生成租客和地图数据
    
    Args:
        tenant_count: 要生成的租客数量
        reset_data: 是否重置现有数据
    
    Returns:
        - tenants: 生成的租客列表
        - properties: 房产数据（用于地图显示）
        - landlords: 房东数据
        - map_data: 地图可视化数据
    """
    try:
        logger.info(f"开始初始化系统: 租客数量={request.tenant_count}, 重置数据={request.reset_data}")
        
        # 如果需要重置数据，先清理现有数据
        if request.reset_data:
            await agent_factory.clear_all_data()
            logger.info("已清理现有数据")
        
        # 检查是否已有数据
        existing_properties = await agent_factory.get_properties_count()
        existing_landlords = await agent_factory.get_landlords_count()
        
        # 如果没有房产和房东数据，先初始化基础数据
        if existing_properties == 0 or existing_landlords == 0:
            logger.info("初始化房产和房东数据...")
            await agent_factory.initialize_properties_and_landlords()
        
        # 生成指定数量的租客
        logger.info(f"生成 {request.tenant_count} 个租客...")
        tenants = await agent_factory.generate_tenants(request.tenant_count)
        
        # 获取所有房产数据用于地图展示
        properties = await agent_factory.get_all_properties()
        landlords = await agent_factory.get_all_landlords()
        
        # 准备地图数据
        map_data = []
        for prop in properties:
            # 安全地获取月租金
            try:
                # 如果有price字段，手动计算月租金
                price_info = prop.get("price", {})
                if isinstance(price_info, dict) and price_info:
                    amount = price_info.get("amount", 0)
                    frequency = price_info.get("frequency", "monthly")
                    
                    if frequency == 'weekly':
                        monthly_rent = amount * 52 / 12
                    elif frequency == 'yearly':
                        monthly_rent = amount / 12
                    else:
                        monthly_rent = amount
                else:
                    # 如果没有price字段，使用默认值
                    monthly_rent = 2000
            except Exception as e:
                logger.warning(f"计算房产 {prop.get('property_id', 'unknown')} 的月租金时出错: {e}")
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
            "message": "系统初始化成功",
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
        
        logger.info(f"系统初始化完成: {len(tenants)}个租客, {len(properties)}个房产, {len(landlords)}个房东")
        return result
        
    except Exception as e:
        logger.error(f"系统初始化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"初始化失败: {str(e)}")

@app.post("/start-session")
async def start_session(max_tenants: int = Query(1, description="最大租客数量")):
    """启动会话 - 前端兼容接口"""
    return await start_auto_negotiation_live(max_tenants)

class StartNegotiationRequest(BaseModel):
    tenant_ids: List[str] = []
    
@app.post("/start-negotiation")
async def start_negotiation(request: StartNegotiationRequest):
    """
    开始协商流程 - 基于已生成的租客启动协商
    
    Args:
        tenant_ids: 要参与协商的租客ID列表，如果为空则使用所有租客
    
    Returns:
        - 创建的协商会话信息
        - WebSocket连接信息
    """
    try:
        logger.info(f"开始协商流程，租客IDs: {request.tenant_ids}")
        
        # 如果没有指定租客ID，获取所有租客的前几个
        if not request.tenant_ids:
            all_tenants = await agent_factory.get_all_tenants()
            if not all_tenants:
                raise HTTPException(status_code=400, detail="没有可用的租客数据，请先调用初始化API")
            # 默认取前3个租客
            request.tenant_ids = [tenant["tenant_id"] for tenant in all_tenants[:3]]
        
        # 验证租客ID是否存在
        existing_tenants = []
        for tenant_id in request.tenant_ids:
            tenant_data = await group_service._get_tenant_by_id(tenant_id)
            if tenant_data:
                existing_tenants.append(tenant_data)
            else:
                logger.warning(f"租客 {tenant_id} 不存在，跳过")
        
        if not existing_tenants:
            raise HTTPException(status_code=400, detail="没有找到有效的租客")
        
        # 开始群体协商
        negotiation_result = await group_service.start_group_negotiation_with_tenants(existing_tenants)
        
        if "error" in negotiation_result:
            raise HTTPException(status_code=400, detail=negotiation_result["error"])
        
        # 为每个会话发送初始化消息到WebSocket
        for session in negotiation_result.get('sessions', []):
            session_id = session['session_id']
            await manager.send_message_to_session(session_id, {
                "type": "negotiation_started",
                "session_id": session_id,
                "message": "协商已开始，租客正在寻找房东...",
                "session_info": session,
                "timestamp": datetime.now().isoformat()
            })
        
        result = {
            "message": "协商流程启动成功",
            "total_sessions": len(negotiation_result.get('sessions', [])),
            "sessions": negotiation_result.get('sessions', []),
            "websocket_info": {
                "endpoint": "/ws/{session_id}",
                "description": "连接到WebSocket以接收实时协商消息"
            }
        }
        
        logger.info(f"协商流程启动成功: {len(result['sessions'])} 个会话")
        return result
        
    except Exception as e:
        logger.error(f"启动协商流程失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动协商失败: {str(e)}")

@app.post("/start-auto-negotiation-live") 
async def start_auto_negotiation_live(max_tenants: int = Query(1, description="最大租客数量")):
    """
    启动租客主导的实时自动协商（保持向后兼容）
    """
    try:
        # 获取前N个租客
        all_tenants = await agent_factory.get_all_tenants()
        if not all_tenants:
            raise HTTPException(status_code=400, detail="没有可用的租客数据，请先调用初始化API")
        
        tenant_ids = [tenant["tenant_id"] for tenant in all_tenants[:max_tenants]]
        
        # 调用新的协商API
        request = StartNegotiationRequest(tenant_ids=tenant_ids)
        result = await start_negotiation(request)
        
        # 返回向后兼容的格式
        return {
            "message": "成功启动租客主导的实时自动协商",
            "active_sessions": result["total_sessions"],
            "session_ids": [s["session_id"] for s in result["sessions"]]
        }
        
    except Exception as e:
        logger.error(f"启动实时自动协商失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/sessions")
async def get_all_sessions():
    """获取所有协商会话"""
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
        
        # 特别处理：检查是否存在WebSocket连接，如果存在则告知前端保持连接
        has_websocket = session_id in manager.active_connections
        
        # 返回会话信息和WebSocket连接状态
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
        logger.error(f"获取会话 {session_id} 失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """获取协商系统统计数据"""
    try:
        stats = group_service.get_negotiation_stats()
        return stats
    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
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
            "message": "WebSocket连接已建立",
            "timestamp": datetime.now().isoformat()
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
                    "status": session["status"],
                    "timestamp": datetime.now().isoformat()
                })
                
                # 额外发送一条确认消息，确保前端知道WebSocket连接正常工作
                await websocket.send_json({
                    "type": "websocket_ready",
                    "message": "实时对话准备就绪，对话将持续进行",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发送会话的历史消息
                if session.get("messages"):
                    await websocket.send_json({
                        "type": "history",
                        "messages": session["messages"],
                        "timestamp": datetime.now().isoformat()
                    })
        
        # 保持连接活跃，监听消息
        ping_counter = 0
        while True:
            try:
                # 使用较短的超时以便能够定期发送心跳
                data = await asyncio.wait_for(websocket.receive_json(), timeout=15)
                
                # 处理心跳
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong", 
                        "timestamp": datetime.now().isoformat()
                    })
                    ping_counter += 1
                    # 每隔5次心跳，发送一次会话状态更新
                    if ping_counter % 5 == 0:
                        await websocket.send_json({
                            "type": "connection_status",
                            "status": "active",
                            "session_id": session_id,
                            "timestamp": datetime.now().isoformat()
                        })
                    continue
                
                # 处理其他消息类型
                await websocket.send_json({
                    "type": "message_received",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                })
                
            except asyncio.TimeoutError:
                # 超时时发送主动心跳，保持连接
                try:
                    await websocket.send_json({
                        "type": "server_ping", 
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.debug(f"发送心跳失败，可能连接已断开: {str(e)}")
                    break
            
            except Exception as e:
                if isinstance(e, WebSocketDisconnect):
                    logger.debug(f"WebSocket客户端断开连接: {str(e)}")
                else:
                    logger.debug(f"WebSocket消息处理错误: {str(e)}")
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
