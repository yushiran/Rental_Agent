"""
实时自动协商演示 - 基于WebSocket的实时对话展示
"""
import streamlit as st
import requests
import json
import asyncio
import websockets
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class WebSocketNegotiationDemo:
    """WebSocket实时自动协商演示"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8001"
        self.websocket_url = "ws://localhost:8001"
        self.session_messages: Dict[str, List[Dict]] = {}
        self.websocket_connections: Dict[str, object] = {}
        self.is_running = False
        
    def get_all_sessions(self) -> List[Dict]:
        """获取所有活跃会话"""
        try:
            response = requests.get(f"{self.api_base_url}/sessions")
            if response.status_code == 200:
                return response.json().get("sessions", [])
            return []
        except Exception as e:
            st.error(f"获取会话失败: {str(e)}")
            return []
    
    def start_group_negotiation(self, max_tenants: int = 10) -> Dict:
        """启动群体协商"""
        try:
            response = requests.post(
                f"{self.api_base_url}/start-group-negotiation",
                params={"max_tenants": max_tenants}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def start_auto_negotiation_live(self, max_rounds: int = 5) -> Dict:
        """启动实时自动协商"""
        try:
            response = requests.post(
                f"{self.api_base_url}/start-auto-negotiation-live",
                params={"max_rounds": max_rounds}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_negotiation_stats(self) -> Dict:
        """获取协商统计"""
        try:
            response = requests.get(f"{self.api_base_url}/stats")
            return response.json()
        except Exception as e:
            return {"active_sessions": 0}
    
    async def connect_websocket(self, session_id: str):
        """连接到特定会话的WebSocket"""
        try:
            uri = f"{self.websocket_url}/ws/{session_id}"
            async with websockets.connect(uri) as websocket:
                self.websocket_connections[session_id] = websocket
                
                # 监听消息
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if session_id not in self.session_messages:
                            self.session_messages[session_id] = []
                        
                        self.session_messages[session_id].append({
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "data": data
                        })
                        
                        # 在Streamlit中显示新消息需要触发重新运行
                        
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            st.error(f"WebSocket连接失败: {str(e)}")
    
    def connect_to_all_sessions(self, sessions: List[Dict]):
        """连接到所有会话的WebSocket"""
        for session in sessions:
            session_id = session["session_id"]
            # 在新线程中启动WebSocket连接
            thread = threading.Thread(
                target=lambda: asyncio.run(self.connect_websocket(session_id))
            )
            thread.daemon = True
            thread.start()


def main():
    """主程序"""
    st.set_page_config(
        page_title="🔄 实时自动协商演示",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔄 实时自动协商演示")
    st.markdown("基于WebSocket的租客-房东实时对话系统")
    
    demo = WebSocketNegotiationDemo()
    
    # 侧边栏控制
    st.sidebar.header("🎮 控制面板")
    
    # 步骤1：启动群体协商
    st.sidebar.subheader("步骤1: 启动群体协商")
    max_tenants = st.sidebar.slider("最大租客数量", 1, 20, 5)
    
    if st.sidebar.button("🚀 启动群体协商", type="primary"):
        with st.spinner("正在启动群体协商..."):
            result = demo.start_group_negotiation(max_tenants)
            if "error" in result:
                st.sidebar.error(f"启动失败: {result['error']}")
            else:
                st.sidebar.success(f"✅ 成功启动 {result['successful_matches']} 个协商会话")
                st.rerun()
    
    # 获取当前会话
    sessions = demo.get_all_sessions()
    stats = demo.get_negotiation_stats()
    
    # 状态概览
    st.sidebar.subheader("📊 当前状态")
    st.sidebar.metric("活跃会话", stats.get("active_sessions", 0))
    st.sidebar.metric("总消息数", stats.get("total_messages", 0))
    
    if sessions:
        st.sidebar.metric("平均匹配分数", f"{stats.get('average_match_score', 0):.2f}")
    
    # 步骤2：启动实时协商
    if sessions:
        st.sidebar.subheader("步骤2: 启动实时协商")
        max_rounds = st.sidebar.slider("最大对话轮数", 2, 10, 5)
        
        if st.sidebar.button("🤖 开始实时自动协商", type="secondary"):
            demo.is_running = True
            
            # 连接到所有会话的WebSocket
            demo.connect_to_all_sessions(sessions)
            
            with st.spinner("正在启动实时自动协商..."):
                result = demo.start_auto_negotiation_live(max_rounds)
                if "error" in result:
                    st.sidebar.error(f"启动失败: {result['error']}")
                else:
                    st.sidebar.success(f"✅ {result['message']}")
    
    # 主内容区域
    if not sessions:
        st.info("👆 请先在侧边栏启动群体协商以创建会话")
        return
    
    # 实时消息展示
    st.header("💬 实时对话展示")
    
    # 创建选项卡
    if len(sessions) <= 4:
        # 如果会话数较少，显示所有会话
        tabs = st.tabs([f"会话 {i+1}" for i in range(len(sessions))])
        
        for i, (tab, session) in enumerate(zip(tabs, sessions)):
            with tab:
                display_session_messages(demo, session)
    else:
        # 如果会话数较多，允许选择特定会话
        selected_session_idx = st.selectbox(
            "选择要查看的会话",
            range(len(sessions)),
            format_func=lambda x: f"会话 {x+1}: {sessions[x]['tenant_name']} ↔ {sessions[x]['landlord_name']}"
        )
        
        if selected_session_idx is not None:
            display_session_messages(demo, sessions[selected_session_idx])
    
    # 统计图表
    if len(sessions) > 1:
        st.header("📈 会话统计")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 匹配分数分布
            match_scores = [s["match_score"] for s in sessions]
            fig = px.histogram(
                x=match_scores,
                title="匹配分数分布",
                labels={"x": "匹配分数", "y": "会话数量"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 会话状态饼图
            status_counts = {}
            for session in sessions:
                status = session["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            fig = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="会话状态分布"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # 自动刷新
    if demo.is_running:
        time.sleep(2)
        st.rerun()


def display_session_messages(demo: WebSocketNegotiationDemo, session: Dict):
    """显示特定会话的消息"""
    session_id = session["session_id"]
    
    # 会话信息
    st.subheader(f"🏠 {session['property_address']}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("租客", session["tenant_name"])
    with col2:
        st.metric("房东", session["landlord_name"])
    with col3:
        st.metric("月租", f"¥{session['monthly_rent']:,}")
    
    # 实时消息
    if session_id in demo.session_messages:
        messages = demo.session_messages[session_id]
        
        st.subheader("💬 实时对话")
        
        # 创建消息容器
        message_container = st.container()
        
        with message_container:
            for msg in messages[-10:]:  # 只显示最新的10条消息
                data = msg["data"]
                timestamp = msg["timestamp"]
                
                if data.get("type") == "session_info":
                    st.info(f"[{timestamp}] 会话已建立")
                
                elif data.get("type") == "auto_negotiation_start":
                    st.success(f"[{timestamp}] 🤖 自动协商开始，最大轮数: {data.get('max_rounds', 0)}")
                
                elif data.get("type") == "round_start":
                    st.warning(f"[{timestamp}] 🔄 第 {data.get('round_number', 0)} 轮开始")
                
                elif data.get("type") == "tenant_interest_start":
                    st.info(f"[{timestamp}] 👤 {data.get('sender_name', '租客')} 开始表达兴趣")
                
                elif data.get("type") == "tenant_interest_complete":
                    tenant_msg = data.get("tenant_message", "")
                    landlord_resp = data.get("landlord_response", "")
                    
                    st.chat_message("user").write(f"**租客**: {tenant_msg}")
                    st.chat_message("assistant").write(f"**房东**: {landlord_resp}")
                
                elif data.get("type") == "tenant_message_start":
                    st.chat_message("user").write(f"**租客** (第{data.get('round', 0)}轮): {data.get('message', '')}")
                
                elif data.get("type") == "landlord_response":
                    st.chat_message("assistant").write(f"**房东** (第{data.get('round', 0)}轮): {data.get('response', '')}")
                
                elif data.get("type") == "round_complete":
                    st.success(f"[{timestamp}] ✅ 第 {data.get('round_number', 0)} 轮完成")
                
                elif data.get("type") == "auto_negotiation_complete":
                    st.balloons()
                    st.success(f"[{timestamp}] 🎉 自动协商完成！共进行了 {data.get('completed_rounds', 0)} 轮对话")
                
                elif data.get("type") == "error":
                    st.error(f"[{timestamp}] ❌ 错误: {data.get('error', '未知错误')}")
    
    else:
        st.info("等待WebSocket连接...")


if __name__ == "__main__":
    main()
