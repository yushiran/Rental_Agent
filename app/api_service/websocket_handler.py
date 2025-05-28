from typing import Dict, List, Any
import json
import asyncio
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class WebSocketHandler:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_subscriptions: Dict[str, List[str]] = {}  # 客户端订阅的对话ID
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = []
        
        logger.info(f"WebSocket client {client_id} connected")
        
        # 发送连接成功消息
        await self.send_personal_message({
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "message": "WebSocket连接已建立"
        }, client_id)
        
    async def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
            
        logger.info(f"WebSocket client {client_id} disconnected")
        
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                await self.disconnect(client_id)
                
    async def broadcast_message(self, message: Dict[str, Any]):
        """广播消息给所有连接的客户端"""
        if not self.active_connections:
            return
            
        # 创建断开连接的客户端列表
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
                
        # 移除断开连接的客户端
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
            
    async def send_to_conversation_subscribers(
        self, 
        conversation_id: str, 
        message: Dict[str, Any]
    ):
        """发送消息给订阅特定对话的客户端"""
        subscribers = [
            client_id for client_id, subscriptions in self.client_subscriptions.items()
            if conversation_id in subscriptions
        ]
        
        for client_id in subscribers:
            await self.send_personal_message(message, client_id)
            
    async def handle_client_message(
        self, 
        client_id: str, 
        message: Dict[str, Any],
        agent_manager
    ):
        """处理来自客户端的消息"""
        try:
            message_type = message.get("type")
            
            if message_type == "subscribe_conversation":
                # 订阅对话
                conversation_id = message.get("conversation_id")
                if conversation_id:
                    if client_id not in self.client_subscriptions:
                        self.client_subscriptions[client_id] = []
                    if conversation_id not in self.client_subscriptions[client_id]:
                        self.client_subscriptions[client_id].append(conversation_id)
                        
                    await self.send_personal_message({
                        "type": "subscription_confirmed",
                        "conversation_id": conversation_id,
                        "message": f"已订阅对话 {conversation_id}"
                    }, client_id)
                    
            elif message_type == "unsubscribe_conversation":
                # 取消订阅对话
                conversation_id = message.get("conversation_id")
                if (client_id in self.client_subscriptions and 
                    conversation_id in self.client_subscriptions[client_id]):
                    self.client_subscriptions[client_id].remove(conversation_id)
                    
                    await self.send_personal_message({
                        "type": "unsubscription_confirmed",
                        "conversation_id": conversation_id,
                        "message": f"已取消订阅对话 {conversation_id}"
                    }, client_id)
                    
            elif message_type == "send_message":
                # 发送消息到对话
                conversation_id = message.get("conversation_id")
                content = message.get("content")
                sender = message.get("sender", f"Client-{client_id}")
                
                if conversation_id and content:
                    try:
                        response = agent_manager.send_message(
                            conversation_id=conversation_id,
                            message=content,
                            sender=sender
                        )
                        
                        # 通知订阅者
                        await self.send_to_conversation_subscribers(conversation_id, {
                            "type": "message_sent",
                            "conversation_id": conversation_id,
                            "content": content,
                            "sender": sender,
                            "timestamp": datetime.now().isoformat(),
                            "response": response
                        })
                        
                    except Exception as e:
                        await self.send_personal_message({
                            "type": "error",
                            "message": f"发送消息失败: {str(e)}"
                        }, client_id)
                        
            elif message_type == "get_agent_status":
                # 获取Agent状态
                agent_name = message.get("agent_name")
                if agent_name:
                    try:
                        info = agent_manager.get_agent_info(agent_name)
                        await self.send_personal_message({
                            "type": "agent_status",
                            "agent_name": agent_name,
                            "info": info
                        }, client_id)
                    except Exception as e:
                        await self.send_personal_message({
                            "type": "error",
                            "message": f"获取Agent状态失败: {str(e)}"
                        }, client_id)
                        
            elif message_type == "list_conversations":
                # 获取对话列表
                try:
                    conversations = agent_manager.get_all_conversations()
                    await self.send_personal_message({
                        "type": "conversations_list",
                        "conversations": conversations
                    }, client_id)
                except Exception as e:
                    await self.send_personal_message({
                        "type": "error",
                        "message": f"获取对话列表失败: {str(e)}"
                    }, client_id)
                    
            elif message_type == "ping":
                # 心跳检测
                await self.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, client_id)
                
            else:
                await self.send_personal_message({
                    "type": "error",
                    "message": f"未知消息类型: {message_type}"
                }, client_id)
                
        except Exception as e:
            logger.error(f"Error handling client message from {client_id}: {e}")
            await self.send_personal_message({
                "type": "error",
                "message": f"处理消息时出错: {str(e)}"
            }, client_id)
            
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            "active_connections": len(self.active_connections),
            "clients": list(self.active_connections.keys()),
            "total_subscriptions": sum(len(subs) for subs in self.client_subscriptions.values()),
            "subscription_details": self.client_subscriptions
        }
