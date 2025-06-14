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
            # 4. 开始协商对话 - 使用异步并发处理
            tasks = [self._start_negotiation_session(match) for match in matching_results]
            session_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤成功的会话
            for result in session_results:
                if isinstance(result, dict) and result is not None:
                    negotiation_sessions.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"创建协商会话时出错: {str(result)}")
            
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
            results = self.landlords_db.fetch_documents(0, {})  # 0 means no limit
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
    


    async def send_message_to_session(
        self, 
        session_id: str, 
        sender_id: str, 
        message: str,
        sender_type: str = "tenant",
        websocket_manager=None
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
            
            # 收集流式响应并实时推送
            full_response = ""
            response_chunks = []
            
            # 先推送开始响应的消息
            response_sender_type = "landlord" if sender_type == "tenant" else "tenant"
            response_sender_name = session["landlord_name"] if sender_type == "tenant" else session["tenant_name"]
            
            if websocket_manager:
                await websocket_manager.send_message_to_session(session_id, {
                    "type": "response_start",
                    "sender": response_sender_type,
                    "sender_name": response_sender_name,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # 流式收集响应并实时推送每个chunk
            async for chunk in response_generator:
                full_response += chunk
                response_chunks.append(chunk)
                
                # 实时推送每个chunk到前端
                if websocket_manager:
                    await websocket_manager.send_message_to_session(session_id, {
                        "type": "response_chunk",
                        "sender": response_sender_type,
                        "sender_name": response_sender_name,
                        "chunk": chunk,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # 推送响应完成消息
            if websocket_manager:
                await websocket_manager.send_message_to_session(session_id, {
                    "type": "response_complete",
                    "sender": response_sender_type,
                    "sender_name": response_sender_name,
                    "full_response": full_response,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
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
    
    async def _generate_tenant_message(self, session: Dict[str, Any]) -> Optional[str]:
        """让租客Agent根据对话历史自动生成消息"""
        try:
            # 获取对话历史
            messages = session.get("messages", [])
            
            # 获取租客信息
            tenant_id = session["tenant_id"]
            tenant = self._get_tenant_by_id(tenant_id)
            
            if not tenant:
                return None
            
            # 构建对话历史字符串
            conversation_history = ""
            for msg in messages[-8:]:  # 取最近8条消息保持上下文
                sender = "Tenant" if msg["sender_type"] == "tenant" else "Landlord"
                conversation_history += f"{sender}: {msg['message']}\n"
            
            # 如果是第一条消息，让租客自我介绍
            if not messages:
                property_address = session["property_address"]
                monthly_rent = session["monthly_rent"]
                
                intro_message = f"Hi, I'm {tenant.name}. I'm very interested in your property at {property_address}. "
                intro_message += f"I have an annual income of £{tenant.annual_income:,.0f}"
                if tenant.has_guarantor:
                    intro_message += " and I have a guarantor for additional security"
                intro_message += f". My budget is up to £{tenant.max_budget:,.0f} per month, and the rent of £{monthly_rent} fits well within my range. "
                intro_message += "Could you tell me more about the property details and viewing arrangements?"
                
                return intro_message
            
            # 使用租客Agent生成响应
            response_generator = get_tenant_streaming_response(
                messages=conversation_history,
                tenant_id=tenant_id,
                tenant_name=tenant.name,
                budget_info={
                    "annual_income": tenant.annual_income,
                    "max_budget": tenant.max_budget,
                    "has_guarantor": tenant.has_guarantor
                },
                preferences={
                    "min_bedrooms": tenant.min_bedrooms,
                    "max_bedrooms": tenant.max_bedrooms,
                    "preferred_locations": tenant.preferred_locations,
                    "is_student": tenant.is_student,
                    "has_pets": tenant.has_pets,
                    "is_smoker": tenant.is_smoker,
                    "num_occupants": tenant.num_occupants
                }
            )
            
            # 收集流式响应
            full_response = ""
            async for chunk in response_generator:
                full_response += chunk
            
            return full_response.strip() if full_response.strip() else None
            
        except Exception as e:
            logger.error(f"生成租客消息失败: {str(e)}")
            return None
    
    async def start_auto_negotiation_live(self, websocket_manager=None) -> Dict[str, Any]:
        """启动实时自动协商 - 通过WebSocket实时推送每一条消息，无轮次限制"""
        try:
            if not self.active_negotiations:
                return {"error": "没有活跃的协商会话"}
            
            if not websocket_manager:
                return {"error": "WebSocket管理器未提供"}
            
            logger.info("开始实时自动协商，无轮次限制")
            
            # 广播开始消息
            await websocket_manager.broadcast_to_all_sessions({
                "type": "auto_negotiation_start",
                "unlimited_rounds": True,
                "total_sessions": len(self.active_negotiations),
                "timestamp": datetime.now().isoformat()
            })
            
            # 持续对话，直到用户手动停止
            round_num = 0
            try:
                while True:  # 无限循环，持续对话
                    round_num += 1
                    logger.info(f"开始第 {round_num} 轮实时自动对话")
                    
                    # 广播轮次开始
                    await websocket_manager.broadcast_to_all_sessions({
                        "type": "round_start",
                        "round_number": round_num,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 对每个会话进行一次对话
                    for session_id, session in self.active_negotiations.items():
                        if session["status"] != "active":
                            continue
                        
                        # 租客继续对话
                        tenant_msg = await self._generate_tenant_message(session)
                        if tenant_msg:
                            # 推送租客消息到前端
                            await websocket_manager.send_message_to_session(session_id, {
                                "type": "tenant_message",
                                "sender": "tenant",
                                "sender_name": session["tenant_name"],
                                "message": tenant_msg,
                                "round": round_num,
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            # 发送消息并获取响应（这里会通过websocket实时推送房东的响应）
                            result = await self.send_message_to_session(
                                session_id=session_id,
                                sender_id=session["tenant_id"],
                                message=tenant_msg,
                                sender_type="tenant",
                                websocket_manager=websocket_manager
                            )
                            
                            if "error" in result:
                                # 推送错误信息
                                await websocket_manager.send_message_to_session(session_id, {
                                    "type": "error",
                                    "message": result["error"],
                                    "round": round_num,
                                    "timestamp": datetime.now().isoformat()
                                })
                    
                    # 广播轮次结束
                    await websocket_manager.broadcast_to_all_sessions({
                        "type": "round_complete",
                        "round_number": round_num,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 添加短暂延迟，避免过于频繁的消息
                    await asyncio.sleep(2)
                    
            except asyncio.CancelledError:
                # 处理取消事件 - 当用户停止自动对话时
                await websocket_manager.broadcast_to_all_sessions({
                    "type": "auto_negotiation_cancelled",
                    "completed_rounds": round_num,
                    "total_sessions": len(self.active_negotiations),
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "message": f"用户取消了自动协商，已完成 {round_num} 轮对话",
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

    def _get_property_by_id(self, property_id: str) -> Optional[PropertyModel]:
        """根据ID获取房产信息"""
        try:
            results = self.properties_db.fetch_documents(1, {"property_id": property_id})
            return results[0] if results else None
        except Exception as e:
            logger.error(f"获取房产失败: {str(e)}")
            return None