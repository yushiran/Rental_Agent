from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import statistics
import random

from .base import BaseRentalAgent, AgentProfile, Property, MarketData
from loguru import logger


class MarketAnalystAgent(BaseRentalAgent):
    """Market Analyst Agent - Responsible for market data analysis and trend forecasting"""
    
    def __init__(
        self,
        name: str,
        llm_config: Dict[str, Any],
        data_sources: List[str] = None,
        **kwargs
    ):
        profile = AgentProfile(
            name=name,
            role="Market Analyst",
            goals=[
                "Provide accurate market data analysis",
                "Predict real estate market trends", 
                "Offer pricing recommendations for tenants and landlords"
            ],
            constraints=[
                "Base analysis on real data",
                "Maintain objective and neutral stance",
                "Keep market information updated"
            ],
            capabilities=[
                "Data analysis",
                "Trend forecasting",
                "Price recommendations",
                "Market report generation"
            ]
        )
        
        system_message = f"""You are a professional real estate market analyst named {name}.

Role:
- You have extensive experience in real estate market analysis
- Expert in data analysis and trend forecasting
- Provide objective market advice for tenants and landlords

Your expertise:
1. Analyze real estate market price trends
2. Assess supply and demand relationships in different areas
3. Provide data-driven pricing recommendations
4. Forecast future market directions

Communication style:
- Professional and objective
- Use data to support viewpoints
- Provide specific numbers and analysis
- Remain neutral, not favoring any party

You will provide fair and professional advice to all participants based on the latest market data.
"""
        
        super().__init__(
            name=name,
            profile=profile,
            llm_config=llm_config,
            system_message=system_message,
            **kwargs
        )
        
        self.data_sources = data_sources or ["rightmove", "zoopla", "local_agents"]
        self.market_cache: Dict[str, MarketData] = {}
        self.price_history: Dict[str, List[Dict]] = {}
        self.last_update = datetime.now()
        
        # Initialize simulated market data
        self._initialize_market_data()
        
    def _initialize_market_data(self):
        """Initialize simulated market data"""
        areas = ["City_Center", "East_District", "West_District", "South_District", "North_District", "Development_Zone"]
        
        for area in areas:
            # Generate base price data
            base_price = random.uniform(3000, 8000)
            price_trend = random.choice(["increasing", "decreasing", "stable"])
            supply_level = random.choice(["high", "medium", "low"])
            demand_level = random.choice(["high", "medium", "low"])
            
            # Generate historical transaction data
            transactions = []
            for i in range(10):
                date = datetime.now() - timedelta(days=i*30)
                price_variation = random.uniform(0.9, 1.1)
                transactions.append({
                    "date": date.isoformat(),
                    "price": base_price * price_variation,
                    "property_type": random.choice(["1-bedroom", "2-bedroom", "3-bedroom", "4-bedroom"]),
                    "area": area
                })
                
            market_data = MarketData(
                area=area,
                average_price=base_price,
                price_trend=price_trend,
                supply_level=supply_level,
                demand_level=demand_level,
                recent_transactions=transactions
            )
            
            self.market_cache[area] = market_data
            self.price_history[area] = transactions
            
    def get_market_analysis(self, area: str) -> MarketData:
        """获取指定区域的市场分析"""
        if area not in self.market_cache:
            # 如果没有数据，创建默认数据
            self._initialize_area_data(area)
            
        market_data = self.market_cache[area]
        
        self.log_interaction("market_analysis_request", {
            "area": area,
            "average_price": market_data.average_price,
            "trend": market_data.price_trend
        })
        
        return market_data
        
    def _initialize_area_data(self, area: str):
        """为新区域初始化数据"""
        base_price = random.uniform(3000, 8000)
        market_data = MarketData(
            area=area,
            average_price=base_price,
            price_trend=random.choice(["increasing", "decreasing", "stable"]),
            supply_level=random.choice(["high", "medium", "low"]),
            demand_level=random.choice(["high", "medium", "low"]),
            recent_transactions=[]
        )
        self.market_cache[area] = market_data
        
    def analyze_property_value(self, property_data: Property) -> Dict:
        """分析房源价值"""
        # 提取区域信息
        area = self._extract_area_from_address(property_data.address)
        market_data = self.get_market_analysis(area)
        
        # 计算房源相对市场价值
        price_ratio = property_data.price / market_data.average_price
        
        if price_ratio < 0.8:
            value_assessment = "低于市场价，性价比很高"
            recommendation = "强烈推荐"
        elif price_ratio < 1.0:
            value_assessment = "略低于市场价，较好选择"
            recommendation = "推荐"
        elif price_ratio < 1.2:
            value_assessment = "略高于市场价，需要考虑"
            recommendation = "谨慎考虑"
        else:
            value_assessment = "明显高于市场价"
            recommendation = "不推荐"
            
        # 分析房源特色价值
        feature_score = self._calculate_feature_score(property_data)
        
        analysis = {
            "property_id": property_data.id,
            "market_price": market_data.average_price,
            "listed_price": property_data.price,
            "price_ratio": price_ratio,
            "value_assessment": value_assessment,
            "recommendation": recommendation,
            "feature_score": feature_score,
            "market_trend": market_data.price_trend,
            "supply_demand": f"供应{market_data.supply_level}/需求{market_data.demand_level}",
            "analysis_date": datetime.now().isoformat()
        }
        
        self.log_interaction("property_analysis", analysis)
        return analysis
        
    def _extract_area_from_address(self, address: str) -> str:
        """从地址中提取区域信息"""
        areas = list(self.market_cache.keys())
        for area in areas:
            if area in address:
                return area
        return "其他区域"
        
    def _calculate_feature_score(self, property_data: Property) -> int:
        """计算房源特色评分"""
        score = 50  # 基础分
        
        # 面积加分
        if property_data.area > 100:
            score += 20
        elif property_data.area > 80:
            score += 10
        elif property_data.area < 40:
            score -= 10
            
        # 设施加分
        premium_amenities = ["健身房", "游泳池", "停车位", "阳台", "花园"]
        amenity_score = len([a for a in property_data.amenities if a in premium_amenities]) * 5
        score += amenity_score
        
        # 房间数量
        if property_data.bedrooms >= 3:
            score += 10
        if property_data.bathrooms >= 2:
            score += 5
            
        return min(100, max(0, score))
        
    def generate_market_report(self, areas: List[str] = None) -> Dict:
        """生成市场报告"""
        if areas is None:
            areas = list(self.market_cache.keys())
            
        report = {
            "report_date": datetime.now().isoformat(),
            "areas_analyzed": areas,
            "market_summary": {},
            "price_trends": {},
            "recommendations": {}
        }
        
        all_prices = []
        trend_analysis = {"increasing": 0, "decreasing": 0, "stable": 0}
        
        for area in areas:
            if area in self.market_cache:
                market_data = self.market_cache[area]
                all_prices.append(market_data.average_price)
                trend_analysis[market_data.price_trend] += 1
                
                report["price_trends"][area] = {
                    "average_price": market_data.average_price,
                    "trend": market_data.price_trend,
                    "supply_demand": f"{market_data.supply_level}/{market_data.demand_level}"
                }
                
        # 整体市场摘要
        if all_prices:
            report["market_summary"] = {
                "overall_average": statistics.mean(all_prices),
                "price_range": f"¥{min(all_prices):.0f} - ¥{max(all_prices):.0f}",
                "market_activity": self._assess_market_activity(trend_analysis)
            }
            
        # 投资建议
        report["recommendations"] = self._generate_investment_advice(report)
        
        self.log_interaction("market_report_generated", {
            "areas_count": len(areas),
            "overall_average": report["market_summary"].get("overall_average", 0)
        })
        
        return report
        
    def _assess_market_activity(self, trend_analysis: Dict) -> str:
        """评估市场活跃度"""
        total = sum(trend_analysis.values())
        if trend_analysis["increasing"] / total > 0.6:
            return "市场活跃，价格上涨趋势明显"
        elif trend_analysis["decreasing"] / total > 0.6:
            return "市场降温，价格下降趋势明显"
        else:
            return "市场平稳，价格变化温和"
            
    def _generate_investment_advice(self, report: Dict) -> Dict:
        """生成投资建议"""
        advice = {
            "for_landlords": [],
            "for_tenants": [],
            "market_outlook": ""
        }
        
        # 基于市场活跃度给出建议
        market_activity = report["market_summary"].get("market_activity", "")
        
        if "上涨" in market_activity:
            advice["for_landlords"].append("适当提高租金，市场接受度较高")
            advice["for_tenants"].append("建议尽快决策，避免价格进一步上涨")
            advice["market_outlook"] = "市场向好，租金有上涨空间"
        elif "下降" in market_activity:
            advice["for_landlords"].append("适当降低租金，提高竞争力")
            advice["for_tenants"].append("耐心等待，可能获得更好价格")
            advice["market_outlook"] = "市场调整期，租金有下降压力"
        else:
            advice["for_landlords"].append("维持现有价格策略")
            advice["for_tenants"].append("正常决策，市场价格稳定")
            advice["market_outlook"] = "市场平稳，价格相对稳定"
            
        return advice
        
    def make_decision(self, context: Dict) -> Dict:
        """基于上下文做出分析决策"""
        if context["type"] == "price_analysis":
            property_data = context["property"]
            analysis = self.analyze_property_value(property_data)
            return {
                "action": "provide_analysis",
                "analysis": analysis
            }
            
        elif context["type"] == "market_inquiry":
            area = context["area"]
            market_data = self.get_market_analysis(area)
            return {
                "action": "provide_market_data",
                "data": market_data
            }
            
        elif context["type"] == "trend_forecast":
            areas = context.get("areas", list(self.market_cache.keys()))
            report = self.generate_market_report(areas)
            return {
                "action": "provide_forecast",
                "report": report
            }
            
        else:
            return {"action": "need_more_info"}
            
    def update_market_data(self, new_transaction: Dict):
        """更新市场数据"""
        area = new_transaction.get("area")
        if area and area in self.market_cache:
            # 添加新交易到历史记录
            self.price_history[area].append(new_transaction)
            
            # 重新计算平均价格
            recent_prices = [t["price"] for t in self.price_history[area][-20:]]
            new_average = statistics.mean(recent_prices)
            
            # 更新市场数据
            self.market_cache[area].average_price = new_average
            self.market_cache[area].recent_transactions.append(new_transaction)
            
            self.log_interaction("market_data_update", {
                "area": area,
                "new_average": new_average,
                "transaction_count": len(self.price_history[area])
            })
            
    def process_message(self, message: str, sender: str) -> str:
        """处理接收到的消息"""
        self.log_interaction("message_received", {
            "from": sender,
            "content": message
        })
        
        # 这里会被autogen的LLM处理，返回智能回复
        return message
