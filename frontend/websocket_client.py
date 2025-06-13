"""
简化版WebSocket客户端
提供高效的WebSocket连接管理和消息处理
"""
import asyncio
import json
import websockets
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WebSocketClient:
    """简化版WebSocket客户端"""
    
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.message_callbacks: List[Callable] = []
        self.connection_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
    def add_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """添加消息回调函数"""
        self.message_callbacks.append(callback)
    
    def add_connection_callback(self, callback: Callable[[bool], None]):
        """添加连接状态回调函数"""
        self.connection_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[str], None]):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)
    
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            # 添加连接超时设置
            self.websocket = await websockets.connect(
                self.uri, 
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            self.is_connected = True
            
            # 通知连接成功
            for callback in self.connection_callbacks:
                callback(True)
            
            logger.info(f"WebSocket连接成功: {self.uri}")
            
            # 开始监听消息
            await self._listen_messages()
            
        except websockets.exceptions.InvalidURI as e:
            self.is_connected = False
            error_msg = f"WebSocket URI无效: {str(e)}"
            logger.error(error_msg)
            
            for callback in self.connection_callbacks:
                callback(False)
            for callback in self.error_callbacks:
                callback(error_msg)
                
        except asyncio.TimeoutError as e:
            self.is_connected = False
            error_msg = f"WebSocket连接超时: {str(e)}"
            logger.error(error_msg)
            
            for callback in self.connection_callbacks:
                callback(False)
            for callback in self.error_callbacks:
                callback(error_msg)
                
        except Exception as e:
            self.is_connected = False
            error_msg = f"WebSocket连接失败: {str(e)}"
            logger.error(error_msg)
            
            # 通知连接失败
            for callback in self.connection_callbacks:
                callback(False)
            for callback in self.error_callbacks:
                callback(error_msg)
    
    async def _listen_messages(self):
        """监听WebSocket消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # 添加时间戳
                    data["_timestamp"] = datetime.now().isoformat()
                    
                    # 调用所有消息回调
                    for callback in self.message_callbacks:
                        callback(data)
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析失败: {str(e)}")
                    continue
                    
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            logger.info("WebSocket连接已关闭")
            
            # 通知连接断开
            for callback in self.connection_callbacks:
                callback(False)
                
        except Exception as e:
            self.is_connected = False
            error_msg = f"WebSocket消息监听错误: {str(e)}"
            logger.error(error_msg)
            
            # 通知错误
            for callback in self.error_callbacks:
                callback(error_msg)
    
    async def send_message(self, message: Dict[str, Any]):
        """发送消息到WebSocket服务器"""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.send(json.dumps(message))
                logger.debug(f"发送消息: {message}")
            except Exception as e:
                error_msg = f"发送消息失败: {str(e)}"
                logger.error(error_msg)
                for callback in self.error_callbacks:
                    callback(error_msg)
    
    async def send_ping(self):
        """发送心跳消息"""
        await self.send_message({"type": "ping"})
    
    async def disconnect(self):
        """断开WebSocket连接"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket连接已断开")


class MessageBuffer:
    """消息缓冲器，用于管理和过滤消息"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.messages: List[Dict[str, Any]] = []
        self.session_messages: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_message(self, message: Dict[str, Any]):
        """添加消息到缓冲器"""
        # 添加到全局消息列表
        self.messages.append(message)
        
        # 按会话分类
        session_id = message.get("session_id")
        if session_id and session_id != "global":
            if session_id not in self.session_messages:
                self.session_messages[session_id] = []
            self.session_messages[session_id].append(message)
        
        # 限制缓冲区大小
        if len(self.messages) > self.max_size:
            # 保留最新的80%消息
            keep_count = int(self.max_size * 0.8)
            self.messages = self.messages[-keep_count:]
    
    def get_messages(self, session_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取消息"""
        if session_id:
            messages = self.session_messages.get(session_id, [])
        else:
            messages = self.messages
        
        if limit:
            return messages[-limit:]
        return messages
    
    def clear(self, session_id: Optional[str] = None):
        """清除消息"""
        if session_id:
            self.session_messages.pop(session_id, None)
        else:
            self.messages.clear()
            self.session_messages.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "total_messages": len(self.messages),
            "session_count": len(self.session_messages),
            "avg_messages_per_session": len(self.messages) // max(len(self.session_messages), 1)
        }
