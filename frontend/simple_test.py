"""
极简版租房协商演示 - 仅基本功能
"""
import streamlit as st
import requests
import time
import json
import asyncio
import websockets
from typing import Dict, List
import threading
from datetime import datetime


class SimpleDemo:
    """极简演示类"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000"
        
        # 初始化会话状态
        if "messages" not in st.session_state:
            st.session_state.messages = {}
        if "ws_connected" not in st.session_state:
            st.session_state.ws_connected = False
        if "live_sessions" not in st.session_state:
            st.session_state.live_sessions = {}
    
    def check_connection(self) -> bool:
        """检查API连接"""
        try:
            response = requests.get(f"{self.api_base_url}/", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def reset_memory(self) -> Dict:
        """重置内存"""
        try:
            response = requests.post(f"{self.api_base_url}/reset-memory", timeout=10)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def start_negotiation(self, max_tenants: int, max_rounds: int) -> Dict:
        """启动协商"""
        try:
            response = requests.post(
                f"{self.api_base_url}/start-auto-negotiation-live",
                params={"max_tenants": max_tenants, "max_rounds": max_rounds},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_sessions(self) -> List[Dict]:
        """获取会话列表"""
        try:
            response = requests.get(f"{self.api_base_url}/sessions", timeout=10)
            if response.status_code == 200:
                return response.json().get("sessions", [])
            return []
        except:
            return []
    
    def get_session_details(self, session_id: str) -> Dict:
        """获取特定会话详情"""
        try:
            response = requests.get(f"{self.api_base_url}/sessions/{session_id}", timeout=10)
            if response.status_code == 200:
                session_data = response.json()
                # 如果session_state中没有该会话的消息，则从API获取历史消息
                if session_id not in st.session_state.messages and "messages" in session_data:
                    st.session_state.messages[session_id] = []
                    for msg in session_data.get("messages", []):
                        self.add_message(
                            session_id,
                            msg.get("sender_type", "unknown"),
                            msg.get("message", ""),
                            msg.get("sender_name", f"{msg.get('sender_type', 'unknown').title()}")
                        )
                return session_data
            return {}
        except Exception as e:
            print(f"获取会话详情失败: {e}")
            return {}
    
    async def websocket_listener(self, session_id: str):
        """WebSocket监听器"""
        try:
            uri = f"{self.ws_url}/ws/{session_id}"
            async with websockets.connect(uri) as websocket:
                st.session_state.ws_connected = True
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # 处理不同类型的消息
                        if data.get("type") == "tenant_message_start":
                            self.add_message(session_id, "tenant", data.get("message", ""), data.get("sender_name", ""))
                        elif data.get("type") == "landlord_response":
                            self.add_message(session_id, "landlord", data.get("response", ""), data.get("sender_name", ""))
                        elif data.get("type") == "tenant_interest_complete":
                            self.add_message(session_id, "tenant", data.get("tenant_message", ""), "租客")
                            self.add_message(session_id, "landlord", data.get("landlord_response", ""), "房东")
                        elif data.get("type") == "error":
                            self.add_message(session_id, "system", f"错误: {data.get('message', '')}", "系统")
                        
                        # 强制刷新页面以显示新消息
                        st.rerun()
                        
                    except websockets.exceptions.ConnectionClosed:
                        break
                    except Exception as e:
                        print(f"WebSocket消息处理错误: {e}")
                        break
        except Exception as e:
            print(f"WebSocket连接错误: {e}")
        finally:
            st.session_state.ws_connected = False
    
    def add_message(self, session_id: str, sender_type: str, message: str, sender_name: str = None):
        """添加消息到会话"""
        if session_id not in st.session_state.messages:
            st.session_state.messages[session_id] = []
        
        # 如果没有提供sender_name，根据sender_type生成
        if not sender_name:
            if sender_type == "tenant":
                sender_name = "租客"
            elif sender_type == "landlord":
                sender_name = "房东"
            else:
                sender_name = sender_type.title()
        
        st.session_state.messages[session_id].append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender_type": sender_type,
            "sender_name": sender_name,
            "message": message
        })
    
    def start_websocket_for_session(self, session_id: str):
        """为特定会话启动WebSocket连接"""
        # 在启动WebSocket之前先获取会话详情和历史消息
        session_details = self.get_session_details(session_id)
        
        def run_websocket():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.websocket_listener(session_id))
        
        if session_id not in st.session_state.live_sessions:
            thread = threading.Thread(target=run_websocket, daemon=True)
            thread.start()
            st.session_state.live_sessions[session_id] = thread


def main():
    """主函数"""
    st.set_page_config(
        page_title="极简租房协商演示",
        page_icon="🏠",
        layout="wide"
    )
    
    st.title("🏠 极简租房协商演示")
    st.markdown("---")
    
    # 初始化
    if "demo" not in st.session_state:
        st.session_state.demo = SimpleDemo()
    
    demo = st.session_state.demo
    
    # 检查连接
    if not demo.check_connection():
        st.error("❌ 无法连接到后端API")
        st.info("请确保后端服务运行在 http://localhost:8000")
        st.code("cd backend && python -m app.api_service.main")
        return
    
    st.success("✅ 后端API连接正常")
    
    # 控制面板
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🔄 重置")
        if st.button("重置内存"):
            with st.spinner("重置中..."):
                result = demo.reset_memory()
                if "error" in result:
                    st.error(f"重置失败: {result['error']}")
                else:
                    st.success("重置成功")
    
    with col2:
        st.subheader("🚀 启动协商")
        max_tenants = st.number_input("租客数量", 1, 20, 5)
        max_rounds = st.number_input("对话轮数", 1, 10, 3)
        
        if st.button("开始协商"):
            with st.spinner("启动中..."):
                result = demo.start_negotiation(max_tenants, max_rounds)
                if "error" in result:
                    st.error(f"启动失败: {result['error']}")
                else:
                    st.success("启动成功")
                    st.json(result)
                    # 清空之前的消息
                    st.session_state.messages = {}
                    st.session_state.live_sessions = {}
                    st.rerun()
    
    with col3:
        st.subheader("📊 会话状态")
        if st.button("刷新会话"):
            st.rerun()
        
        sessions = demo.get_sessions()
        st.metric("活跃会话", len(sessions))
    
    # 会话列表
    st.markdown("---")
    st.subheader("📋 会话列表")
    
    sessions = demo.get_sessions()
    if sessions:
        for i, session in enumerate(sessions):
            session_id = session.get('session_id', f'session_{i}')
            
            with st.expander(f"会话 {i+1}: {session.get('tenant_name', 'N/A')} ↔ {session.get('landlord_name', 'N/A')}", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("租金", f"£{session.get('monthly_rent', 0):,.0f}")
                with col2:
                    st.metric("匹配分数", f"{session.get('match_score', 0):.1f}")
                with col3:
                    st.metric("状态", session.get('status', 'N/A'))
                with col4:
                    # WebSocket连接控制
                    if session_id not in st.session_state.live_sessions:
                        if st.button(f"🔗 连接实时对话", key=f"connect_{session_id}"):
                            demo.start_websocket_for_session(session_id)
                            st.rerun()
                    else:
                        st.success("🟢 实时连接中")
                
                st.text(f"地址: {session.get('property_address', 'N/A')}")
                st.text(f"会话ID: {session_id}")
                
                # 显示对话消息
                if session_id in st.session_state.messages and st.session_state.messages[session_id]:
                    st.markdown("**💬 实时对话:**")
                    
                    # 创建消息容器
                    message_container = st.container()
                    with message_container:
                        for msg in st.session_state.messages[session_id][-10:]:  # 只显示最近10条消息
                            timestamp = msg["timestamp"]
                            sender_name = msg["sender_name"]
                            message = msg["message"]
                            sender_type = msg["sender_type"]
                            
                            if sender_type == "tenant":
                                st.chat_message("user").write(f"**{sender_name}** ({timestamp}): {message}")
                            elif sender_type == "landlord":
                                st.chat_message("assistant").write(f"**{sender_name}** ({timestamp}): {message}")
                            else:
                                st.info(f"**{sender_name}** ({timestamp}): {message}")
                    
                    # 自动滚动到最新消息
                    if len(st.session_state.messages[session_id]) > 0:
                        st.markdown("---")
                        st.caption(f"共 {len(st.session_state.messages[session_id])} 条消息")
                else:
                    st.info("暂无对话消息。点击'连接实时对话'开始监听。")
    
    else:
        st.info("暂无活跃会话。点击'开始协商'创建新会话。")
    
    # 自动刷新功能
    if sessions and any(session_id in st.session_state.live_sessions for session_id in [s.get('session_id', '') for s in sessions]):
        time.sleep(2)  # 每2秒刷新一次
        st.rerun()


if __name__ == "__main__":
    main()
