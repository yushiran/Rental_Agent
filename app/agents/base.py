from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from autogen import AssistantAgent, ConversableAgent
from loguru import logger


@dataclass
class AgentProfile:
    """Agent profile base class"""
    name: str
    role: str
    goals: List[str]
    constraints: List[str]
    capabilities: List[str]
    
    
@dataclass
class Property:
    """Property information"""
    id: str
    address: str
    price: float
    property_type: str
    bedrooms: int
    bathrooms: int
    area: float
    amenities: List[str]
    available_date: datetime
    description: str
    landlord_id: str
    
    
@dataclass
class MarketData:
    """Market data"""
    area: str
    average_price: float
    price_trend: str  # "increasing", "decreasing", "stable"
    supply_level: str  # "high", "medium", "low"
    demand_level: str  # "high", "medium", "low"
    recent_transactions: List[Dict]
    

class BaseRentalAgent(ConversableAgent):
    """Rental system base Agent class"""
    
    def __init__(
        self,
        name: str,
        profile: AgentProfile,
        llm_config: Dict[str, Any],
        system_message: str = "",
        **kwargs
    ):
        super().__init__(
            name=name,
            llm_config=llm_config,
            system_message=system_message,
            **kwargs
        )
        self.profile = profile
        self.memory: List[Dict] = []
        self.preferences: Dict = {}
        self.transaction_history: List[Dict] = []
        
    def log_interaction(self, interaction_type: str, data: Dict):
        """记录交互历史"""
        self.memory.append({
            "timestamp": datetime.now().isoformat(),
            "type": interaction_type,
            "data": data
        })
        logger.info(f"{self.name} - {interaction_type}: {data}")
        
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        recent_memory = self.memory[-5:] if len(self.memory) > 5 else self.memory
        return json.dumps(recent_memory, indent=2, ensure_ascii=False)
        
    @abstractmethod
    def make_decision(self, context: Dict) -> Dict:
        """基于上下文做出决策"""
        pass
        
    @abstractmethod
    def process_message(self, message: str, sender: str) -> str:
        """处理收到的消息"""
        pass
