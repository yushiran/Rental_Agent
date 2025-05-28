from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseRentalAgent, AgentProfile, Property, MarketData
from loguru import logger


class TenantAgent(BaseRentalAgent):
    """租客Agent - 负责寻找合适房源并进行租房决策"""
    
    def __init__(
        self,
        name: str,
        llm_config: Dict[str, Any],
        budget: float,
        preferred_areas: List[str],
        requirements: Dict[str, Any],
        **kwargs
    ):
        profile = AgentProfile(
            name=name,
            role="租客",
            goals=[
                "在预算范围内找到满足需求的房源",
                "通过合理谈判获得最优租金",
                "确保租房条件符合个人要求"
            ],
            constraints=[
                f"预算上限: ¥{budget}",
                f"偏好区域: {', '.join(preferred_areas)}",
                "必须满足基本居住需求"
            ],
            capabilities=[
                "房源搜索与筛选",
                "价格谈判",
                "市场分析理解",
                "决策制定"
            ]
        )
        
        system_message = f"""You are a professional tenant assistant named {name}.

Role:
- You are looking for suitable rental property
- Budget limit: ¥{budget}/month
- Preferred areas: {', '.join(preferred_areas)}
- Requirements: {requirements}

Your objectives:
1. Find the most suitable property within budget
2. Negotiate reasonable rent through professional communication
3. Ensure property meets all necessary conditions

Communication style:
- Polite and professional
- Ask detailed questions about property (price, location, conditions)
- Make rational decisions based on market data
- Maintain reasonable position in negotiations
- If satisfied, say "I agree to this condition" or "I accept this price"
- If unsatisfied, clearly say "I cannot accept this" or "The price is too high"

Important: Do not mention house viewing, scheduling visits, or property tours. Make decisions based on property information directly.
Always remember your budget constraints and specific needs. Consider cost-effectiveness in all decisions.
"""
        
        super().__init__(
            name=name,
            profile=profile,
            llm_config=llm_config,
            system_message=system_message,
            **kwargs
        )
        
        self.budget = budget
        self.preferred_areas = preferred_areas
        self.requirements = requirements
        self.viewed_properties: List[Property] = []
        self.interested_properties: List[str] = []
        
    def evaluate_property(self, property_data: Property, market_data: MarketData) -> Dict:
        """评估房源是否符合要求"""
        evaluation = {
            "property_id": property_data.id,
            "meets_budget": property_data.price <= self.budget,
            "in_preferred_area": any(area.lower() in property_data.address.lower() 
                                   for area in self.preferred_areas),
            "meets_requirements": self._check_requirements(property_data),
            "market_value": self._assess_market_value(property_data, market_data),
            "overall_score": 0,
            "recommendation": ""
        }
        
        # 计算综合评分
        score = 0
        if evaluation["meets_budget"]:
            score += 30
        if evaluation["in_preferred_area"]:
            score += 25
        if evaluation["meets_requirements"]:
            score += 25
        if evaluation["market_value"] == "good_value":
            score += 20
            
        evaluation["overall_score"] = score
        
        if score >= 80:
            evaluation["recommendation"] = "强烈推荐"
        elif score >= 60:
            evaluation["recommendation"] = "值得考虑"
        else:
            evaluation["recommendation"] = "不推荐"
            
        self.log_interaction("property_evaluation", evaluation)
        return evaluation
        
    def _check_requirements(self, property_data: Property) -> bool:
        """检查房源是否满足基本要求"""
        if "min_bedrooms" in self.requirements:
            if property_data.bedrooms < self.requirements["min_bedrooms"]:
                return False
                
        if "min_bathrooms" in self.requirements:
            if property_data.bathrooms < self.requirements["min_bathrooms"]:
                return False
                
        if "required_amenities" in self.requirements:
            required = set(self.requirements["required_amenities"])
            available = set(property_data.amenities)
            if not required.issubset(available):
                return False
                
        return True
        
    def _assess_market_value(self, property_data: Property, market_data: MarketData) -> str:
        """评估房源市场价值"""
        if property_data.price < market_data.average_price * 0.9:
            return "excellent_value"
        elif property_data.price < market_data.average_price * 1.1:
            return "good_value"
        else:
            return "overpriced"
            
    def make_decision(self, context: Dict) -> Dict:
        """基于上下文做出租房决策"""
        if context["type"] == "property_viewing":
            property_data = context["property"]
            market_data = context["market_data"]
            evaluation = self.evaluate_property(property_data, market_data)
            
            if evaluation["overall_score"] >= 60:
                decision = {
                    "action": "interested",
                    "max_offer": min(self.budget, property_data.price * 0.95),
                    "conditions": self._generate_conditions(),
                    "reasoning": f"评分{evaluation['overall_score']}/100，{evaluation['recommendation']}"
                }
            else:
                decision = {
                    "action": "pass",
                    "reasoning": f"评分{evaluation['overall_score']}/100，不符合要求"
                }
                
        elif context["type"] == "negotiation":
            # 谈判决策逻辑
            current_price = context["current_price"]
            decision = self._negotiate_price(current_price, context)
            
        else:
            decision = {"action": "need_more_info"}
            
        self.log_interaction("decision_making", decision)
        return decision
        
    def _generate_conditions(self) -> List[str]:
        """生成租房条件"""
        conditions = []
        if "pet_friendly" in self.requirements and self.requirements["pet_friendly"]:
            conditions.append("允许饲养宠物")
        if "parking" in self.requirements and self.requirements["parking"]:
            conditions.append("提供停车位")
        return conditions
        
    def _negotiate_price(self, current_price: float, context: Dict) -> Dict:
        """价格谈判策略"""
        market_data = context.get("market_data")
        
        if current_price > self.budget:
            return {
                "action": "decline",
                "reasoning": "超出预算范围"
            }
            
        if market_data and current_price > market_data.average_price * 1.1:
            counter_offer = min(
                current_price * 0.9,
                market_data.average_price,
                self.budget
            )
            return {
                "action": "counter_offer",
                "price": counter_offer,
                "reasoning": f"基于市场平均价格¥{market_data.average_price}进行合理还价"
            }
            
        return {
            "action": "accept",
            "reasoning": "价格合理，符合市场行情"
        }
        
    def process_message(self, message: str, sender: str) -> str:
        """处理接收到的消息"""
        self.log_interaction("message_received", {
            "from": sender,
            "content": message
        })
        
        # 这里会被autogen的LLM处理，返回智能回复
        return message
