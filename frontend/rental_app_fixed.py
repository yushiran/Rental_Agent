"""
租房协商前端应用 - 优化版
集成LangGraph流式输出，提供更高效的实时对话体验
修复了线程安全和Streamlit会话状态访问问题
"""
import streamlit as st
import requests
import time
import json
import asyncio
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime

from rental_websocket_client import WebSocketClient, MessageManager


class RentalApp:
    """租房协商应用类"""
    
    # 类变量定义（对所有实例共享）
    _ws_client = None
    _message_manager = None
    _event_loop = None
    _background_task = None
    
    def __init__(self):
        """初始化租房协商应用"""
        self.api_base_url = "http://localhost:8000"
        self.ws_base_url = "ws://localhost:8000"
        
        # 初始化WebSocket客户端和消息管理器
        # 由于这些需要通过线程共享，所以我们把它们存储在类变量中
        if RentalApp._message_manager is None:
            RentalApp._message_manager = MessageManager(max_history=100)
        
        # 初始化应用状态
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """初始化Session State变量"""
        if "sessions" not in st.session_state:
            st.session_state.sessions = []
        if "active_session_id" not in st.session_state:
            st.session_state.active_session_id = None
        if "auto_refresh" not in st.session_state:
            st.session_state.auto_refresh = True
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = time.time()
    
    def check_api_connection(self) -> bool:
        """检查API连接状态"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def create_rental_session(self, tenant_name: str, landlord_name: str, 
                           property_address: str, monthly_rent: float) -> Dict[str, Any]:
        """创建新的租房协商会话"""
        try:
            response = requests.post(
                f"{self.api_base_url}/sessions",
                json={
                    "tenant_name": tenant_name,
                    "landlord_name": landlord_name,
                    "property_address": property_address,
                    "monthly_rent": monthly_rent
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"状态码: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def update_sessions(self) -> List[Dict[str, Any]]:
        """更新会话列表"""
        try:
            response = requests.get(f"{self.api_base_url}/sessions", timeout=10)
            if response.status_code == 200:
                sessions = response.json().get("sessions", [])
                st.session_state.sessions = sessions
                return sessions
            return []
        except:
            return []
    
    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """获取特定会话的详情"""
        try:
            response = requests.get(f"{self.api_base_url}/sessions/{session_id}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}
    
    def send_message(self, session_id: str, message: str, sender_type: str = "tenant") -> Dict[str, Any]:
        """发送消息到指定会话"""
        try:
            response = requests.post(
                f"{self.api_base_url}/sessions/{session_id}/send-message",
                json={"message": message, "sender_type": sender_type},
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"状态码: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _setup_websocket(self):
        """设置WebSocket连接"""
        # 创建WebSocket客户端
        RentalApp._ws_client = WebSocketClient(self.ws_base_url)
        
        # 连接到全局通知通道
        await RentalApp._ws_client.connect("global")
        
        # 添加消息回调
        RentalApp._ws_client.add_message_callback("global", self._on_global_message)
    
    async def _connect_to_session(self, session_id: str):
        """连接到指定会话"""
        if not RentalApp._ws_client:
            return
        
        # 添加会话特定回调
        RentalApp._ws_client.add_message_callback(session_id, self._on_session_message)
        RentalApp._ws_client.add_connection_callback(session_id, 
                                                   lambda status: self._on_connection_status(session_id, status))
        RentalApp._ws_client.add_error_callback(session_id,
                                              lambda error: self._on_error(session_id, error))
        
        # 连接到会话
        await RentalApp._ws_client.connect(session_id)
    
    def _on_global_message(self, data: Dict[str, Any]):
        """处理全局消息"""
        msg_type = data.get("type", "")
        
        if msg_type == "auto_negotiation_start":
            # 自动协商开始通知，可能需要更新UI
            pass
        
        elif msg_type == "auto_negotiation_stopped" or msg_type == "auto_negotiation_cancelled":
            # 自动协商停止
            # 不要在后台线程访问 st.session_state
            # 保存消息到内部状态，UI线程会在下次重新渲染时处理
            message = f"自动协商已停止，共完成 {data.get('completed_rounds', '未知')} 轮对话"
            # 添加系统消息到活跃会话
            if RentalApp._ws_client:
                for session_id in RentalApp._ws_client.get_active_sessions():
                    if session_id != "global":
                        self._add_system_message(session_id, message)
        
        elif msg_type == "auto_negotiation_error":
            # 自动协商错误
            error = data.get("error", "未知错误")
            # 添加系统消息到活跃会话
            if RentalApp._ws_client:
                for session_id in RentalApp._ws_client.get_active_sessions():
                    if session_id != "global":
                        self._add_system_message(session_id, f"错误: {error}")
    
    def _on_session_message(self, data: Dict[str, Any]):
        """处理会话特定消息"""
        session_id = data.get("session_id", "")
        if not session_id:
            # 尝试从当前WebSocket连接获取会话ID
            for s_id in RentalApp._ws_client.get_active_sessions():
                if s_id != "global":
                    session_id = s_id
                    break
        
        msg_type = data.get("type", "")
        
        if msg_type == "tenant_message" or msg_type == "tenant_message_start":
            # 租客消息
            sender_name = data.get("sender_name", "租客")
            message = data.get("message", "")
            self._add_message(session_id, "tenant", message, sender_name)
        
        elif msg_type == "response_chunk":
            # 响应块 - 流式输出
            sender = data.get("sender", "")
            sender_name = data.get("sender_name", sender.title())
            chunk = data.get("chunk", "")
            
            # 在消息管理器中查找最后一条来自该发送者的消息
            messages = RentalApp._message_manager.get_messages(session_id)
            last_sender_msg = None
            for msg in reversed(messages):
                if msg.get("sender_type") == sender:
                    last_sender_msg = msg
                    break
            
            if last_sender_msg and last_sender_msg.get("is_streaming", False):
                # 更新现有的流式消息
                last_sender_msg["message"] += chunk
            else:
                # 创建新的流式消息
                self._add_message(session_id, sender, chunk, sender_name, is_streaming=True)
        
        elif msg_type == "response":
            # 完整响应 - 非流式
            sender = data.get("sender", "")
            sender_name = data.get("sender_name", sender.title())
            message = data.get("message", "")
            
            # 查找是否有流式消息需要替换
            messages = RentalApp._message_manager.get_messages(session_id)
            last_sender_msg = None
            for msg in reversed(messages):
                if msg.get("sender_type") == sender and msg.get("is_streaming", False):
                    last_sender_msg = msg
                    break
            
            if last_sender_msg:
                # 替换流式消息为完整消息
                last_sender_msg["message"] = message
                last_sender_msg["is_streaming"] = False
            else:
                # 添加新消息
                self._add_message(session_id, sender, message, sender_name)
        
        elif msg_type == "landlord_message" or msg_type == "landlord_message_start":
            # 房东消息
            sender_name = data.get("sender_name", "房东")
            message = data.get("message", "")
            self._add_message(session_id, "landlord", message, sender_name)
        
        elif msg_type == "system_message":
            # 系统消息
            message = data.get("message", "")
            self._add_system_message(session_id, message)
    
    def _on_connection_status(self, session_id: str, status: bool):
        """处理连接状态变化"""
        # 不要在后台线程中直接修改st.session_state
        # 而是将连接状态存储在后台线程可以访问的数据结构中
        # 界面渲染时会从MessageManager获取最新消息
        
        if status:
            message = "🟢 已连接到实时对话服务"
        else:
            message = "🔴 已断开与实时对话服务的连接"
        
        self._add_system_message(session_id, message)
    
    def _on_error(self, session_id: str, error: str):
        """处理错误消息"""
        self._add_system_message(session_id, f"❌ 错误: {error}")
    
    def _add_message(self, session_id: str, sender_type: str, message: str, sender_name: str = None, is_streaming: bool = False):
        """添加消息到消息管理器"""
        if not sender_name:
            if sender_type == "tenant":
                sender_name = "租客"
            elif sender_type == "landlord":
                sender_name = "房东"
            else:
                sender_name = sender_type.title()
        
        message_data = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "sender_type": sender_type,
            "sender_name": sender_name,
            "message": message,
            "is_streaming": is_streaming
        }
        
        RentalApp._message_manager.add_message(session_id, message_data)
    
    def _add_system_message(self, session_id: str, message: str):
        """添加系统消息"""
        self._add_message(session_id, "system", message, "系统")
    
    def is_connected(self, session_id: str) -> bool:
        """检查会话是否已连接"""
        # 不使用st.session_state.connection_status，而是从WebSocket客户端获取状态
        if not RentalApp._ws_client:
            return False
            
        # 检查是否在活跃连接中
        return session_id in RentalApp._ws_client.get_active_sessions()
    
    def ensure_websocket_running(self):
        """确保WebSocket客户端运行中"""
        if RentalApp._background_task is None or not RentalApp._background_task.is_alive():
            # 初始化事件循环并启动WebSocket后台任务
            def run_async_loop():
                RentalApp._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(RentalApp._event_loop)
                RentalApp._event_loop.run_until_complete(self._setup_websocket())
                RentalApp._event_loop.run_forever()
            
            # 创建并启动后台线程
            RentalApp._background_task = threading.Thread(target=run_async_loop, daemon=True)
            RentalApp._background_task.start()
    
    def connect_to_session(self, session_id: str):
        """连接到会话WebSocket"""
        if not RentalApp._event_loop:
            self.ensure_websocket_running()
            time.sleep(0.5)  # 等待WebSocket客户端初始化
        
        if RentalApp._event_loop and RentalApp._ws_client:
            future = asyncio.run_coroutine_threadsafe(
                self._connect_to_session(session_id), 
                RentalApp._event_loop
            )
            try:
                # 等待连接完成，但设置超时
                future.result(timeout=5)
            except Exception as e:
                print(f"连接到会话 {session_id} 时出错: {str(e)}")
    
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取指定会话的消息"""
        return RentalApp._message_manager.get_messages(session_id)
    
    def clear_new_messages(self, session_id: str) -> int:
        """清除新消息标记并返回数量"""
        return RentalApp._message_manager.clear_new_messages(session_id)
    
    def has_new_messages(self, session_id: str) -> bool:
        """检查是否有新消息"""
        return RentalApp._message_manager.has_new_messages(session_id)
    
    def get_new_message_count(self, session_id: str) -> int:
        """获取新消息数量"""
        return RentalApp._message_manager.get_new_message_count(session_id)


def main():
    """主函数"""
    st.set_page_config(
        page_title="LangGraph租房协商演示",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🏠 LangGraph 租房协商助手")
    
    # 创建或获取已有的应用实例
    if "rental_app" not in st.session_state:
        st.session_state.rental_app = RentalApp()
    
    rental_app = st.session_state.rental_app
    
    # 确保WebSocket客户端运行中
    rental_app.ensure_websocket_running()
    
    # 检查API连接状态
    if not rental_app.check_api_connection():
        st.error("⚠️ 无法连接到后端服务，请确保服务器已启动。")
        st.stop()
    
    # 侧边栏管理
    with st.sidebar:
        st.header("创建新会话")
        with st.form("create_session"):
            tenant_name = st.text_input("租客名称", "Alex")
            landlord_name = st.text_input("房东名称", "Sarah")
            property_address = st.text_input("房产地址", "123 Main St, London")
            monthly_rent = st.number_input("月租金 (£)", 600, 5000, 1200)
            
            submit = st.form_submit_button("创建会话")
            if submit:
                result = rental_app.create_rental_session(
                    tenant_name, landlord_name, property_address, monthly_rent
                )
                if "error" in result:
                    st.error(f"创建会话失败: {result['error']}")
                else:
                    st.success(f"已创建会话: {result.get('session_id')}")
                    # 更新会话列表
                    rental_app.update_sessions()
                    # 重新加载页面
                    st.rerun()
        
        # 自动刷新控制
        st.divider()
        st.header("设置")
        auto_refresh = st.checkbox(
            "自动刷新会话列表", 
            value=st.session_state.auto_refresh,
            help="每30秒自动刷新会话列表"
        )
        
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
            st.rerun()
        
        # 手动刷新按钮
        if st.button("刷新会话列表"):
            rental_app.update_sessions()
            st.rerun()
    
    # 主内容区域
    rental_app.update_sessions()
    
    # 检查自动刷新
    current_time = time.time()
    if hasattr(st.session_state, 'last_refresh'):
        last_refresh = st.session_state.last_refresh
        time_diff = current_time - last_refresh
        
        # 更新最后刷新时间
        st.session_state.last_refresh = current_time
        
        # 如果启用自动刷新且间隔超过30秒，或会话列表为空，则刷新
        if (st.session_state.auto_refresh and 
            (time_diff > 30 or not any(
                rental_app.is_connected(s.get("session_id")) 
                for s in st.session_state.sessions))):
            rental_app.update_sessions()
    
    # 显示会话列表
    if not st.session_state.sessions:
        st.info("👋 欢迎！请在侧边栏创建一个新的租房协商会话。")
    else:
        # 创建会话选项卡
        session_tabs = st.tabs([
            f"{s.get('tenant_name', 'Tenant')} ↔ {s.get('landlord_name', 'Landlord')}" 
            for s in st.session_state.sessions
        ])
        
        # 为每个会话显示对话内容
        for i, (tab, session) in enumerate(zip(session_tabs, st.session_state.sessions)):
            with tab:
                session_id = session.get("session_id")
                
                # 如果这是第一次访问此会话，获取详细信息并连接WebSocket
                if not rental_app.is_connected(session_id):
                    rental_app.get_session_details(session_id)
                    rental_app.connect_to_session(session_id)
                
                # 显示会话基本信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("月租金", f"£{session.get('monthly_rent', 0):,.0f}")
                with col2:
                    st.metric("匹配分数", f"{session.get('match_score', 0):.1f}")
                with col3:
                    st.metric("状态", session.get('status', 'active'))
                with col4:
                    if rental_app.is_connected(session_id):
                        st.success("🟢 实时连接中")
                    else:
                        if st.button("🔗 连接实时对话", key=f"connect_{session_id}"):
                            rental_app.connect_to_session(session_id)
                            st.rerun()
                
                # 显示房产地址
                st.info(f"📍 地址: {session.get('property_address', 'N/A')}")
                
                # 显示对话消息
                messages = rental_app.get_messages(session_id)
                
                if messages:
                    with st.container():
                        # 创建聊天界面
                        for msg in messages[-50:]:  # 限制显示最近的50条消息
                            timestamp = msg.get("timestamp", "")
                            sender_name = msg.get("sender_name", "")
                            message = msg.get("message", "")
                            sender_type = msg.get("sender_type", "")
                            is_streaming = msg.get("is_streaming", False)
                            
                            # 根据发送者类型显示不同样式的消息
                            if sender_type == "tenant":
                                message_container = st.chat_message("user")
                                if is_streaming:
                                    message_container.write(f"**{sender_name}** ({timestamp}): {message}▌")
                                else:
                                    message_container.write(f"**{sender_name}** ({timestamp}): {message}")
                            
                            elif sender_type == "landlord":
                                message_container = st.chat_message("assistant")
                                if is_streaming:
                                    message_container.write(f"**{sender_name}** ({timestamp}): {message}▌")
                                else:
                                    message_container.write(f"**{sender_name}** ({timestamp}): {message}")
                            
                            elif sender_type == "system":
                                st.info(f"**{sender_name}** ({timestamp}): {message}")
                            
                            else:
                                st.write(f"**{sender_name}** ({timestamp}): {message}")
                    
                    # 清除新消息标记
                    new_count = rental_app.clear_new_messages(session_id)
                    if new_count > 0:
                        st.toast(f"已更新 {new_count} 条新消息")
                    
                    # 显示消息总数
                    st.caption(f"共 {len(messages)} 条消息")
                else:
                    st.warning("暂无对话消息。请等待实时对话开始...")
                
                # 可选：添加手动发送消息的功能（正常情况下由系统自动对话）
                with st.expander("高级操作：手动发送消息"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        message = st.text_input("消息内容", key=f"message_{session_id}")
                    with col2:
                        sender_type = st.selectbox(
                            "发送者",
                            ["tenant", "landlord"],
                            key=f"sender_type_{session_id}"
                        )
                    
                    if st.button("发送", key=f"send_{session_id}"):
                        if message:
                            result = rental_app.send_message(session_id, message, sender_type)
                            if "error" in result:
                                st.error(f"发送失败: {result['error']}")
                            else:
                                st.success("发送成功")
                                # 清空输入框
                                st.session_state[f"message_{session_id}"] = ""
                        else:
                            st.warning("请输入消息内容")


if __name__ == "__main__":
    main()
