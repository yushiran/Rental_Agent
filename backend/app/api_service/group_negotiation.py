"""
群体Agent沟通服务 - 实现租客寻找房东并协商的核心功能
"""
import asyncio
import uuid
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.mongo import MongoClientWrapper
from app.agents.models import LandlordModel, TenantModel, PropertyModel
from app.agents import AgentDataInitializer
from app.conversation_service.generate_response import (
    get_tenant_streaming_response,
    get_landlord_streaming_response
)


class GroupNegotiationService:
    """群体协商服务 - 管理多个租客与房东的匹配和协商"""
    
    def __init__(self):
        self.landlords_db = MongoClientWrapper(
            model=LandlordModel,
            collection_name="landlords"
        )
        self.tenants_db = MongoClientWrapper(
            model=TenantModel,
            collection_name="tenants"
        )
        self.properties_db = MongoClientWrapper(
            model=PropertyModel,
            collection_name="properties"
        )
        
        # 活跃的协商会话
        self.active_negotiations: Dict[str, Dict[str, Any]] = {}
        # 租客匹配状态
        self.tenant_matching: Dict[str, List[str]] = {}

        agent_factory = AgentDataInitializer()
        agent_factory.initialize_all_data()
    
    async def start_group_negotiation(self, max_tenants: int = 10) -> Dict[str, Any]:
        """
        启动群体协商：
        1. 获取所有租客
        2. 为每个租客找到匹配的房东
        3. 开始协商对话
        """
        try:
            logger.info("开始群体协商流程...")
            
            # 1. 获取所有租客
            tenants = await self._get_all_tenants(limit=max_tenants)
            if not tenants:
                return {"error": "没有找到租客数据"}
            
            # 2. 获取所有房东和房产
            landlords = await self._get_all_landlords()
            if not landlords:
                return {"error": "没有找到房东数据"}
            
            # 3. 为每个租客匹配适合的房东和房产
            matching_results = await self._match_tenants_to_landlords(tenants, landlords)
            
            # 4. 开始协商对话
            negotiation_sessions = []
            for match in matching_results:
                session = await self._start_negotiation_session(match)
                if session:
                    negotiation_sessions.append(session)
            
            logger.info(f"成功启动 {len(negotiation_sessions)} 个协商会话")
            
            return {
                "total_tenants": len(tenants),
                "total_landlords": len(landlords),
                "successful_matches": len(negotiation_sessions),
                "sessions": negotiation_sessions
            }
            
        except Exception as e:
            logger.error(f"群体协商启动失败: {str(e)}")
            return {"error": str(e)}
    
    async def _get_all_tenants(self, limit: int = 50) -> List[TenantModel]:
        """获取所有租客"""
        try:
            results = self.tenants_db.fetch_documents(limit, {})
            return results  # MongoDB client now returns Pydantic models directly
        except Exception as e:
            logger.error(f"获取租客失败: {str(e)}")
            return []
    
    async def _get_all_landlords(self) -> List[LandlordModel]:
        """获取所有房东"""
        try:
            results = self.landlords_db.fetch_documents(100, {})
            return results  # MongoDB client now returns Pydantic models directly
        except Exception as e:
            logger.error(f"获取房东失败: {str(e)}")
            return []
    
    async def _match_tenants_to_landlords(
        self, 
        tenants: List[TenantModel], 
        landlords: List[LandlordModel]
    ) -> List[Dict[str, Any]]:
        """为租客匹配合适的房东和房产"""
        matches = []
        
        for tenant in tenants:
            best_matches = self._find_best_properties_for_tenant(tenant, landlords)
            
            # 为每个租客选择最佳匹配
            if best_matches:
                top_match = best_matches[0]  # 选择最佳匹配
                matches.append({
                    "tenant": tenant,
                    "landlord": top_match["landlord"],
                    "property": top_match["property"],
                    "match_score": top_match["score"],
                    "match_reasons": top_match["reasons"]
                })
        
        logger.info(f"为 {len(matches)} 个租客找到了匹配的房东")
        return matches
    
    def _find_best_properties_for_tenant(
        self, 
        tenant: TenantModel, 
        landlords: List[LandlordModel]
    ) -> List[Dict[str, Any]]:
        """为单个租客找到最佳房产匹配"""
        potential_matches = []
        
        for landlord in landlords:
            for property_model in landlord.properties:
                # 使用租客模型的匹配方法
                match_result = tenant.matches_property_criteria(property_model)
                
                if match_result["matches"] and match_result["affordability"]:
                    potential_matches.append({
                        "landlord": landlord,
                        "property": property_model,
                        "score": match_result["score"],
                        "reasons": match_result["reasons"],
                        "distance": match_result.get("distance_to_preferred_km")
                    })
        
        # 按匹配分数排序
        potential_matches.sort(key=lambda x: x["score"], reverse=True)
        return potential_matches[:3]  # 返回前3个最佳匹配
    
    async def _start_negotiation_session(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """开始单个协商会话"""
        try:
            tenant = match["tenant"]
            landlord = match["landlord"]
            property_model = match["property"]
            
            session_id = str(uuid.uuid4())
            
            # 创建会话数据
            session_data = {
                "session_id": session_id,
                "tenant_id": tenant.tenant_id,
                "tenant_name": tenant.name,
                "landlord_id": landlord.landlord_id,
                "landlord_name": landlord.name,
                "property_id": property_model.property_id,
                "property_address": property_model.display_address,
                "monthly_rent": property_model.monthly_rent,
                "property": property_model.to_dict(),  # Store full property data
                "match_score": match["match_score"],
                "match_reasons": match["match_reasons"],
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "messages": []
            }
            
            # 保存到活跃协商
            self.active_negotiations[session_id] = session_data
            
            logger.info(f"创建协商会话 {session_id}: {tenant.name} <-> {landlord.name} (房产: {property_model.display_address})")
            
            return {
                "session_id": session_id,
                "tenant_name": tenant.name,
                "landlord_name": landlord.name,
                "property_address": property_model.display_address,
                "monthly_rent": property_model.monthly_rent,
                "match_score": match["match_score"]
            }
            
        except Exception as e:
            logger.error(f"创建协商会话失败: {str(e)}")
            return None
    
    def _get_tenant_by_id(self, tenant_id: str) -> Optional[TenantModel]:
        """根据ID获取租客信息"""
        try:
            results = self.tenants_db.fetch_documents(1, {"tenant_id": tenant_id})
            return results[0] if results else None
        except Exception as e:
            logger.error(f"获取租客失败: {str(e)}")
            return None
    
    def _get_landlord_by_id(self, landlord_id: str) -> Optional[LandlordModel]:
        """根据ID获取房东信息"""
        try:
            results = self.landlords_db.fetch_documents(1, {"landlord_id": landlord_id})
            return results[0] if results else None
        except Exception as e:
            logger.error(f"获取房东失败: {str(e)}")
            return None

    async def send_message_to_session(
        self, 
        session_id: str, 
        sender_id: str, 
        message: str,
        sender_type: str = "tenant"
    ) -> Dict[str, Any]:
        """向协商会话发送消息"""
        try:
            if session_id not in self.active_negotiations:
                return {"error": "协商会话不存在"}
            
            session = self.active_negotiations[session_id]
            
            # 添加消息到会话历史
            message_data = {
                "sender_id": sender_id,
                "sender_type": sender_type,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            session["messages"].append(message_data)
            
            # 根据发送者类型生成响应
            if sender_type == "tenant":
                # 租客发送消息，房东响应
                landlord = self._get_landlord_by_id(session["landlord_id"])
                response_generator = get_landlord_streaming_response(
                    messages=message,
                    landlord_id=session["landlord_id"],
                    landlord_name=landlord.name if landlord else "Unknown Landlord",
                    properties=[session.get("property", {})],
                    business_info={
                        "branch_name": landlord.branch_name if landlord else None,
                        "preferences": landlord.preferences if landlord else {}
                    }
                )
            else:
                # 房东发送消息，租客响应
                tenant = self._get_tenant_by_id(session["tenant_id"])
                response_generator = get_tenant_streaming_response(
                    messages=message,
                    tenant_id=session["tenant_id"],
                    tenant_name=tenant.name if tenant else "Unknown Tenant",
                    budget_info={
                        "annual_income": tenant.annual_income if tenant else 0,
                        "max_budget": tenant.max_budget if tenant else 0,
                        "has_guarantor": tenant.has_guarantor if tenant else False
                    },
                    preferences={
                        "min_bedrooms": tenant.min_bedrooms if tenant else 1,
                        "max_bedrooms": tenant.max_bedrooms if tenant else 3,
                        "preferred_locations": tenant.preferred_locations if tenant else [],
                        "is_student": tenant.is_student if tenant else False,
                        "has_pets": tenant.has_pets if tenant else False,
                        "is_smoker": tenant.is_smoker if tenant else False,
                        "num_occupants": tenant.num_occupants if tenant else 1
                    }
                )
            
            # 收集流式响应
            full_response = ""
            response_chunks = []
            async for chunk in response_generator:
                full_response += chunk
                response_chunks.append(chunk)
            
            # 添加响应到会话历史
            response_data = {
                "sender_id": session["landlord_id"] if sender_type == "tenant" else session["tenant_id"],
                "sender_type": "landlord" if sender_type == "tenant" else "tenant",
                "message": full_response,
                "timestamp": datetime.utcnow().isoformat()
            }
            session["messages"].append(response_data)
            
            return {
                "session_id": session_id,
                "response": full_response,
                "response_chunks": response_chunks,
                "message_count": len(session["messages"])
            }
            
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return {"error": str(e)}
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取协商会话信息"""
        return self.active_negotiations.get(session_id)
    
    async def get_all_active_sessions(self) -> List[Dict[str, Any]]:
        """获取所有活跃的协商会话"""
        return list(self.active_negotiations.values())
    
    async def simulate_tenant_interest(self, session_id: str) -> Dict[str, Any]:
        """模拟租客表达兴趣"""
        session = self.active_negotiations.get(session_id)
        if not session:
            return {"error": "会话不存在"}
        
        # 生成租客兴趣消息
        interest_message = f"Hi, I'm interested in your property at {session['property_address']}. The monthly rent of £{session['monthly_rent']} fits my budget. Could you tell me more about the viewing arrangements?"
        
        return await self.send_message_to_session(
            session_id=session_id,
            sender_id=session["tenant_id"],
            message=interest_message,
            sender_type="tenant"
        )
    
    async def simulate_all_tenant_interests(self) -> List[Dict[str, Any]]:
        """模拟所有租客表达兴趣"""
        results = []
        for session_id in self.active_negotiations.keys():
            result = await self.simulate_tenant_interest(session_id)
            results.append({
                "session_id": session_id,
                "result": result
            })
        return results
    
    async def _generate_tenant_follow_up(self, session: Dict[str, Any], round_num: int) -> Optional[str]:
        """生成租客的后续对话内容"""
        try:
            # 根据轮数和之前的对话生成不同的后续消息
            tenant_name = session["tenant_name"]
            property_address = session["property_address"]
            monthly_rent = session["monthly_rent"]
            
            # 获取之前的消息历史
            messages = session.get("messages", [])
            
            # 根据轮数生成不同类型的后续消息
            follow_up_templates = {
                1: [
                    f"Thank you for the information about {property_address}. Could you provide more details about the deposit requirements and any additional fees?",
                    f"I'm quite interested in proceeding. What would be the next steps for viewing the property?",
                    f"The property looks perfect for my needs. Are there any specific requirements for tenants that I should be aware of?"
                ],
                2: [
                    f"I appreciate your quick response. When would be the earliest possible move-in date for {property_address}?",
                    f"Could you clarify the lease terms? I'm looking for a long-term rental arrangement.",
                    f"Are utilities included in the £{monthly_rent} monthly rent, or would those be additional costs?"
                ],
                3: [
                    f"Everything sounds good so far. Could we schedule a viewing this week?",
                    f"I'd like to move forward with the application. What documents would you need from me?",
                    f"Is there any flexibility on the rent price given my strong rental history?"
                ]
            }
            
            # 如果轮数超出模板范围，生成通用消息
            if round_num not in follow_up_templates:
                return f"I'm still very interested in {property_address}. Could we discuss the final details to move forward?"
            
            # 随机选择一个模板
            templates = follow_up_templates[round_num]
            selected_message = random.choice(templates)
            
            return selected_message
            
        except Exception as e:
            logger.error(f"生成租客后续消息失败: {str(e)}")
            return None
    
    async def start_auto_negotiation(self, max_rounds: int = 5) -> Dict[str, Any]:
        """启动自动协商 - 让所有会话自动进行多轮对话"""
        try:
            if not self.active_negotiations:
                return {"error": "没有活跃的协商会话"}
            
            logger.info(f"开始自动协商，最大轮数: {max_rounds}")
            results = []
            
            # 首先让所有租客表达兴趣
            await self.simulate_all_tenant_interests()
            
            # 进行多轮自动对话
            for round_num in range(1, max_rounds):
                logger.info(f"开始第 {round_num} 轮自动对话")
                round_results = []
                
                for session_id, session in self.active_negotiations.items():
                    if session["status"] != "active":
                        continue
                    
                    # 租客继续对话
                    tenant_msg = await self._generate_tenant_follow_up(session, round_num)
                    if tenant_msg:
                        result = await self.send_message_to_session(
                            session_id=session_id,
                            sender_id=session["tenant_id"],
                            message=tenant_msg,
                            sender_type="tenant"
                        )
                        round_results.append({
                            "session_id": session_id,
                            "round": round_num,
                            "type": "tenant_message",
                            "result": result
                        })
                
                results.extend(round_results)
                # 在每轮之间稍作延迟
                await asyncio.sleep(1)
            
            return {
                "message": f"完成 {max_rounds-1} 轮自动协商",
                "total_sessions": len(self.active_negotiations),
                "total_exchanges": len(results)
            }
            
        except Exception as e:
            logger.error(f"自动协商失败: {str(e)}")
            return {"error": str(e)}
    
    async def start_auto_negotiation_live(self, max_rounds: int = 5, websocket_manager=None) -> Dict[str, Any]:
        """启动实时自动协商 - 通过WebSocket实时推送每一条消息"""
        try:
            if not self.active_negotiations:
                return {"error": "没有活跃的协商会话"}
            
            if not websocket_manager:
                return {"error": "WebSocket管理器未提供"}
            
            logger.info(f"开始实时自动协商，最大轮数: {max_rounds}")
            
            # 广播开始消息
            await websocket_manager.broadcast_to_all_sessions({
                "type": "auto_negotiation_start",
                "max_rounds": max_rounds,
                "total_sessions": len(self.active_negotiations),
                "timestamp": datetime.now().isoformat()
            })
            
            # 首先让所有租客表达兴趣
            await self._simulate_all_tenant_interests_live(websocket_manager)
            
            # 进行多轮自动对话
            for round_num in range(1, max_rounds):
                logger.info(f"开始第 {round_num} 轮实时自动对话")
                
                # 广播轮次开始
                await websocket_manager.broadcast_to_all_sessions({
                    "type": "round_start",
                    "round_number": round_num,
                    "timestamp": datetime.now().isoformat()
                })
                
                for session_id, session in self.active_negotiations.items():
                    if session["status"] != "active":
                        continue
                    
                    # 租客继续对话
                    tenant_msg = await self._generate_tenant_follow_up(session, round_num)
                    if tenant_msg:
                        # 先通过WebSocket推送租客将要发送的消息
                        await websocket_manager.send_message_to_session(session_id, {
                            "type": "tenant_message_start",
                            "sender": "tenant",
                            "sender_name": session["tenant_name"],
                            "message": tenant_msg,
                            "round": round_num,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # 发送消息并获取响应
                        result = await self.send_message_to_session(
                            session_id=session_id,
                            sender_id=session["tenant_id"],
                            message=tenant_msg,
                            sender_type="tenant"
                        )
                        
                        if "error" not in result:
                            # 推送房东的响应
                            await websocket_manager.send_message_to_session(session_id, {
                                "type": "landlord_response",
                                "sender": "landlord",
                                "sender_name": session["landlord_name"],
                                "response": result["response"],
                                "round": round_num,
                                "timestamp": datetime.now().isoformat()
                            })
                        else:
                            # 推送错误信息
                            await websocket_manager.send_message_to_session(session_id, {
                                "type": "error",
                                "message": result["error"],
                                "round": round_num,
                                "timestamp": datetime.now().isoformat()
                            })
                
                # 在每轮之间延迟，让用户看清楚
                await asyncio.sleep(2)
                
                # 广播轮次结束
                await websocket_manager.broadcast_to_all_sessions({
                    "type": "round_complete",
                    "round_number": round_num,
                    "timestamp": datetime.now().isoformat()
                })
            
            # 广播完成消息
            await websocket_manager.broadcast_to_all_sessions({
                "type": "auto_negotiation_complete",
                "completed_rounds": max_rounds - 1,
                "total_sessions": len(self.active_negotiations),
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "message": f"完成 {max_rounds-1} 轮实时自动协商",
                "total_sessions": len(self.active_negotiations),
                "method": "websocket_live"
            }
            
        except Exception as e:
            logger.error(f"实时自动协商失败: {str(e)}")
            # 广播错误消息
            if websocket_manager:
                await websocket_manager.broadcast_to_all_sessions({
                    "type": "auto_negotiation_error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
            return {"error": str(e)}
    
    async def _simulate_all_tenant_interests_live(self, websocket_manager):
        """实时模拟所有租客表达兴趣"""
        for session_id, session in self.active_negotiations.items():
            # 推送租客兴趣表达开始
            await websocket_manager.send_message_to_session(session_id, {
                "type": "tenant_interest_start",
                "sender": "tenant",
                "sender_name": session["tenant_name"],
                "timestamp": datetime.now().isoformat()
            })
            
            result = await self.simulate_tenant_interest(session_id)
            
            if "error" not in result:
                # 推送成功的兴趣表达
                await websocket_manager.send_message_to_session(session_id, {
                    "type": "tenant_interest_complete",
                    "tenant_message": result.get("tenant_message", ""),
                    "landlord_response": result.get("response", ""),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # 推送错误
                await websocket_manager.send_message_to_session(session_id, {
                    "type": "error",
                    "message": result["error"],
                    "timestamp": datetime.now().isoformat()
                })
            
            # 会话间延迟
            await asyncio.sleep(1)

    def get_negotiation_stats(self) -> Dict[str, Any]:
        """获取协商统计信息"""
        active_count = len(self.active_negotiations)
        
        if active_count == 0:
            return {"active_sessions": 0}
        
        # 计算平均消息数
        total_messages = sum(len(session["messages"]) for session in self.active_negotiations.values())
        avg_messages = total_messages / active_count if active_count > 0 else 0
        
        # 计算平均匹配分数
        total_score = sum(session["match_score"] for session in self.active_negotiations.values())
        avg_score = total_score / active_count if active_count > 0 else 0
        
        return {
            "active_sessions": active_count,
            "total_messages": total_messages,
            "average_messages_per_session": round(avg_messages, 2),
            "average_match_score": round(avg_score, 2)
        }
           