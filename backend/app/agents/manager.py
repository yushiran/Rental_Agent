from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from uuid import uuid4

from autogen import GroupChat, GroupChatManager
from autogen.agentchat.conversable_agent import ConversableAgent
from loguru import logger

from .tenant import TenantAgent
from .landlord import LandlordAgent
from .market_analyst import MarketAnalystAgent
from .base import Property, MarketData


class CustomTerminationCondition:
    """自定义终止条件"""
    
    def __init__(self, max_rounds: int = 6):
        self.max_rounds = max_rounds
        self.round_count = 0
        self.agreement_keywords = [
            "agree", "accept", "deal", "yes", "ok", "agreed", "accepted", "sounds good",
            "i agree", "i accept", "we have a deal", "let's do it", "perfect", "excellent"
        ]
        self.rejection_keywords = [
            "reject", "refuse", "no", "decline", "disagree", "cannot accept", "too expensive", 
            "not interested", "pass", "no deal", "cannot agree", "not acceptable"
        ]
    
    def __call__(self, messages: List[Dict]) -> bool:
        """Check if conversation should be terminated"""
        # Check round limit
        current_round = len([msg for msg in messages if msg.get("name") != "System"]) // 3
        if current_round >= self.max_rounds:
            print(f"Conversation reached maximum rounds limit ({self.max_rounds}), auto-terminating")
            return True
            
        # Check if recent messages contain agreement or rejection keywords
        if len(messages) >= 2:
            recent_messages = messages[-2:]  # Check last two messages
            
            for msg in recent_messages:
                content = msg.get("content", "").lower()
                
                # Check for agreement
                if any(keyword in content for keyword in self.agreement_keywords):
                    print(f"Detected agreement keywords, terminating conversation")
                    return True
                    
                # Check for explicit rejection
                if any(keyword in content for keyword in self.rejection_keywords):
                    print(f"Detected rejection keywords, terminating conversation")
                    return True
                    
        return False


class RentalAgentManager:
    """Rental Agent Manager - Coordinates multi-agent interactions"""
    
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
        self.agents: Dict[str, Any] = {}
        self.active_conversations: Dict[str, GroupChat] = {}
        self.conversation_history: List[Dict] = []
        
    def create_tenant(
        self,
        name: str,
        budget: float,
        preferred_areas: List[str],
        requirements: Dict[str, Any]
    ) -> TenantAgent:
        """Create tenant agent"""
        tenant = TenantAgent(
            name=name,
            llm_config=self.llm_config,
            budget=budget,
            preferred_areas=preferred_areas,
            requirements=requirements
        )
        self.agents[name] = tenant
        logger.info(f"Created tenant agent: {name}")
        return tenant
        
    def create_landlord(
        self,
        name: str,
        properties: List[Property],
        pricing_strategy: str = "market_based",
        tenant_preferences: Dict[str, Any] = None
    ) -> LandlordAgent:
        """创建房主Agent"""
        landlord = LandlordAgent(
            name=name,
            llm_config=self.llm_config,
            properties=properties,
            pricing_strategy=pricing_strategy,
            tenant_preferences=tenant_preferences
        )
        self.agents[name] = landlord
        logger.info(f"Created landlord agent: {name}")
        return landlord
        
    def create_market_analyst(
        self,
        name: str = "MarketAnalyst",
        data_sources: List[str] = None
    ) -> MarketAnalystAgent:
        """创建市场分析师Agent"""
        analyst = MarketAnalystAgent(
            name=name,
            llm_config=self.llm_config,
            data_sources=data_sources
        )
        self.agents[name] = analyst
        logger.info(f"Created market analyst agent: {name}")
        return analyst
        
    def start_rental_conversation(
        self,
        tenant_name: str,
        landlord_name: str,
        analyst_name: str,
        property_id: str,
        max_rounds: int = 20
    ) -> str:
        """开始租房对话"""
        conversation_id = str(uuid4())
        
        # 获取参与的Agent
        tenant = self.agents.get(tenant_name)
        landlord = self.agents.get(landlord_name)
        analyst = self.agents.get(analyst_name)
        
        if not all([tenant, landlord, analyst]):
            raise ValueError("Required agents not found")
            
        # 获取房源信息
        if property_id not in landlord.properties:
            raise ValueError(f"Property {property_id} not found")
            
        property_data = landlord.properties[property_id]
        
        # 获取市场数据
        area = analyst._extract_area_from_address(property_data.address)
        market_data = analyst.get_market_analysis(area)
        
        # 创建群聊
        participants = [tenant, landlord, analyst]
        
        # 创建自定义终止条件
        termination_condition = CustomTerminationCondition(max_rounds=6)
        
        group_chat = GroupChat(
            agents=participants,
            messages=[],
            max_round=6,  # 设置最大轮数为6
            speaker_selection_method="auto"
        )
        
        # 将终止条件添加到GroupChat实例中
        group_chat.termination_condition = termination_condition
        
        self.active_conversations[conversation_id] = group_chat
        
        # 记录对话开始
        self.conversation_history.append({
            "conversation_id": conversation_id,
            "start_time": datetime.now().isoformat(),
            "participants": [tenant_name, landlord_name, analyst_name],
            "property_id": property_id,
            "status": "active"
        })
        
        # 自动启动对话，让agents开始交互
        try:
            # 初始化对话消息
            initial_message = f"""
Rental consultation conversation started:

Property Information:
- Address: {property_data.address}
- Price: ¥{property_data.price}/month
- Type: {property_data.property_type}
- Rooms: {property_data.bedrooms} bedroom(s), {property_data.bathrooms} bathroom(s)
- Area: {property_data.area} sqm
- Amenities: {', '.join(property_data.amenities)}

Market Situation:
- Area: {area}
- Average Price: ¥{market_data.average_price}/month
- Price Trend: {market_data.price_trend}
- Supply/Demand: Supply {market_data.supply_level}/Demand {market_data.demand_level}

Let's begin the discussion!
"""
            
            # 先将初始消息添加到对话中
            group_chat.messages.append({
                "role": "user",
                "content": initial_message,
                "name": "系统"
            })
            
            # 如果有有效的API密钥，尝试启动自动对话
            if self.llm_config.get("api_key") and "your-api" not in str(self.llm_config.get("api_key")):
                manager = self.get_conversation_manager(conversation_id)
                
                # 尝试启动一轮对话让agents开始互动
                try:
                    # 使用同步方法避免事件循环冲突
                    tenant.initiate_chat(
                        recipient=manager,
                        message="Hello everyone, I would like to learn more about this property.",
                        max_turns=2
                    )
                except Exception as e:
                    logger.warning(f"Failed to auto-start agent conversation: {e}")
            else:
                logger.info("No valid API key found, conversation created but agents won't auto-respond")
                
        except Exception as e:
            logger.warning(f"Error during conversation initialization: {e}")
            # 确保至少有初始消息
            if not group_chat.messages:
                group_chat.messages.append({
                    "role": "user", 
                    "content": initial_message,
                    "name": "系统"
                })
        
        logger.info(f"Started rental conversation: {conversation_id}")
        return conversation_id
        
    def get_conversation_manager(self, conversation_id: str) -> GroupChatManager:
        """获取对话管理器"""
        if conversation_id not in self.active_conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
            
        group_chat = self.active_conversations[conversation_id]
        
        # 创建带有终止条件的GroupChatManager
        manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=self.llm_config
        )
        
        # 如果有终止条件，检查是否应该终止
        if hasattr(group_chat, 'termination_condition'):
            termination_func = group_chat.termination_condition
            
            def is_termination_msg(message):
                """检查是否应该终止"""
                return termination_func(group_chat.messages)
                
            manager.is_termination_msg = is_termination_msg
            
        return manager
        
    def send_message(self, conversation_id: str, message: str, sender: str = "用户") -> str:
        """向对话发送消息"""
        if conversation_id not in self.active_conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
            
        group_chat = self.active_conversations[conversation_id]
        
        # 添加用户消息到对话历史
        group_chat.messages.append({
            "role": "user",
            "content": message,
            "name": sender
        })
        
        # 如果有有效的API密钥，尝试让agents响应
        if self.llm_config.get("api_key") and "your-api" not in str(self.llm_config.get("api_key")):
            try:
                manager = self.get_conversation_manager(conversation_id)
                
                # 选择第一个agent作为响应者
                responding_agent = group_chat.agents[0]
                
                # 触发一轮对话
                responding_agent.initiate_chat(
                    recipient=manager,
                    message=f"User said: {message}, please discuss and respond.",
                    max_turns=2
                )
                
                response = f"消息已发送，agents正在响应: {message}"
                logger.info(f"Message sent and agents responding to conversation {conversation_id}")
                return response
                
            except Exception as e:
                logger.error(f"Error triggering agent response: {e}")
                response = f"消息已添加到对话，但agents响应时出错: {message}"
                logger.info(f"Message sent to conversation {conversation_id}: {message}")
                return response
        else:
            # 没有有效API密钥时，只记录消息
            response = f"消息已添加到对话: {message} (注意：需要有效的API密钥才能让agents自动响应)"
            logger.info(f"Message sent to conversation {conversation_id}: {message}")
            return response
            
    def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """获取对话消息"""
        if conversation_id not in self.active_conversations:
            return []
            
        group_chat = self.active_conversations[conversation_id]
        return group_chat.messages
        
    def end_conversation(self, conversation_id: str) -> Dict:
        """结束对话"""
        if conversation_id not in self.active_conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
            
        # 更新对话状态
        for conv in self.conversation_history:
            if conv["conversation_id"] == conversation_id:
                conv["end_time"] = datetime.now().isoformat()
                conv["status"] = "completed"
                break
                
        # 移除活跃对话
        del self.active_conversations[conversation_id]
        
        logger.info(f"Ended conversation: {conversation_id}")
        return {"status": "conversation_ended", "conversation_id": conversation_id}
        
    def get_agent_info(self, agent_name: str) -> Dict:
        """获取Agent信息"""
        if agent_name not in self.agents:
            return {"error": "Agent not found"}
            
        agent = self.agents[agent_name]
        return {
            "name": agent.name,
            "role": agent.profile.role,
            "goals": agent.profile.goals,
            "capabilities": agent.profile.capabilities,
            "memory_entries": len(agent.memory)
        }
        
    def get_all_conversations(self) -> List[Dict]:
        """获取所有对话历史"""
        return self.conversation_history
        
    def simulate_rental_scenario(
        self,
        scenario_config: Dict[str, Any]
    ) -> Dict:
        """模拟租房场景"""
        scenario_id = str(uuid4())
        
        # 解析场景配置
        tenant_config = scenario_config["tenant"]
        landlord_config = scenario_config["landlord"]
        property_config = scenario_config["property"]
        
        # 创建房源
        property_config_copy = property_config.copy()
        
        # 处理日期字符串转换
        if isinstance(property_config_copy.get("available_date"), str):
            from datetime import datetime
            property_config_copy["available_date"] = datetime.fromisoformat(property_config_copy["available_date"])
        
        property_data = Property(**property_config_copy)
        
        # 创建Agent
        tenant = self.create_tenant(**tenant_config)
        landlord = self.create_landlord(
            **landlord_config,
            properties=[property_data]
        )
        analyst = self.create_market_analyst()
        
        # 开始对话
        conversation_id = self.start_rental_conversation(
            tenant.name,
            landlord.name,
            analyst.name,
            property_data.id
        )
        
        return {
            "scenario_id": scenario_id,
            "conversation_id": conversation_id,
            "tenant_name": tenant.name,
            "landlord_name": landlord.name,
            "analyst_name": analyst.name,
            "property_id": property_data.id
        }
