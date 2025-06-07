"""
简化版租房协商对话展示面板
专门用于查看和展示现有的协商session对话内容
"""
import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# 页面配置
st.set_page_config(
    page_title="协商对话查看器",
    page_icon="💬",
    layout="wide"
)

# 简单样式
st.markdown("""
<style>
.session-box {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    background: #f8f9fa;
}

.selected-session {
    border: 2px solid #007bff;
    background: #e3f2fd;
}

.chat-tenant {
    background: #e8f5e8;
    padding: 0.8rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    border-left: 4px solid #28a745;
}

.chat-landlord {
    background: #fff3cd;
    padding: 0.8rem;
    border-radius: 8px;
    margin: 0.5rem 0;
    border-left: 4px solid #ffc107;
}
</style>
""", unsafe_allow_html=True)

API_BASE_URL = "http://localhost:8000"

class SimpleNegotiationViewer:
    """简单的协商对话查看器"""
    
    def __init__(self):
        if 'selected_session' not in st.session_state:
            st.session_state.selected_session = None
        if 'chat_logs' not in st.session_state:
            st.session_state.chat_logs = {}
    
    def check_api_connection(self) -> bool:
        """检查API连接"""
        try:
            response = requests.get(f"{API_BASE_URL}/", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_sessions(self) -> List[Dict]:
        """获取所有会话"""
        try:
            response = requests.get(f"{API_BASE_URL}/sessions", timeout=10)
            if response.status_code == 200:
                return response.json().get("sessions", [])
            return []
        except:
            return []
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        try:
            response = requests.get(f"{API_BASE_URL}/sessions/{session_id}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None
    
    def send_test_message(self, session_id: str, message: str, sender_type: str) -> Dict:
        """发送测试消息"""
        try:
            data = {"message": message, "sender_type": sender_type}
            response = requests.post(f"{API_BASE_URL}/sessions/{session_id}/message", json=data, timeout=30)
            if response.status_code == 200:
                return response.json()
            return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}


def main():
    """主函数"""
    st.title("💬 租房协商对话查看器")
    st.markdown("查看和测试租房协商系统中的对话session")
    
    viewer = SimpleNegotiationViewer()
    
    # 检查API连接
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if viewer.check_api_connection():
            st.success("✅ API连接正常")
        else:
            st.error("❌ 无法连接到API (http://localhost:8000)")
            st.stop()
    
    with col2:
        if st.button("🔄 刷新", type="secondary"):
            st.rerun()
    
    with col3:
        if st.button("🗑️ 清空日志"):
            st.session_state.chat_logs = {}
            st.success("已清空聊天日志")
    
    st.markdown("---")
    
    # 获取会话列表
    sessions = viewer.get_sessions()
    
    if not sessions:
        st.warning("暂无活跃的协商会话")
        st.info("请先运行后端API并创建一些协商会话")
        return
    
    # 布局：左侧会话列表，右侧对话内容
    col_sessions, col_chat = st.columns([1, 2])
    
    with col_sessions:
        st.header("📋 会话列表")
        st.caption(f"共找到 {len(sessions)} 个会话")
        
        for i, session in enumerate(sessions):
            # 处理session数据格式
            if hasattr(session, 'session_id'):
                session_id = session.session_id
                tenant_name = getattr(session, 'tenant_name', 'Unknown')
                landlord_name = getattr(session, 'landlord_name', 'Unknown')
                property_addr = getattr(session, 'property_address', 'Unknown')
                monthly_rent = getattr(session, 'monthly_rent', 0)
                status = getattr(session, 'status', 'Unknown')
            else:
                session_id = session.get('session_id', 'Unknown')
                tenant_name = session.get('tenant_name', 'Unknown')
                landlord_name = session.get('landlord_name', 'Unknown')
                property_addr = session.get('property_address', 'Unknown')
                monthly_rent = session.get('monthly_rent', 0)
                status = session.get('status', 'Unknown')
            
            # 会话卡片
            is_selected = st.session_state.selected_session == session_id
            box_class = "session-box selected-session" if is_selected else "session-box"
            
            with st.container():
                if st.button(
                    f"会话 {i+1}",
                    key=f"session_{i}",
                    help=f"点击查看会话 {session_id}",
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state.selected_session = session_id
                    st.rerun()
                
                st.markdown(f"""
                <div class="{box_class}">
                    <strong>🏠 {property_addr[:30]}...</strong><br>
                    <span style="color: #666;">ID: {session_id[-8:]}</span><br>
                    👤 租客: {tenant_name}<br>
                    🏢 房东: {landlord_name}<br>
                    💰 租金: ${monthly_rent}<br>
                    📊 状态: {status}
                </div>
                """, unsafe_allow_html=True)
    
    with col_chat:
        st.header("💬 对话内容")
        
        if not st.session_state.selected_session:
            st.info("👈 请从左侧选择一个会话查看对话内容")
            return
        
        session_id = st.session_state.selected_session
        session_info = viewer.get_session_info(session_id)
        
        if not session_info:
            st.error("无法获取会话信息")
            return
        
        # 显示会话详情
        with st.expander("📝 会话详情", expanded=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("月租金", f"${session_info.get('monthly_rent', 0)}")
            with col_b:
                st.metric("匹配分数", f"{session_info.get('match_score', 0):.2f}")
            with col_c:
                st.metric("状态", session_info.get('status', 'Unknown'))
            
            st.text(f"🏠 地址: {session_info.get('property_address', 'Unknown')}")
            st.text(f"👤 租客: {session_info.get('tenant_name', 'Unknown')}")
            st.text(f"🏢 房东: {session_info.get('landlord_name', 'Unknown')}")
        
        # 初始化聊天日志
        if session_id not in st.session_state.chat_logs:
            st.session_state.chat_logs[session_id] = []
        
        # 显示聊天历史
        st.subheader("💭 对话历史")
        
        chat_container = st.container()
        chat_logs = st.session_state.chat_logs[session_id]
        
        with chat_container:
            if not chat_logs:
                st.info("暂无对话记录，发送第一条消息开始对话！")
            else:
                for log in chat_logs:
                    if log['sender_type'] == 'tenant':
                        st.markdown(f"""
                        <div class="chat-tenant">
                            <strong>👤 {session_info.get('tenant_name', 'Tenant')}</strong> 
                            <span style="color: #666; font-size: 0.8em;">{log['timestamp']}</span><br>
                            {log['message']}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="chat-landlord">
                            <strong>🏢 {session_info.get('landlord_name', 'Landlord')}</strong> 
                            <span style="color: #666; font-size: 0.8em;">{log['timestamp']}</span><br>
                            {log['message']}
                        </div>
                        """, unsafe_allow_html=True)
        
        # 消息发送区域
        st.markdown("---")
        st.subheader("✉️ 发送消息")
        
        # 发送者选择
        sender_type = st.radio(
            "选择发送者",
            ["tenant", "landlord"],
            format_func=lambda x: f"👤 租客 ({session_info.get('tenant_name', 'Unknown')})" if x == "tenant" else f"🏢 房东 ({session_info.get('landlord_name', 'Unknown')})",
            horizontal=True
        )
        
        # 快速消息模板
        if sender_type == "tenant":
            templates = [
                "我对这个房产很感兴趣，能详细介绍一下吗？",
                "租金是否还有商量的空间？",
                "周边的交通和生活设施怎么样？",
                "什么时候可以安排看房？",
                "租金包含哪些费用？水电费怎么算？"
            ]
        else:
            templates = [
                "欢迎咨询！这套房子地理位置优越，设施完善。",
                "租金是按照市场价制定的，已经很优惠了。",
                "交通便利，附近有地铁站，生活设施齐全。",
                "随时可以安排看房，请提前预约。",
                "租金包含物业费，水电费按实际使用量计算。"
            ]
        
        template_msg = st.selectbox("选择消息模板（可选）", ["自定义"] + templates)
        
        # 消息输入
        if template_msg == "自定义":
            message = st.text_area("输入消息内容", height=100, placeholder="请输入要发送的消息...")
        else:
            message = st.text_area("消息内容", value=template_msg, height=100)
        
        # 发送按钮
        col_send, col_clear = st.columns([3, 1])
        
        with col_send:
            if st.button("📤 发送消息", type="primary", disabled=not message.strip()):
                with st.spinner("正在发送消息..."):
                    result = viewer.send_test_message(session_id, message.strip(), sender_type)
                    
                    if "error" not in result:
                        # 记录发送的消息
                        st.session_state.chat_logs[session_id].append({
                            'sender_type': sender_type,
                            'message': message.strip(),
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        
                        # 记录响应
                        response_sender = "landlord" if sender_type == "tenant" else "tenant"
                        st.session_state.chat_logs[session_id].append({
                            'sender_type': response_sender,
                            'message': result.get('response', ''),
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        
                        st.success("✅ 消息发送成功！")
                        st.rerun()
                    else:
                        st.error(f"❌ 发送失败: {result['error']}")
        
        with col_clear:
            if st.button("🗑️ 清空对话"):
                st.session_state.chat_logs[session_id] = []
                st.success("已清空当前会话的对话记录")
                st.rerun()


if __name__ == "__main__":
    main()
