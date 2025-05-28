from typing import Dict, List, Any, Optional
from datetime import datetime

from .base import BaseRentalAgent, AgentProfile, Property, MarketData
from loguru import logger


class LandlordAgent(BaseRentalAgent):
    """房主Agent - 负责房源管理和租客筛选"""
    
    def __init__(
        self,
        name: str,
        llm_config: Dict[str, Any],
        properties: List[Property],
        pricing_strategy: str = "market_based",
        tenant_preferences: Dict[str, Any] = None,
        **kwargs
    ):
        profile = AgentProfile(
            name=name,
            role="房主",
            goals=[
                "以合理价格快速出租房源",
                "找到可靠的长期租客",
                "维护房产价值和收益"
            ],
            constraints=[
                "必须符合法律法规",
                "确保租客信用良好",
                "维护房产安全"
            ],
            capabilities=[
                "房源定价",
                "租客筛选",
                "合同谈判",
                "房产管理"
            ]
        )
        
        system_message = f"""You are a professional landlord named {name}.

Role:
- You own {len(properties)} properties for rent
- Pricing strategy: {pricing_strategy}
- Tenant preferences: {tenant_preferences or 'No special requirements'}

Your objectives:
1. Rent properties at reasonable market prices quickly
2. Find reliable long-term tenants
3. Maintain good landlord reputation through professional service

Communication style:
- Professional and friendly
- Provide detailed property information and advantages
- Use market data for reasonable pricing
- Willing to negotiate prices based on circumstances
- If deal is reached, say "Great, we have a deal" or "I agree to this condition"
- If unacceptable, say "Sorry, this price is too low"

Important: Do not mention house viewing, scheduling tours, or property visits. Focus on property information, price, and condition discussions.
Adjust strategy flexibly based on market conditions while ensuring reasonable rental income.
"""
        
        super().__init__(
            name=name,
            profile=profile,
            llm_config=llm_config,
            system_message=system_message,
            **kwargs
        )
        
        self.properties = {prop.id: prop for prop in properties}
        self.pricing_strategy = pricing_strategy
        self.tenant_preferences = tenant_preferences or {}
        self.rental_applications: List[Dict] = []
        self.tenant_inquiries: List[Dict] = []
        
    def set_property_price(self, property_id: str, market_data: MarketData) -> float:
        """基于市场数据设定房源价格"""
        if property_id not in self.properties:
            raise ValueError(f"Property {property_id} not found")
            
        property_data = self.properties[property_id]
        
        if self.pricing_strategy == "market_based":
            # 基于市场平均价格定价
            base_price = market_data.average_price
            
            # 根据房源特色调整价格
            adjustment_factor = 1.0
            
            # 面积调整
            if property_data.area > 100:
                adjustment_factor += 0.1
            elif property_data.area < 50:
                adjustment_factor -= 0.1
                
            # 设施调整
            premium_amenities = ["健身房", "游泳池", "停车位", "阳台"]
            amenity_bonus = len([a for a in property_data.amenities if a in premium_amenities]) * 0.05
            adjustment_factor += amenity_bonus
            
            # 市场趋势调整
            if market_data.price_trend == "increasing":
                adjustment_factor += 0.05
            elif market_data.price_trend == "decreasing":
                adjustment_factor -= 0.05
                
            suggested_price = base_price * adjustment_factor
            
        elif self.pricing_strategy == "competitive":
            # 略低于市场价格快速出租
            suggested_price = market_data.average_price * 0.95
            
        elif self.pricing_strategy == "premium":
            # 高于市场价格，突出房源优势
            suggested_price = market_data.average_price * 1.15
            
        else:
            suggested_price = market_data.average_price
            
        # 更新房源价格
        self.properties[property_id].price = suggested_price
        
        self.log_interaction("price_setting", {
            "property_id": property_id,
            "old_price": property_data.price,
            "new_price": suggested_price,
            "market_average": market_data.average_price,
            "strategy": self.pricing_strategy
        })
        
        return suggested_price
        
    def evaluate_tenant(self, tenant_info: Dict) -> Dict:
        """评估潜在租客"""
        evaluation = {
            "tenant_name": tenant_info.get("name", "未知"),
            "income_adequacy": False,
            "meets_preferences": True,
            "risk_level": "medium",
            "score": 0,
            "recommendation": ""
        }
        
        # 收入评估（租金不超过收入的30%）
        if "monthly_income" in tenant_info and "desired_rent" in tenant_info:
            income = tenant_info["monthly_income"]
            rent = tenant_info["desired_rent"]
            if income >= rent * 3.33:  # 收入至少是租金的3.33倍
                evaluation["income_adequacy"] = True
                evaluation["score"] += 40
                
        # 信用记录
        if tenant_info.get("credit_score", 0) >= 700:
            evaluation["score"] += 30
        elif tenant_info.get("credit_score", 0) >= 600:
            evaluation["score"] += 20
            
        # 租房历史
        if tenant_info.get("rental_history", []):
            good_references = sum(1 for ref in tenant_info["rental_history"] 
                                if ref.get("rating", 0) >= 4)
            evaluation["score"] += min(good_references * 10, 30)
            
        # 偏好匹配
        if self.tenant_preferences:
            if (self.tenant_preferences.get("no_pets", False) and 
                tenant_info.get("has_pets", False)):
                evaluation["meets_preferences"] = False
                evaluation["score"] -= 20
                
        # 风险评估
        if evaluation["score"] >= 80:
            evaluation["risk_level"] = "low"
            evaluation["recommendation"] = "推荐接受"
        elif evaluation["score"] >= 60:
            evaluation["risk_level"] = "medium"
            evaluation["recommendation"] = "可以考虑"
        else:
            evaluation["risk_level"] = "high"
            evaluation["recommendation"] = "不推荐"
            
        self.log_interaction("tenant_evaluation", evaluation)
        return evaluation
        
    def make_decision(self, context: Dict) -> Dict:
        """基于上下文做出决策"""
        if context["type"] == "rental_inquiry":
            # 处理租房咨询
            tenant_info = context["tenant_info"]
            property_id = context["property_id"]
            
            evaluation = self.evaluate_tenant(tenant_info)
            
            if evaluation["score"] >= 60:
                decision = {
                    "action": "invite_viewing",
                    "property_id": property_id,
                    "available_times": self._get_available_viewing_times(),
                    "additional_requirements": self._get_additional_requirements()
                }
            else:
                decision = {
                    "action": "decline_politely",
                    "reason": "暂时没有合适的房源匹配您的需求"
                }
                
        elif context["type"] == "price_negotiation":
            # 处理价格谈判
            decision = self._handle_price_negotiation(context)
            
        elif context["type"] == "application_review":
            # 审核租房申请
            decision = self._review_application(context)
            
        else:
            decision = {"action": "need_more_info"}
            
        self.log_interaction("decision_making", decision)
        return decision
        
    def _get_available_viewing_times(self) -> List[str]:
        """获取可看房时间"""
        return [
            "明天下午2-4点",
            "后天上午10-12点",
            "周末上午9-11点"
        ]
        
    def _get_additional_requirements(self) -> List[str]:
        """获取额外要求"""
        requirements = []
        if self.tenant_preferences.get("income_proof", True):
            requirements.append("请提供收入证明")
        if self.tenant_preferences.get("reference_check", True):
            requirements.append("请提供前房主推荐信")
        return requirements
        
    def _handle_price_negotiation(self, context: Dict) -> Dict:
        """处理价格谈判"""
        property_id = context["property_id"]
        offered_price = context["offered_price"]
        current_price = self.properties[property_id].price
        market_data = context.get("market_data")
        
        # 计算可接受的最低价格
        min_acceptable = current_price * 0.9
        if market_data and market_data.supply_level == "high":
            min_acceptable = current_price * 0.85
            
        if offered_price >= min_acceptable:
            return {
                "action": "accept_offer",
                "final_price": offered_price,
                "reasoning": "价格在可接受范围内"
            }
        elif offered_price >= current_price * 0.8:
            counter_price = (offered_price + current_price) / 2
            return {
                "action": "counter_offer",
                "counter_price": counter_price,
                "reasoning": f"愿意降价，但希望达到¥{counter_price}"
            }
        else:
            return {
                "action": "decline_offer",
                "reasoning": "价格低于成本底线，无法接受"
            }
            
    def _review_application(self, context: Dict) -> Dict:
        """审核租房申请"""
        application = context["application"]
        evaluation = self.evaluate_tenant(application["tenant_info"])
        
        if evaluation["score"] >= 70:
            return {
                "action": "approve_application",
                "lease_terms": self._generate_lease_terms(),
                "reasoning": f"申请人评分{evaluation['score']}/100，符合要求"
            }
        else:
            return {
                "action": "reject_application",
                "reasoning": f"申请人评分{evaluation['score']}/100，不符合要求"
            }
            
    def _generate_lease_terms(self) -> Dict:
        """生成租赁条款"""
        return {
            "lease_duration": "12个月",
            "deposit": "两个月租金",
            "payment_schedule": "每月1号前付款",
            "utilities": "租客承担",
            "maintenance": "房主负责大修，租客负责日常维护"
        }
        
    def process_message(self, message: str, sender: str) -> str:
        """处理接收到的消息"""
        self.log_interaction("message_received", {
            "from": sender,
            "content": message
        })
        
        # 这里会被autogen的LLM处理，返回智能回复
        return message
