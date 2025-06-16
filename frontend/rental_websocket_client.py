"""
WebSocket 客户端实现 - 与LangGraph流式控制器集成
提供高效的WebSocket连接管理和消息处理
"""
import asyncio
import json
import websockets
from typing import Callable, Dict, Any, List, Optional, Set
from datetime import datetime
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket客户端，支持自动重连和消息流处理"""
    
    def __init__(self, base_url: str):
        """
        初始化WebSocket客户端
        
        Args:
            base_url: WebSocket服务器基础URL，例如: "ws://localhost:8000"
        """
        self.base_url = base_url.rstrip("/")
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.active_tasks: Dict[str, List[asyncio.Task]] = {}
        self.message_callbacks: Dict[str, List[Callable]] = {}
        self.connection_callbacks: Dict[str, List[Callable]] = {}
        self.error_callbacks: Dict[str, List[Callable]] = {}
        self.lock = Lock()
        self.stopping = False
    
    def add_message_callback(self, session_id: str, callback: Callable[[Dict[str, Any]], None]):
        """添加消息回调函数"""
        with self.lock:
            if session_id not in self.message_callbacks:
                self.message_callbacks[session_id] = []
            self.message_callbacks[session_id].append(callback)
    
    def add_connection_callback(self, session_id: str, callback: Callable[[bool], None]):
        """添加连接状态回调函数"""
        with self.lock:
            if session_id not in self.connection_callbacks:
                self.connection_callbacks[session_id] = []
            self.connection_callbacks[session_id].append(callback)
    
    def add_error_callback(self, session_id: str, callback: Callable[[str], None]):
        """添加错误回调函数"""
        with self.lock:
            if session_id not in self.error_callbacks:
                self.error_callbacks[session_id] = []
            self.error_callbacks[session_id].append(callback)
    
    async def connect(self, session_id: str) -> bool:
        """连接到特定会话的WebSocket"""
        if session_id in self.connections:
            return True
        
        uri = f"{self.base_url}/ws/{session_id}"
        logger.info(f"连接到WebSocket: {uri}")
        
        try:
            # 添加连接超时设置
            websocket = await websockets.connect(
                uri, 
                ping_interval=20,
                ping_timeout=15,
                close_timeout=10
            )
            
            with self.lock:
                self.connections[session_id] = websocket
                self.active_tasks[session_id] = []
            
            # 启动消息监听和心跳任务
            listener_task = asyncio.create_task(self._listen_messages(session_id, websocket))
            heartbeat_task = asyncio.create_task(self._send_heartbeat(session_id, websocket))
            
            with self.lock:
                if session_id in self.active_tasks:
                    self.active_tasks[session_id].extend([listener_task, heartbeat_task])
            
            # 通知连接成功
            await self._notify_connection_status(session_id, True)
            return True
            
        except Exception as e:
            error_msg = f"WebSocket连接失败: {str(e)}"
            logger.error(error_msg)
            await self._notify_error(session_id, error_msg)
            await self._notify_connection_status(session_id, False)
            return False
    
    async def disconnect(self, session_id: str):
        """断开指定会话的WebSocket连接"""
        with self.lock:
            if session_id in self.active_tasks:
                for task in self.active_tasks[session_id]:
                    if not task.done():
                        task.cancel()
                self.active_tasks[session_id] = []
            
            if session_id in self.connections:
                try:
                    await self.connections[session_id].close()
                except Exception as e:
                    logger.warning(f"关闭WebSocket连接时出错: {str(e)}")
                del self.connections[session_id]
                
        await self._notify_connection_status(session_id, False)
        logger.info(f"已断开WebSocket连接: {session_id}")
    
    async def disconnect_all(self):
        """断开所有WebSocket连接"""
        self.stopping = True
        session_ids = []
        
        with self.lock:
            session_ids = list(self.connections.keys())
        
        for session_id in session_ids:
            await self.disconnect(session_id)
        
        self.stopping = False
        logger.info("已断开所有WebSocket连接")
    
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """向指定会话发送消息"""
        if session_id not in self.connections:
            logger.warning(f"无法发送消息: 会话 {session_id} 未连接")
            return False
        
        try:
            await self.connections[session_id].send(json.dumps(message))
            return True
        except Exception as e:
            error_msg = f"发送消息失败: {str(e)}"
            logger.error(error_msg)
            await self._notify_error(session_id, error_msg)
            
            # 尝试重新连接
            await self.disconnect(session_id)
            return False
    
    def is_connected(self, session_id: str) -> bool:
        """检查特定会话是否已连接"""
        return session_id in self.connections
    
    def get_active_sessions(self) -> Set[str]:
        """获取所有活跃的会话ID"""
        return set(self.connections.keys())
    
    async def _listen_messages(self, session_id: str, websocket: websockets.WebSocketClientProtocol):
        """监听特定会话的消息"""
        try:
            while not self.stopping:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # 添加元数据
                    if "timestamp" not in data:
                        data["timestamp"] = datetime.now().isoformat()
                    
                    # 调用消息回调
                    await self._notify_message(session_id, data)
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"WebSocket连接已关闭: {session_id}")
                    break
                except json.JSONDecodeError:
                    logger.warning(f"无法解析WebSocket消息: {message}")
                    continue
                
        except asyncio.CancelledError:
            logger.debug(f"消息监听任务已取消: {session_id}")
            raise
        except Exception as e:
            if not self.stopping:
                error_msg = f"WebSocket消息监听错误: {str(e)}"
                logger.error(error_msg)
                await self._notify_error(session_id, error_msg)
                
        # 如果循环退出，通知连接已断开
        if not self.stopping:
            with self.lock:
                if session_id in self.connections:
                    del self.connections[session_id]
            
            await self._notify_connection_status(session_id, False)
    
    async def _send_heartbeat(self, session_id: str, websocket: websockets.WebSocketClientProtocol):
        """定期发送心跳消息，保持连接活跃"""
        try:
            while not self.stopping:
                await asyncio.sleep(15)  # 每15秒发送一次心跳
                try:
                    if websocket.open:
                        await websocket.send(json.dumps({"type": "ping"}))
                    else:
                        logger.warning(f"WebSocket连接已关闭，停止心跳: {session_id}")
                        break
                except Exception as e:
                    logger.warning(f"发送心跳失败: {str(e)}")
                    break
                    
        except asyncio.CancelledError:
            logger.debug(f"心跳任务已取消: {session_id}")
            raise
        except Exception as e:
            if not self.stopping:
                logger.error(f"心跳任务错误: {str(e)}")
    
    async def _notify_message(self, session_id: str, data: Dict[str, Any]):
        """通知消息回调"""
        callbacks = []
        with self.lock:
            callbacks = self.message_callbacks.get(session_id, [])[:]
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"执行消息回调时出错: {str(e)}")
    
    async def _notify_connection_status(self, session_id: str, status: bool):
        """通知连接状态回调"""
        callbacks = []
        with self.lock:
            callbacks = self.connection_callbacks.get(session_id, [])[:]
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(status)
                else:
                    callback(status)
            except Exception as e:
                logger.error(f"执行连接状态回调时出错: {str(e)}")
    
    async def _notify_error(self, session_id: str, error_msg: str):
        """通知错误回调"""
        callbacks = []
        with self.lock:
            callbacks = self.error_callbacks.get(session_id, [])[:]
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error_msg)
                else:
                    callback(error_msg)
            except Exception as e:
                logger.error(f"执行错误回调时出错: {str(e)}")


class MessageManager:
    """消息管理器，用于处理和存储WebSocket消息"""
    
    def __init__(self, max_history: int = 100):
        """
        初始化消息管理器
        
        Args:
            max_history: 每个会话的最大消息历史记录数
        """
        self.messages: Dict[str, List[Dict[str, Any]]] = {}
        self.new_messages: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history = max_history
        self.lock = Lock()
    
    def add_message(self, session_id: str, message: Dict[str, Any]):
        """添加消息到指定会话"""
        with self.lock:
            # 确保会话消息列表已初始化
            if session_id not in self.messages:
                self.messages[session_id] = []
                self.new_messages[session_id] = []
            
            # 添加消息
            self.messages[session_id].append(message)
            self.new_messages[session_id].append(message)
            
            # 限制消息数量
            if len(self.messages[session_id]) > self.max_history:
                self.messages[session_id] = self.messages[session_id][-self.max_history:]
    
    def get_messages(self, session_id: str, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取指定会话的消息"""
        with self.lock:
            if session_id not in self.messages:
                return []
            
            messages = self.messages[session_id]
            if count is not None and count > 0:
                return messages[-count:]
            return messages[:]
    
    def clear_new_messages(self, session_id: str) -> int:
        """清除新消息标记并返回新消息数量"""
        with self.lock:
            if session_id not in self.new_messages:
                return 0
            
            count = len(self.new_messages[session_id])
            self.new_messages[session_id] = []
            return count
    
    def has_new_messages(self, session_id: str) -> bool:
        """检查是否有新消息"""
        with self.lock:
            return session_id in self.new_messages and len(self.new_messages[session_id]) > 0
    
    def get_new_message_count(self, session_id: str) -> int:
        """获取新消息数量"""
        with self.lock:
            if session_id not in self.new_messages:
                return 0
            return len(self.new_messages[session_id])
    
    def clear_all(self, session_id: Optional[str] = None):
        """清除所有消息"""
        with self.lock:
            if session_id:
                if session_id in self.messages:
                    self.messages[session_id] = []
                if session_id in self.new_messages:
                    self.new_messages[session_id] = []
            else:
                self.messages.clear()
                self.new_messages.clear()
