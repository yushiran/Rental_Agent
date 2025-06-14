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
            
        # 使用类变量来管理WebSocket连接和消息，避免线程问题
        self._ws_connections = {}  # 存储活跃的WebSocket连接
        self._message_buffer = {}  # 线程安全的消息缓冲区
        self._new_messages = {}    # 标记新消息
    
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
    
    def start_negotiation(self, max_tenants: int) -> Dict:
        """启动协商"""
        try:
            response = requests.post(
                f"{self.api_base_url}/start-auto-negotiation-live",
                params={"max_tenants": max_tenants},
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
                    # 确保WebSocket连接保持活跃
                    if session_id in st.session_state.live_sessions:
                        print(f"会话 {session_id} 已有WebSocket连接，保持连接")
                    else:
                        print(f"会话 {session_id} 没有WebSocket连接，准备启动")
                return session_data
            return {}
        except Exception as e:
            print(f"获取会话详情失败: {e}")
            return {}
    
    async def websocket_listener(self, session_id: str):
        """WebSocket监听器"""
        max_retries = 3
        retry_count = 0
        retry_delay = 1  # 初始重试延迟（秒）
        
        while retry_count < max_retries:
            try:
                uri = f"{self.ws_url}/ws/{session_id}"
                print(f"尝试连接WebSocket: {uri}")
                
                # 使用更健壮的连接设置
                async with websockets.connect(
                    uri,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=15
                ) as websocket:
                    print(f"WebSocket连接成功: {session_id}")
                    # 记录连接状态在类属性中，而非session_state
                    self._ws_connections[session_id] = True
                    
                    # 连接成功后重置重试计数
                    retry_count = 0
                    retry_delay = 1
                    
                    # 保持心跳，确保连接活跃
                    ping_task = asyncio.create_task(self._keep_websocket_alive(websocket))
                    
                    try:
                        while True:
                            message = await websocket.recv()
                            data = json.loads(message)
                            
                            # 使用线程安全的方式添加消息
                            self._add_message_thread_safe(session_id, data)
                            
                            # 不要在WebSocket线程中调用st.rerun()
                            # 因为它只能在主线程中使用
                            
                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"WebSocket连接关闭: {e}")
                        # 取消心跳任务
                        ping_task.cancel()
                        # 连接关闭时尝试重新连接
                        raise
                        
                    except Exception as e:
                        print(f"WebSocket消息处理错误: {e}")
                        ping_task.cancel()
                        raise
            
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.WebSocketException) as e:
                retry_count += 1
                print(f"WebSocket连接错误 (尝试 {retry_count}/{max_retries}): {e}")
                
                if retry_count < max_retries:
                    # 指数退避重试
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 10)  # 最大延迟10秒
            
            except Exception as e:
                print(f"WebSocket未预期错误: {e}")
                break
        
        print(f"WebSocket连接失败或结束: {session_id}")
        # 更新连接状态
        if session_id in self._ws_connections:
            del self._ws_connections[session_id]
    
    def _add_message_thread_safe(self, session_id, data):
        """线程安全地处理接收到的WebSocket消息"""
        try:
            if data.get("type") == "tenant_message_start" or data.get("type") == "tenant_message":
                self.thread_safe_add_message(session_id, "tenant", data.get("message", ""), data.get("sender_name", ""))
            elif data.get("type") == "landlord_response" or data.get("type") == "response_complete":
                self.thread_safe_add_message(session_id, "landlord", data.get("response", "") or data.get("full_response", ""), data.get("sender_name", ""))
            elif data.get("type") == "response_chunk":
                # 实时更新当前消息（这需要更复杂的实现，此处简化）
                pass
            elif data.get("type") == "tenant_interest_complete":
                self.thread_safe_add_message(session_id, "tenant", data.get("tenant_message", ""), "租客")
                self.thread_safe_add_message(session_id, "landlord", data.get("landlord_response", ""), "房东")
            elif data.get("type") == "error":
                self.thread_safe_add_message(session_id, "system", f"错误: {data.get('message', '')}", "系统")
            elif data.get("type") == "auto_negotiation_start":
                self.thread_safe_add_message(session_id, "system", "自动对话开始 (持续进行中...)", "系统")
            elif data.get("type") == "auto_negotiation_cancelled" or data.get("type") == "auto_negotiation_stopped":
                self.thread_safe_add_message(session_id, "system", f"自动对话已停止，总计 {data.get('completed_rounds', '?')} 轮", "系统")
            elif data.get("type") == "websocket_ready":
                self.thread_safe_add_message(session_id, "system", "✅ 实时对话连接已就绪，对话将持续进行", "系统")
            elif data.get("type") == "connection_status" or data.get("type") == "server_ping" or data.get("type") == "pong":
                # 心跳响应和连接状态，不需要处理
                print(f"收到连接状态消息: {data.get('type')}")
        except Exception as e:
            print(f"处理WebSocket消息失败: {e}")
    
    async def _keep_websocket_alive(self, websocket):
        """保持WebSocket连接活跃的心跳机制"""
        try:
            while True:
                await asyncio.sleep(15)  # 每15秒发送一次心跳
                try:
                    await websocket.send(json.dumps({"type": "ping"}))
                except Exception as e:
                    print(f"发送心跳失败: {e}")
                    break
        except asyncio.CancelledError:
            # 任务被取消
            pass
        except Exception as e:
            print(f"心跳任务错误: {e}")
    
    def add_message(self, session_id: str, sender_type: str, message: str, sender_name: str = None):
        """
        添加消息到会话 - 此方法只在主线程中调用，安全访问session_state
        """
        # 确保会话消息列表已初始化
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
        
        # 添加消息到会话状态
        message_data = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender_type": sender_type,
            "sender_name": sender_name,
            "message": message
        }
        
        st.session_state.messages[session_id].append(message_data)
        
        # 同时更新缓冲区，保持同步
        if session_id not in self._message_buffer:
            self._message_buffer[session_id] = []
            
        self._message_buffer[session_id].append(message_data)
    
    def thread_safe_add_message(self, session_id: str, sender_type: str, message: str, sender_name: str = None):
        """
        线程安全版本的添加消息方法 - 可以在后台线程中安全调用
        只更新类变量，不访问session_state
        """
        # 如果没有提供sender_name，根据sender_type生成
        if not sender_name:
            if sender_type == "tenant":
                sender_name = "租客"
            elif sender_type == "landlord":
                sender_name = "房东"
            else:
                sender_name = sender_type.title()
        
        # 创建消息数据
        message_data = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender_type": sender_type,
            "sender_name": sender_name,
            "message": message
        }
        
        # 添加到线程安全的缓冲区
        if session_id not in self._message_buffer:
            self._message_buffer[session_id] = []
            
        self._message_buffer[session_id].append(message_data)
        
        # 标记此会话有新消息
        self._new_messages[session_id] = True
    
    def start_websocket_for_session(self, session_id: str):
        """为特定会话启动WebSocket连接"""
        # 在启动WebSocket之前先获取会话详情和历史消息
        session_details = self.get_session_details(session_id)
        
        def run_websocket():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.websocket_listener(session_id))
            except Exception as e:
                print(f"WebSocket连接错误: {e}")
        
        # 使用类变量检查连接状态，而非session_state
        if session_id not in self._ws_connections:
            thread = threading.Thread(target=run_websocket, daemon=True)
            thread.start()
            
            # 记录线程到session state，这只在主线程中被修改，所以是安全的
            if "ws_threads" not in st.session_state:
                st.session_state.ws_threads = {}
            st.session_state.ws_threads[session_id] = thread
            
            # 更新UI状态，表明我们正在连接
            if "live_sessions" not in st.session_state:
                st.session_state.live_sessions = {}
            st.session_state.live_sessions[session_id] = True
    
    def cleanup_connections(self):
        """清理无效的WebSocket连接"""
        inactive_sessions = []
        
        # 检查所有连接的状态
        for session_id in list(self._ws_connections.keys()):
            try:
                # 验证连接是否仍然有效
                is_active = self._ws_connections[session_id]
                if not is_active:
                    inactive_sessions.append(session_id)
            except:
                inactive_sessions.append(session_id)
        
        # 移除无效连接
        for session_id in inactive_sessions:
            if session_id in self._ws_connections:
                del self._ws_connections[session_id]
            print(f"已清理无效连接: {session_id}")
        
        # 在UI中显示结果
        return len(inactive_sessions)
    
    def sync_messages_to_session_state(self):
        """
        将消息缓冲区的内容同步到session_state
        只在主线程中调用此方法
        """
        updated_sessions = []
        
        # 对每个有新消息的会话进行同步
        for session_id in list(self._message_buffer.keys()):
            if session_id in self._new_messages and self._new_messages[session_id]:
                # 确保session_state中有该会话的消息列表
                if session_id not in st.session_state.messages:
                    st.session_state.messages[session_id] = []
                
                # 获取缓冲区中的所有消息
                buffer_messages = self._message_buffer[session_id]
                
                # 清空session_state中的消息并添加缓冲区中的所有消息
                # 这样可以确保两者完全同步
                st.session_state.messages[session_id] = buffer_messages.copy()
                
                # 重置新消息标记
                self._new_messages[session_id] = False
                updated_sessions.append(session_id)
        
        return updated_sessions


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
    
    # 定期清理无效连接
    cleaned = demo.cleanup_connections()
    if cleaned > 0:
        st.toast(f"已清理 {cleaned} 个无效连接")
    
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
        
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            if st.button("开始协商", key="start_negotiation"):
                with st.spinner("启动中..."):
                    result = demo.start_negotiation(max_tenants)
                    if "error" in result:
                        st.error(f"启动失败: {result['error']}")
                    else:
                        st.success("启动成功！对话将持续进行")
                        st.json(result)
                        # 清空之前的消息
                        st.session_state.messages = {}
                        st.session_state.live_sessions = {}
                        st.rerun()
        
        with col2_2:
            if st.button("停止对话", key="stop_negotiation", type="primary"):
                with st.spinner("停止中..."):
                    try:
                        # 调用API终止无限对话
                        requests.post(f"{demo.api_base_url}/stop-auto-negotiation", timeout=10)
                        st.success("已停止自动对话")
                    except Exception as e:
                        st.error(f"停止失败: {str(e)}")
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
                    if not (session_id in demo._ws_connections and demo._ws_connections[session_id]):
                        if st.button(f"🔗 连接实时对话", key=f"connect_{session_id}"):
                            demo.start_websocket_for_session(session_id)
                            st.rerun()
                    else:
                        st.success("🟢 实时连接中")
                
                st.text(f"地址: {session.get('property_address', 'N/A')}")
                st.text(f"会话ID: {session_id}")
                
                # 显示对话消息
                has_messages = ((session_id in st.session_state.messages and st.session_state.messages[session_id]) or
                               (session_id in demo._message_buffer and demo._message_buffer[session_id]))
                
                if has_messages:
                    # 添加状态指示器
                    status_col1, status_col2 = st.columns([3, 1])
                    with status_col1:
                        st.markdown("**💬 实时对话 (持续进行中...):**")
                    with status_col2:
                        # 添加一个小的动态指示器，表明对话是持续的
                        if session_id in demo._ws_connections and demo._ws_connections[session_id]:
                            # 使用st.empty来避免重复刷新页面
                            status_placeholder = st.empty()
                            status_placeholder.markdown("🔄 **自动对话进行中**")
                        else:
                            st.markdown("⏸️ **等待连接...**")
                    
                    # 创建消息容器
                    message_container = st.container()
                    with message_container:
                        # 选择消息源：优先使用缓冲区，因为它可能包含最新的消息
                        messages = []
                        if session_id in demo._message_buffer:
                            messages = demo._message_buffer[session_id]
                        elif session_id in st.session_state.messages:
                            messages = st.session_state.messages[session_id]
                            
                        # 显示最近15条消息，因为是持续对话可能会有更多
                        for msg in messages[-15:]:  
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
                    message_count = 0
                    if session_id in demo._message_buffer:
                        message_count = len(demo._message_buffer[session_id])
                    elif session_id in st.session_state.messages:
                        message_count = len(st.session_state.messages[session_id])
                        
                    if message_count > 0:
                        st.markdown("---")
                        # 显示总消息数和提示此为持续对话
                        st.caption(f"共 {message_count} 条消息 | 对话将持续进行，直到手动停止")
                else:
                    st.info("暂无对话消息。点击'连接实时对话'开始监听。")
    
    else:
        st.info("暂无活跃会话。点击'开始协商'创建新会话。")
    
    # 同步消息缓冲区到session_state
    updated_sessions = demo.sync_messages_to_session_state()
    
    # 自动刷新功能
    has_active_connection = any(session_id in demo._ws_connections and demo._ws_connections[session_id] 
                               for session_id in [s.get('session_id', '') for s in sessions])
    
    # 检查是否有新消息需要刷新
    has_new_messages = any(session_id in demo._new_messages and demo._new_messages[session_id] 
                          for session_id in [s.get('session_id', '') for s in sessions])
    
    # 添加刷新状态指示器
    if has_active_connection:
        st.sidebar.success("🔄 自动刷新页面以获取最新消息")
        
        # 如果有新更新的会话，显示通知
        if updated_sessions:
            for session_id in updated_sessions:
                session_name = next((s["tenant_name"] + " ↔ " + s["landlord_name"] 
                                 for s in sessions if s.get("session_id") == session_id), "会话")
                st.toast(f"已更新 {session_name} 的新消息")
        
        # 创建一个可见的计时器，显示距离下次刷新的时间
        refresh_placeholder = st.sidebar.empty()
        for i in range(3, 0, -1):
            refresh_placeholder.text(f"将在 {i} 秒后刷新...")
            time.sleep(1)
        refresh_placeholder.text("刷新中...")
        st.rerun()


if __name__ == "__main__":
    main()
