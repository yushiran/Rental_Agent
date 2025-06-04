"""
English Streamlit Interface for Rental Agent System
Multi-Agent Rental Negotiation Demo
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

from app.agents.base import Property


class RentalAgentDemo:
    """English Streamlit interface for rental agent system"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.client_id = f"streamlit_{int(time.time())}"
        
        # Initialize session state
        if "agents_created" not in st.session_state:
            st.session_state.agents_created = False
        if "conversation_id" not in st.session_state:
            st.session_state.conversation_id = None
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "conversation_active" not in st.session_state:
            st.session_state.conversation_active = False
        if "last_message_count" not in st.session_state:
            st.session_state.last_message_count = 0
            
    def run(self):
        """Run the Streamlit application"""
        st.set_page_config(
            page_title="Rental Agent System",
            page_icon="🏠",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("🏠 Rental Agent Negotiation System")
        st.markdown("**Multi-Agent Rental Negotiation with AutoGen**")
        st.markdown("---")
        
        # Sidebar configuration
        self._render_sidebar()
        
        # Main interface
        col1, col2 = st.columns([1, 2])
        
        with col1:
            self._render_setup_panel()
            
        with col2:
            self._render_conversation_panel()
            
    def _render_sidebar(self):
        """Render sidebar with system status and controls"""
        st.sidebar.title("System Configuration")
        
        # API connection status
        st.sidebar.subheader("Connection Status")
        if self._check_api_health():
            st.sidebar.success("✅ API Service Online")
        else:
            st.sidebar.error("❌ API Service Offline")
            
        # System information
        st.sidebar.subheader("System Info")
        st.sidebar.info(f"Client ID: {self.client_id}")
        
        # Quick actions
        st.sidebar.subheader("Quick Actions")
        if st.sidebar.button("🎭 Create Demo Scenario"):
            self._create_demo_scenario()
            
        if st.sidebar.button("🗑️ Clear All Data"):
            self._clear_all_data()
            
        # Conversation settings
        st.sidebar.subheader("Conversation Settings")
        st.sidebar.info("Max Rounds: 6")
        st.sidebar.info("Auto-termination: ON")
        st.sidebar.info("Termination triggers:")
        st.sidebar.text("• Agreement reached")
        st.sidebar.text("• Deal rejected")
        st.sidebar.text("• Max rounds reached")
        
    def _render_setup_panel(self):
        """Render agent setup panel"""
        st.subheader("🤖 Agent Configuration")
        
        # Quick scenario setup
        st.markdown("### Quick Start")
        
        scenario_type = st.selectbox(
            "Select Scenario Type",
            ["Budget Conscious Tenant", "Premium Property Deal", "Market Analysis Focus"]
        )
        
        if st.button("🚀 Start Rental Negotiation"):
            if scenario_type == "Budget Conscious Tenant":
                self._start_budget_scenario()
            elif scenario_type == "Premium Property Deal":
                self._start_premium_scenario()
            else:
                self._start_analysis_scenario()
        
        st.markdown("---")
        
        # Manual agent setup (expandable)
        with st.expander("Manual Agent Setup", expanded=False):
            self._render_manual_setup()
            
    def _render_manual_setup(self):
        """Render manual agent configuration"""
        st.markdown("#### Tenant Configuration")
        tenant_name = st.text_input("Tenant Name", "Alex_Chen")
        budget = st.number_input("Budget (¥/month)", min_value=1000, max_value=20000, value=5000)
        areas = st.multiselect("Preferred Areas", 
                              ["Chaoyang", "Haidian", "Dongcheng", "Xicheng"], 
                              default=["Chaoyang"])
        
        st.markdown("#### Landlord Configuration")
        landlord_name = st.text_input("Landlord Name", "Wang_Property")
        property_price = st.number_input("Property Price (¥/month)", min_value=2000, max_value=15000, value=4800)
        property_type = st.selectbox("Property Type", ["Apartment", "House", "Studio"])
        
        if st.button("Create Custom Scenario"):
            self._start_custom_scenario(tenant_name, budget, areas, landlord_name, property_price, property_type)
            
    def _render_conversation_panel(self):
        """Render conversation display panel"""
        st.subheader("💬 Rental Negotiation")
        
        if not st.session_state.conversation_active:
            st.info("👆 Start a scenario from the left panel to begin negotiation")
            return
            
        # Conversation status
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Conversation ID", st.session_state.conversation_id[:8] if st.session_state.conversation_id else "None")
        with col2:
            message_count = len(st.session_state.messages)
            st.metric("Messages", message_count, delta=message_count - st.session_state.last_message_count)
        with col3:
            rounds_left = max(0, 6 - (message_count // 3))  # Approximate rounds
            st.metric("Rounds Left", rounds_left)
            
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh conversation", value=True)
        
        if auto_refresh:
            # Auto-refresh every 3 seconds
            if st.session_state.conversation_active:
                time.sleep(1)  # Brief pause
                self._update_messages()
                st.rerun()
        
        # Manual refresh button
        if st.button("🔄 Refresh Messages"):
            self._update_messages()
            st.rerun()
            
        # Messages display
        st.markdown("### Conversation History")
        
        # Create a container for messages
        message_container = st.container()
        
        with message_container:
            if st.session_state.messages:
                for i, msg in enumerate(st.session_state.messages):
                    self._render_message(msg, i)
            else:
                st.info("No messages yet. Agents are preparing to negotiate...")
                
        # Control buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("⏹️ End Conversation"):
                self._end_conversation()
                
        with col2:
            if st.button("💾 Save Conversation"):
                self._save_conversation()
                
        with col3:
            if st.button("📊 Show Analysis"):
                self._show_conversation_analysis()
                
    def _render_message(self, message: Dict, index: int):
        """Render individual message with styling"""
        sender = message.get("name", "System")
        content = message.get("content", "")
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Make display name more friendly by replacing underscores with spaces
        display_name = sender.replace("_", " ")
        
        # Determine message style based on sender
        if sender == "系统" or sender == "System":
            st.info(f"**{display_name}** ({timestamp})")
            st.write(content)
        elif "租客" in sender or "Tenant" in sender or "Alex" in sender or "Sarah" in sender or "David" in sender:
            st.success(f"**🏠 {display_name}** ({timestamp})")
            st.write(content)
        elif "房主" in sender or "Landlord" in sender or "Wang" in sender or "Premium" in sender or "Smart" in sender:
            st.warning(f"**🏢 {display_name}** ({timestamp})")
            st.write(content)
        elif "分析师" in sender or "Analyst" in sender:
            st.info(f"**📊 {display_name}** ({timestamp})")
            st.write(content)
        else:
            st.write(f"**{display_name}** ({timestamp})")
            st.write(content)
            
        st.markdown("---")
        
    def _start_budget_scenario(self):
        """Start budget conscious tenant scenario"""
        st.info("🚀 Starting Budget Conscious Tenant Scenario...")
        
        scenario_config = {
            "tenant": {
                "name": "Alex_Chen",
                "budget": 4500,
                "preferred_areas": ["Chaoyang", "Haidian"],
                "requirements": {
                    "min_bedrooms": 1,
                    "min_bathrooms": 1,
                    "required_amenities": ["WiFi", "Air Conditioning"]
                }
            },
            "landlord": {
                "name": "Wang_Property_Manager",
                "pricing_strategy": "market_based"
            },
            "property": {
                "id": "prop_budget_001",
                "address": "Chaoyang District, Near Subway",
                "price": 4800,
                "property_type": "Apartment",
                "bedrooms": 1,
                "bathrooms": 1,
                "area": 65,
                "amenities": ["WiFi", "Air Conditioning", "Washing Machine", "Refrigerator"],
                "available_date": "2025-06-01",
                "description": "Modern 1-bedroom apartment near subway station with excellent amenities",
                "landlord_id": "landlord_wang_001"
            }
        }
        
        self._start_scenario(scenario_config)
        
    def _start_premium_scenario(self):
        """Start premium property scenario"""
        st.info("🚀 Starting Premium Property Scenario...")
        
        scenario_config = {
            "tenant": {
                "name": "Sarah_Liu",
                "budget": 8000,
                "preferred_areas": ["Dongcheng", "Xicheng"],
                "requirements": {
                    "min_bedrooms": 2,
                    "min_bathrooms": 2,
                    "required_amenities": ["Parking", "Gym"]
                }
            },
            "landlord": {
                "name": "Premium_Estates",
                "pricing_strategy": "market_based"
            },
            "property": {
                "id": "prop_premium_001",
                "address": "Dongcheng District, CBD Area",
                "price": 7500,
                "property_type": "Luxury Apartment",
                "bedrooms": 2,
                "bathrooms": 2,
                "area": 120,
                "amenities": ["Parking", "Gym", "Pool", "WiFi", "Air Conditioning", "Balcony"],
                "available_date": "2025-06-15",
                "description": "Luxury 2-bedroom apartment in CBD with premium amenities including gym and pool",
                "landlord_id": "landlord_premium_001"
            }
        }
        
        self._start_scenario(scenario_config)
        
    def _start_analysis_scenario(self):
        """Start market analysis focused scenario"""
        st.info("🚀 Starting Market Analysis Scenario...")
        
        scenario_config = {
            "tenant": {
                "name": "David_Zhang",
                "budget": 6000,
                "preferred_areas": ["Haidian"],
                "requirements": {
                    "min_bedrooms": 1,
                    "min_bathrooms": 1,
                    "required_amenities": ["WiFi"]
                }
            },
            "landlord": {
                "name": "Smart_Property",
                "pricing_strategy": "market_based"
            },
            "property": {
                "id": "prop_analysis_001",
                "address": "Haidian District, Tech Hub",
                "price": 5800,
                "property_type": "Modern Apartment",
                "bedrooms": 1,
                "bathrooms": 1,
                "area": 80,
                "amenities": ["WiFi", "Air Conditioning", "Study Room", "High-speed Internet"],
                "available_date": "2025-07-01",
                "description": "Modern 1-bedroom apartment in tech hub area with study room and high-speed internet",
                "landlord_id": "landlord_smart_001"
            }
        }
        
        self._start_scenario(scenario_config)
        
    def _start_scenario(self, scenario_config: Dict):
        """Start a rental scenario with given configuration"""
        try:
            response = requests.post(f"{self.api_base_url}/scenarios/simulate", json=scenario_config)
            if response.status_code == 200:
                result = response.json()
                conversation_id = result["result"]["conversation_id"]
                st.session_state.conversation_id = conversation_id
                st.session_state.conversation_active = True
                st.session_state.messages = []
                st.session_state.last_message_count = 0
                st.success(f"✅ Scenario started! Conversation ID: {conversation_id[:8]}")
                
                # Immediately fetch initial messages
                time.sleep(2)  # Wait for initial messages
                self._update_messages()
                st.rerun()
            else:
                st.error(f"Failed to start scenario: {response.text}")
        except Exception as e:
            st.error(f"Error starting scenario: {str(e)}")
            
    def _update_messages(self):
        """Update conversation messages from API"""
        if not st.session_state.conversation_id:
            return
            
        try:
            response = requests.get(f"{self.api_base_url}/conversations/{st.session_state.conversation_id}/messages")
            if response.status_code == 200:
                result = response.json()
                messages = result.get("messages", [])
                st.session_state.last_message_count = len(st.session_state.messages)
                st.session_state.messages = messages
            else:
                st.error(f"Failed to fetch messages: {response.text}")
        except Exception as e:
            st.error(f"Error fetching messages: {str(e)}")
            
    def _end_conversation(self):
        """End the current conversation"""
        if st.session_state.conversation_id:
            try:
                response = requests.delete(f"{self.api_base_url}/conversations/{st.session_state.conversation_id}")
                if response.status_code == 200:
                    st.success("✅ Conversation ended successfully")
                    st.session_state.conversation_active = False
                    st.session_state.conversation_id = None
                else:
                    st.error(f"Failed to end conversation: {response.text}")
            except Exception as e:
                st.error(f"Error ending conversation: {str(e)}")
                
    def _save_conversation(self):
        """Save conversation to local file"""
        if st.session_state.messages:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rental_conversation_{timestamp}.json"
            
            conversation_data = {
                "conversation_id": st.session_state.conversation_id,
                "timestamp": timestamp,
                "messages": st.session_state.messages
            }
            
            # In a real app, you would save to file or database
            st.success(f"💾 Conversation would be saved as {filename}")
            st.json(conversation_data)
            
    def _show_conversation_analysis(self):
        """Show conversation analysis"""
        if not st.session_state.messages:
            st.warning("No messages to analyze")
            return
            
        st.markdown("### 📊 Conversation Analysis")
        
        # Basic statistics
        message_count = len(st.session_state.messages)
        rounds = message_count // 3  # Approximate
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Messages", message_count)
        with col2:
            st.metric("Conversation Rounds", rounds)
        with col3:
            st.metric("Participants", len(set(msg.get("name", "") for msg in st.session_state.messages)))
            
        # Message distribution
        participants = {}
        for msg in st.session_state.messages:
            sender = msg.get("name", "Unknown")
            participants[sender] = participants.get(sender, 0) + 1
            
        st.markdown("#### Message Distribution")
        for sender, count in participants.items():
            st.write(f"- **{sender}**: {count} messages")
            
    def _create_demo_scenario(self):
        """Create a demo scenario quickly"""
        self._start_budget_scenario()
        
    def _clear_all_data(self):
        """Clear all session data"""
        st.session_state.clear()
        st.success("🗑️ All data cleared")
        st.rerun()
        
    def _check_api_health(self):
        """Check if API service is healthy"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


if __name__ == "__main__":
    demo = RentalAgentDemo()
    demo.run()
