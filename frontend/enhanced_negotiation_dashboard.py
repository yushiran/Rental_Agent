"""
增强版租房协商对话展示面板
支持WebSocket实时通信和更好的用户体验
"""
import streamlit as st
import requests
import json
import asyncio
import websocket
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
import time
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="租房协商实时对话面板",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
.session-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.chat-message-user {
    background: #e3f2fd;
    padding: 0.8rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    border-left: 4px solid #2196f3;
}

.chat-message-assistant {
    background: #f3e5f5;
    padding: 0.8rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    border-left: 4px solid #9c27b0;
}

.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    text-align: center;
}

.status-active {
    color: #4caf50;
    font-weight: bold;
}

.status-pending {
    color: #ff9800;
    font-weight: bold;
}

.status-completed {
    color: #2196f3;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# API基础URL
API_BASE_URL = "http://localhost:8001"

class EnhancedNegotiationDashboard:
    """增强版协商对话面板"""
    
    def __init__(self):
        self.sessions = []
        self.selected_session = None
        
        # 初始化session state
        if 'chat_histories' not in st.session_state:
            st.session_state.chat_histories = {}
        if 'selected_session_id' not in st.session_state:
            st.session_state.selected_session_id = None
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = False
    
    def fetch_sessions(self) -> List[Dict]:
        """获取所有活跃的协商会话"""
        try:
            response = requests.get(f"{API_BASE_URL}/sessions", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("sessions", [])
            else:
                st.error(f"获取会话失败: {response.status_code}")
                return []
        except requests.exceptions.ConnectionError:
            st.error("🔌 无法连接到API服务器，请确保后端服务正在运行 (http://localhost:8001)")
            return []
        except Exception as e:
            st.error(f"连接API失败: {e}")
            return []
    
    def get_session_details(self, session_id: str) -> Optional[Dict]:
        """获取特定会话的详细信息"""
        try:
            response = requests.get(f"{API_BASE_URL}/sessions/{session_id}", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            st.error(f"获取会话详情失败: {e}")
            return None
    
    def send_message(self, session_id: str, message: str, sender_type: str) -> Dict:
        """发送消息到协商会话"""
        try:
            data = {
                "message": message,
                "sender_type": sender_type
            }
            response = requests.post(
                f"{API_BASE_URL}/sessions/{session_id}/message",
                json=data,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"发送失败: {response.status_code}"}
        except Exception as e:
            return {"error": f"发送消息失败: {e}"}
    
    def start_group_negotiation(self, max_tenants: int = 3) -> Dict:
        """启动群体协商"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/start-group-negotiation",
                params={"max_tenants": max_tenants},
                timeout=60
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"启动失败: {response.status_code}"}
        except Exception as e:
            return {"error": f"启动协商失败: {e}"}
    
    def simulate_tenant_interests(self) -> Dict:
        """模拟租客兴趣"""
        try:
            response = requests.post(f"{API_BASE_URL}/simulate-tenant-interests", timeout=60)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"模拟失败: {response.status_code}"}
        except Exception as e:
            return {"error": f"模拟失败: {e}"}
    
    def start_auto_negotiation(self, max_rounds: int = 5) -> Dict:
        """启动自动协商"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/start-auto-negotiation",
                params={"max_rounds": max_rounds},
                timeout=120  # 自动协商可能需要更长时间
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"自动协商失败: {response.status_code}"}
        except Exception as e:
            return {"error": f"自动协商失败: {e}"}
    
    def get_negotiation_stats(self) -> Dict:
        """获取协商统计信息"""
        try:
            response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"获取统计失败: {response.status_code}"}
        except Exception as e:
            return {"error": f"获取统计失败: {e}"}
    
    def format_session_info(self, session: Dict) -> Dict:
        """格式化会话信息"""
        if hasattr(session, 'session_id'):
            return {
                'session_id': session.session_id,
                'tenant_name': getattr(session, 'tenant_name', 'Unknown'),
                'landlord_name': getattr(session, 'landlord_name', 'Unknown'),
                'property_address': getattr(session, 'property_address', 'Unknown'),
                'monthly_rent': getattr(session, 'monthly_rent', 0),
                'match_score': getattr(session, 'match_score', 0),
                'status': getattr(session, 'status', 'Unknown')
            }
        else:
            return {
                'session_id': session.get('session_id', 'Unknown'),
                'tenant_name': session.get('tenant_name', 'Unknown'),
                'landlord_name': session.get('landlord_name', 'Unknown'),
                'property_address': session.get('property_address', 'Unknown'),
                'monthly_rent': session.get('monthly_rent', 0),
                'match_score': session.get('match_score', 0),
                'status': session.get('status', 'Unknown')
            }
    
    def display_chat_message(self, message: str, sender_type: str, sender_name: str, timestamp: datetime):
        """显示聊天消息"""
        if sender_type == 'tenant':
            with st.chat_message("user", avatar="👤"):
                st.markdown(f"**{sender_name}** - {timestamp.strftime('%H:%M:%S')}")
                st.write(message)
        else:
            with st.chat_message("assistant", avatar="🏢"):
                st.markdown(f"**{sender_name}** - {timestamp.strftime('%H:%M:%S')}")
                st.write(message)


def main():
    """主函数"""
    # 页面标题
    st.markdown("""
    # 🏠 租房协商实时对话面板
    ### 智能租房协商系统 - 实时监控与交互界面
    """)
    
    # 初始化面板
    dashboard = EnhancedNegotiationDashboard()
    
    # 全局状态监控栏
    status_container = st.container()
    with status_container:
        col1, col2, col3, col4 = st.columns(4)
        
        # 获取实时统计
        stats = dashboard.get_negotiation_stats()
        sessions = dashboard.fetch_sessions()
        
        with col1:
            active_sessions = stats.get("active_sessions", 0) if "error" not in stats else len(sessions)
            st.metric("🔄 活跃会话", active_sessions)
        
        with col2:
            total_messages = stats.get("total_messages", 0) if "error" not in stats else 0
            st.metric("💬 总对话数", total_messages)
        
        with col3:
            avg_score = stats.get("average_match_score", 0) if "error" not in stats else 0
            st.metric("⭐ 平均匹配分", f"{avg_score:.1f}")
        
        with col4:
            # 检查是否有进行中的自动协商（基于最近的消息活动）
            recent_activity = "🟢 活跃" if total_messages > 0 else "🔴 空闲"
            st.metric("🤖 系统状态", recent_activity)
    
    st.markdown("---")
    
    # 初始化面板
    dashboard = EnhancedNegotiationDashboard()
    
    # 侧边栏控制
    with st.sidebar:
        st.header("🎛️ 控制面板")
        
        # 连接状态检查
        st.subheader("🔌 连接状态")
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=5)
            if response.status_code == 200:
                st.success("✅ API服务器连接正常")
            else:
                st.error("❌ API服务器响应异常")
        except:
            st.error("❌ 无法连接到API服务器")
            st.info("请确保后端服务正在运行在 http://localhost:8001")
        
        st.markdown("---")
        
        # 自动刷新控制
        st.subheader("🔄 自动刷新")
        auto_refresh = st.checkbox("启用自动刷新", value=st.session_state.auto_refresh)
        if auto_refresh != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto_refresh
        
        if auto_refresh:
            refresh_interval = st.slider("刷新间隔（秒）", 5, 60, 10)
        
        # 手动刷新
        if st.button("🔄 立即刷新", type="secondary"):
            st.rerun()
        
        st.markdown("---")
        
        # 协商控制
        st.subheader("🚀 协商控制")
        max_tenants = st.number_input("最大租客数量", min_value=1, max_value=10, value=3)
        
        col_start, col_sim = st.columns(2)
        
        with col_start:
            if st.button("🚀 启动协商", type="primary", use_container_width=True):
                with st.spinner("正在启动协商..."):
                    result = dashboard.start_group_negotiation(max_tenants)
                    if "error" not in result:
                        st.success(f"✅ 成功创建 {result.get('successful_matches', 0)} 个协商会话")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
        
        with col_sim:
            if st.button("🎭 模拟兴趣", type="secondary", use_container_width=True):
                with st.spinner("正在模拟租客兴趣..."):
                    result = dashboard.simulate_tenant_interests()
                    if "error" not in result:
                        st.success(f"✅ 模拟了 {result.get('successful_simulations', 0)} 个会话")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
        
        st.markdown("---")
        
        # 自动协商控制
        st.subheader("🤖 自动协商")
        max_rounds = st.number_input("最大协商轮数", min_value=2, max_value=10, value=5, help="系统会自动进行多轮对话")
        
        if st.button("🤖 开始自动协商", type="primary", use_container_width=True):
            if not dashboard.fetch_sessions():
                st.warning("⚠️ 请先启动协商创建会话")
            else:
                with st.spinner(f"正在进行 {max_rounds} 轮自动协商..."):
                    result = dashboard.start_auto_negotiation(max_rounds)
                    if "error" not in result:
                        st.success(f"✅ {result.get('message', '自动协商完成')}")
                        st.info(f"📊 总共进行了 {result.get('total_exchanges', 0)} 次对话交换")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
        
        st.markdown("---")
        
        # 统计信息
        st.subheader("📊 协商统计")
        stats = dashboard.get_negotiation_stats()
        if "error" not in stats:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("活跃会话", stats.get("active_sessions", 0), delta=None)
                st.metric("平均匹配分数", f"{stats.get('average_match_score', 0):.2f}")
            with col2:
                st.metric("总消息数", stats.get("total_messages", 0))
                st.metric("平均消息/会话", f"{stats.get('average_messages_per_session', 0):.1f}")
        else:
            st.info("暂无统计数据")
    
    # 主内容区域
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📋 活跃会话列表")
        
        # 获取会话列表
        sessions = dashboard.fetch_sessions()
        
        if not sessions:
            st.info("暂无活跃的协商会话")
            st.markdown("""
            #### 开始使用：
            1. 点击左侧 **"🚀 启动协商"** 创建新会话
            2. 或点击 **"🎭 模拟兴趣"** 激活现有会话
            """)
        else:
            st.success(f"找到 {len(sessions)} 个活跃会话")
            
            # 会话筛选
            status_filter = st.selectbox(
                "筛选状态",
                ["全部", "active", "pending", "completed"],
                index=0
            )
            
            # 显示会话卡片
            for i, session in enumerate(sessions):
                session_info = dashboard.format_session_info(session)
                
                # 应用筛选
                if status_filter != "全部" and session_info['status'] != status_filter:
                    continue
                
                # 会话卡片
                with st.container():
                    # 状态颜色
                    status_class = f"status-{session_info['status']}"
                    
                    col_select, col_info = st.columns([1, 4])
                    
                    with col_select:
                        if st.button("选择", key=f"select_{i}", type="secondary"):
                            st.session_state.selected_session_id = session_info['session_id']
                            # 初始化聊天历史
                            if session_info['session_id'] not in st.session_state.chat_histories:
                                st.session_state.chat_histories[session_info['session_id']] = []
                            st.rerun()
                    
                    with col_info:
                        # 检查是否为当前选中的会话
                        is_selected = (st.session_state.selected_session_id == session_info['session_id'])
                        border_style = "border: 2px solid #4CAF50;" if is_selected else "border: 1px solid #ddd;"
                        
                        st.markdown(f"""
                        <div style="padding: 0.8rem; border-radius: 8px; background: #f8f9fa; {border_style}">
                            <strong>🏘️ {session_info['property_address'][:40]}...</strong><br>
                            <span class="{status_class}">● {session_info['status'].upper()}</span><br>
                            👤 租客: {session_info['tenant_name']}<br>
                            🏢 房东: {session_info['landlord_name']}<br>
                            💰 租金: ${session_info['monthly_rent']}<br>
                            📊 匹配分数: {session_info['match_score']:.2f}
                        </div>
                        """, unsafe_allow_html=True)
    
    with col2:
        st.header("💬 对话内容")
        
        # 检查是否选择了会话
        if st.session_state.selected_session_id:
            session_id = st.session_state.selected_session_id
            
            # 获取会话详情
            session_details = dashboard.get_session_details(session_id)
            
            if session_details:
                # 会话信息面板
                with st.expander("📝 会话详细信息", expanded=False):
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("月租金", f"${session_details.get('monthly_rent', 0)}")
                    with col_b:
                        st.metric("匹配分数", f"{session_details.get('match_score', 0):.2f}")
                    with col_c:
                        st.metric("状态", session_details.get('status', 'Unknown'))
                    with col_d:
                        st.metric("会话ID", session_id[-8:])
                    
                    st.markdown(f"""
                    **🏠 房产地址:** {session_details.get('property_address', 'Unknown')}  
                    **👤 租客:** {session_details.get('tenant_name', 'Unknown')}  
                    **🏢 房东:** {session_details.get('landlord_name', 'Unknown')}
                    """)
                
                # 对话历史显示
                st.subheader("🗨️ 对话历史")
                
                # 初始化聊天历史
                if session_id not in st.session_state.chat_histories:
                    st.session_state.chat_histories[session_id] = []
                
                # 显示聊天历史
                chat_container = st.container()
                with chat_container:
                    chat_history = st.session_state.chat_histories[session_id]
                    
                    if not chat_history:
                        st.info("暂无对话记录，开始发送第一条消息吧！")
                    else:
                        for msg in chat_history:
                            dashboard.display_chat_message(
                                msg['message'],
                                msg['sender_type'],
                                msg['sender_name'],
                                msg['timestamp']
                            )
                
                # 消息发送区域
                st.markdown("---")
                st.subheader("✉️ 发送新消息")
                
                # 发送者选择
                col_sender, col_preset = st.columns([1, 1])
                
                with col_sender:
                    sender_type = st.radio(
                        "选择发送者身份",
                        ["tenant", "landlord"],
                        format_func=lambda x: f"👤 租客 ({session_details.get('tenant_name', 'Unknown')})" if x == "tenant" else f"🏢 房东 ({session_details.get('landlord_name', 'Unknown')})",
                        horizontal=False
                    )
                
                with col_preset:
                    st.write("**快速消息模板:**")
                    if sender_type == "tenant":
                        preset_messages = [
                            "您好，我对这个房产很感兴趣！",
                            "请问租金还有商量的余地吗？",
                            "能告诉我更多关于周边设施的信息吗？",
                            "什么时候可以看房？",
                            "这个价格包含哪些费用？"
                        ]
                    else:
                        preset_messages = [
                            "欢迎咨询！这是一个很好的房产。",
                            "租金是根据市场价格制定的，比较合理。",
                            "周边交通便利，生活设施齐全。",
                            "我们可以安排时间看房。",
                            "价格包含基本设施，具体可以详谈。"
                        ]
                    
                    selected_preset = st.selectbox("选择模板消息", ["自定义"] + preset_messages)
                
                # 消息输入和发送
                with st.form("message_form", clear_on_submit=True):
                    if selected_preset == "自定义":
                        message = st.text_area(
                            "输入消息内容",
                            placeholder="请输入要发送的消息...",
                            height=100
                        )
                    else:
                        message = st.text_area(
                            "消息内容",
                            value=selected_preset,
                            height=100
                        )
                    
                    col_send, col_clear = st.columns([3, 1])
                    
                    with col_send:
                        submitted = st.form_submit_button("📤 发送消息", type="primary", use_container_width=True)
                    
                    with col_clear:
                        clear_history = st.form_submit_button("🗑️ 清空历史", use_container_width=True)
                    
                    if submitted and message.strip():
                        with st.spinner("正在发送消息..."):
                            result = dashboard.send_message(session_id, message.strip(), sender_type)
                            
                            if "error" not in result:
                                # 添加用户消息到历史
                                sender_name = session_details.get('tenant_name') if sender_type == 'tenant' else session_details.get('landlord_name')
                                st.session_state.chat_histories[session_id].append({
                                    'sender_type': sender_type,
                                    'sender_name': sender_name,
                                    'message': message.strip(),
                                    'timestamp': datetime.now()
                                })
                                
                                # 添加响应到历史
                                response_sender = "landlord" if sender_type == "tenant" else "tenant"
                                response_sender_name = session_details.get('landlord_name') if sender_type == 'tenant' else session_details.get('tenant_name')
                                st.session_state.chat_histories[session_id].append({
                                    'sender_type': response_sender,
                                    'sender_name': response_sender_name,
                                    'message': result.get('response', ''),
                                    'timestamp': datetime.now()
                                })
                                
                                st.success("✅ 消息发送成功！")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(f"❌ 发送失败: {result['error']}")
                    
                    if clear_history:
                        st.session_state.chat_histories[session_id] = []
                        st.success("🗑️ 对话历史已清空")
                        time.sleep(0.5)
                        st.rerun()
                        
            else:
                st.error("❌ 无法获取会话详情")
                st.button("🔄 重试", on_click=st.rerun)
        else:
            # 未选择会话时的引导界面
            st.info("👈 请从左侧选择一个协商会话开始查看对话内容")
            
            st.markdown("""
            ### 📖 使用指南
            
            #### 🚀 快速开始
            1. **创建协商会话**: 点击左侧 "🚀 启动协商" 按钮
            2. **选择会话**: 从会话列表中选择一个协商会话
            3. **查看对话**: 在此区域查看租客和房东的实时对话
            4. **参与对话**: 选择身份并发送消息参与协商
            
            #### 💡 功能特点
            - 🔄 **实时更新**: 支持自动刷新获取最新对话
            - 💬 **双向对话**: 可以模拟租客或房东发送消息
            - 📊 **详细统计**: 显示协商会话的各项统计信息
            - 🎨 **美观界面**: 现代化的用户界面设计
            - 📱 **响应式布局**: 适配不同屏幕尺寸
            
            #### 🔧 高级功能
            - **消息模板**: 使用预设的消息模板快速发送
            - **状态筛选**: 按会话状态筛选显示
            - **历史记录**: 查看完整的对话历史
            - **实时监控**: 监控协商进度和统计数据
            """)
    
    # 自动刷新逻辑
    if st.session_state.auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
