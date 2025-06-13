from typing import Dict, Optional, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
import json
from loguru import logger

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