"""
WebSocket connection management for real-time agent communication
"""
from typing import Dict, Set, Callable, Any, Coroutine, List
import asyncio
import json
from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """Manages WebSocket connections and provides helper methods for message distribution"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.background_tasks: List[asyncio.Task] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Connect a WebSocket to a session"""
        await websocket.accept()
        async with self._lock:
            if session_id not in self.active_connections:
                self.active_connections[session_id] = set()
            self.active_connections[session_id].add(websocket)
        logger.info(f"WebSocket连接建立，会话ID: {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Disconnect a WebSocket from a session"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket连接断开，会话ID: {session_id}")
    
    async def send_message_to_session(self, session_id: str, message: dict):
        """Send a message to all WebSockets in a session"""
        if session_id in self.active_connections:
            disconnected = set()
            async with self._lock:
                connections = self.active_connections.get(session_id, set()).copy()
            
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"发送消息到WebSocket失败: {str(e)}")
                    disconnected.add(connection)
            
            # 清理断开的连接
            if disconnected:
                async with self._lock:
                    if session_id in self.active_connections:
                        for connection in disconnected:
                            self.active_connections[session_id].discard(connection)
                        if not self.active_connections[session_id]:
                            del self.active_connections[session_id]
    
    async def broadcast_to_all_sessions(self, message: dict):
        """广播消息到所有会话"""
        session_ids = []
        async with self._lock:
            session_ids = list(self.active_connections.keys())
        
        for session_id in session_ids:
            await self.send_message_to_session(session_id, message)
    
    async def stream_to_session(self, session_id: str, stream_generator, message_type="stream_chunk"):
        """
        将流式内容发送到会话
        
        Args:
            session_id: 会话ID
            stream_generator: 异步生成器，产生流式内容
            message_type: 消息类型
        """
        try:
            async for chunk in stream_generator:
                await self.send_message_to_session(session_id, {
                    "type": message_type,
                    "chunk": chunk,
                    "timestamp": "now"
                })
        except Exception as e:
            logger.error(f"流式传输到会话 {session_id} 失败: {str(e)}")
            await self.send_message_to_session(session_id, {
                "type": "stream_error",
                "error": str(e),
                "timestamp": "now"
            })
    
    def start_background_task(self, coro_func: Callable[..., Coroutine], *args, **kwargs):
        """启动一个后台任务"""
        task = asyncio.create_task(coro_func(*args, **kwargs))
        self.background_tasks.append(task)
        
        # Add task completion callback to remove it from the list
        def _on_task_done(t):
            if t in self.background_tasks:
                self.background_tasks.remove(t)
        
        task.add_done_callback(_on_task_done)
        return task
    
    def cancel_all_tasks(self):
        """取消所有后台任务"""
        for task in self.background_tasks:
            if not task.done() and not task.cancelled():
                task.cancel()
        # Don't clear the list here - let the callbacks handle it
        logger.info("已取消所有后台任务")