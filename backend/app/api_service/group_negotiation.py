"""
群体Agent沟通服务 - 实现租客寻找房东并协商的核心功能
"""

import asyncio
import uuid
import sys
from typing import List, Dict, Any, Optional, TypedDict
from datetime import datetime
from loguru import logger
import time

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# 确保日志配置正确，强制显示INFO级别消息
logger.remove()  # 移除默认处理器
logger.add(sys.stderr, level="INFO")  # 添加stderr处理器，设置级别为INFO

from app.mongo import MongoClientWrapper
from app.agents.models import LandlordModel, TenantModel, PropertyModel
from app.agents import AgentDataInitializer
from app.api_service.models import NegotiationStatusUpdate
from app.conversation_service.meta_controller import (
    MetaState,
    ExtendedMetaState,
    stream_conversation_with_state_update,
    meta_controller_graph,
)
from app.config import config

class GroupNegotiationService:
    """群体协商服务 - 管理多个租客与房东的匹配和协商"""

    def __init__(self, websocket_manager=None):
        self.landlords_db = MongoClientWrapper(
            model=LandlordModel, collection_name="landlords"
        )
        self.tenants_db = MongoClientWrapper(
            model=TenantModel, collection_name="tenants"
        )
        self.properties_db = MongoClientWrapper(
            model=PropertyModel, collection_name="properties"
        )

        # 活跃的协商会话 - 使用ExtendedMetaState来存储所有会话状态
        self.active_negotiations: Dict[str, ExtendedMetaState] = {}

        # WebSocket管理器，用于实时通信
        self.websocket_manager = websocket_manager

    async def create_negotiation_session(
        self, tenant: TenantModel, property_match: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new negotiation session between tenant and property owner

        Args:
            tenant: The tenant model
            property_match: The matched property with score and reasons

        Returns:
            Session metadata including ID and status
        """
        try:
            # 1. Get property and landlord details
            property_id = property_match.get("property_id")
            property_data = await self._get_property_by_id(property_id)
            if not property_data:
                logger.error(f"Cannot find property with ID {property_id}")
                return None

            landlord_id = property_data.landlord_id
            landlord = await self._get_landlord_by_id(landlord_id)
            if not landlord:
                logger.error(f"Cannot find landlord with ID {landlord_id}")
                return None

            # 2. Generate a unique session ID
            session_id = f"session_{uuid.uuid4().hex[:8]}_{int(time.time())}"

            # 3. Create initial state for meta controller
            initial_state: ExtendedMetaState = {
                "session_id": session_id,
                "messages": [],
                "active_agent": "tenant",  # Always start with tenant
                "tenant_data": tenant.model_dump(),
                "landlord_data": landlord.model_dump(),
                "property_data": property_data.model_dump(),
                "is_terminated": False,
                "termination_reason": "",
                # Extended state
                "match_score": property_match.get("score", 0),
                "match_reasons": property_match.get("reasons", []),
                "status": "active",
                "created_at": datetime.now().isoformat(),
            }

            # 4. Define message callback for logging and WebSocket communication
            async def message_callback(msg):
                # 详细记录对话内容
                role = msg.get("role", "unknown")
                active_agent = msg.get("active_agent", "unknown")
                content = msg.get("content", "")

                landlord_data = msg.get("landlord_data", {})
                landlord_name = landlord_data.get("name", "unknown landlord name")
                landlord_id = landlord_data.get("landlord_id", "unknown landlord ID")

                tenant_data = msg.get("tenant_data", {})
                tenant_name = tenant_data.get("name", "unknown tenant name")
                tenant_id = tenant_data.get("tenant_id", "unknown tenant ID")

                speaking_agent = "tenant" if active_agent == "landlord" else "landlord"
                speaking_name = (
                    tenant_name if speaking_agent == "tenant" else landlord_name
                )
                speaking_id = tenant_id if speaking_agent == "tenant" else landlord_id

                logger.info(
                    f"🗣️  [SESSION {session_id}] {speaking_agent, speaking_name} ({role}): {content}"
                )

                if self.websocket_manager:
                    websocket_message = {
                        "type": "message_sent",
                        "session_id": session_id,
                        "role": role,
                        "active_agent": speaking_agent,
                        "message": content,
                        "content": content,
                        "agent_type": speaking_agent,
                        "agent_name": speaking_name,
                        "agent_id": speaking_id,
                    }

                    try:
                        await self.websocket_manager.send_message_to_session(
                            session_id, websocket_message
                        )
                        logger.debug(
                            f"✅ Sent WebSocket message for session {session_id}: {speaking_name}"
                        )
                    except Exception as ws_error:
                        logger.error(
                            f"❌ Failed to send WebSocket message: {str(ws_error)}"
                        )
                else:
                    logger.warning(
                        f"WebSocket manager not available, cannot send message for session {session_id}"
                    )

            # 5. Define the actual negotiation coroutine
            async def run_negotiation():
                try:
                    async for msg in stream_conversation_with_state_update(
                        initial_state=initial_state,
                        callback_fn=message_callback,
                        graph=meta_controller_graph,
                    ):
                        await asyncio.sleep(5)  # Simulate async delay

                        # Messages are already added to initial_state in the stream function
                        # Additional monitoring/broadcasting logic could go here
                        pass
                    
                    # 🚀 After negotiation completion, one-click analysis and update all states
                    analysis_result = await self.analyze_and_update_rental_states(session_id)

                    logger.info(f"Session {session_id} analysis result: {analysis_result}")

                    # 发送对话结束事件
                    if self.websocket_manager:
                        end_message = {
                            "type": "dialogue_ended",
                            "session_id": session_id,
                            "reason": "completed",
                            "negotiation_result": analysis_result,
                            "timestamp": datetime.now().isoformat(),
                        }
                        await self.websocket_manager.send_message_to_session(
                            session_id, end_message
                        )

                    # Update status when complete
                    initial_state["status"] = "completed"
                    initial_state["analysis_result"] = analysis_result
                    logger.info(
                        f"Session {session_id} completed with {len(initial_state['messages'])} messages"
                    )

                except asyncio.CancelledError:
                    logger.info(f"Session {session_id} was cancelled")
                    initial_state["status"] = "cancelled"
                    initial_state["termination_reason"] = "manually_cancelled"

                except Exception as e:
                    logger.error(f"Error in session {session_id}: {str(e)}")
                    initial_state["status"] = "error"
                    initial_state["termination_reason"] = f"Error: {str(e)}"

            # 6. Create and store the task
            task = asyncio.create_task(run_negotiation())
            initial_state["task"] = task

            # 7. Store in active negotiations
            self.active_negotiations[session_id] = initial_state

            # 8. Return session metadata (without internal state)
            return {
                "session_id": session_id,
                "tenant_name": tenant.name,
                "landlord_name": landlord.name,
                "property_address": property_data.display_address,
                "monthly_rent": property_data.monthly_rent,
                "match_score": property_match.get("score", 0),
                "match_reasons": property_match.get("reasons", [])[:3],  # Top 3 reasons
                "status": "active",
                "created_at": initial_state["created_at"],
            }
        except Exception as e:
            logger.error(f"Failed to create negotiation session: {str(e)}")
            return None

    async def find_best_property_for_tenant(
        self, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        根据租客ID找到最适配的房产

        Args:
            tenant_id: 租客ID

        Returns:
            包含最佳匹配房产信息的字典，包括property_id、匹配分数和匹配原因
        """
        try:
            # 获取租客信息
            tenant = await self._get_tenant_by_id(tenant_id)
            if not tenant:
                logger.error(f"找不到租客: {tenant_id}")
                return None

            # 获取所有可用房产
            all_properties = await self._get_all_properties()
            if not all_properties:
                logger.error("没有可用房产")
                return None

            def calculate_property_match_score(
                tenant: TenantModel, property_dict: Dict[str, Any]
            ) -> tuple[float, List[str]]:
                """
                计算租客与房产的匹配分数

                Args:
                    tenant: 租客模型
                    property_dict: 房产信息字典

                Returns:
                    匹配分数(0-100)和匹配原因列表
                """
                score = 0
                reasons = []

                try:
                    # 预算匹配 (权重: 30分)
                    monthly_rent = property_dict.get("monthly_rent", 0)
                    if monthly_rent <= tenant.max_budget:
                        budget_ratio = (
                            monthly_rent / tenant.max_budget
                            if tenant.max_budget > 0
                            else 0
                        )
                        if budget_ratio <= 0.8:  # 租金不超过预算80%
                            score += 30
                            reasons.append(f"租金 ${monthly_rent} 在预算范围内")
                        elif budget_ratio <= 1.0:  # 租金在预算范围内但较高
                            score += 20
                            reasons.append(f"租金 ${monthly_rent} 接近预算上限")
                    else:
                        reasons.append(
                            f"租金 ${monthly_rent} 超出预算 ${tenant.max_budget}"
                        )

                    # 卧室数量匹配 (权重: 20分)
                    bedrooms = property_dict.get("bedrooms", 0)
                    if tenant.min_bedrooms <= bedrooms <= tenant.max_bedrooms:
                        score += 20
                        reasons.append(f"{bedrooms}房满足需求")
                    elif (
                        bedrooms == tenant.min_bedrooms - 1
                        or bedrooms == tenant.max_bedrooms + 1
                    ):
                        score += 10
                        reasons.append(f"{bedrooms}房接近需求")
                    else:
                        reasons.append(
                            f"{bedrooms}房不符合需求({tenant.min_bedrooms}-{tenant.max_bedrooms}房)"
                        )

                    # 地理位置匹配 (权重: 20分)
                    property_location = property_dict.get("district", "").lower()
                    if property_location and tenant.preferred_locations:
                        preferred_lower = [
                            loc.lower() for loc in tenant.preferred_locations
                        ]
                        if property_location in preferred_lower:
                            score += 20
                            reasons.append(f"位于偏好区域: {property_location}")
                        elif any(pref in property_location for pref in preferred_lower):
                            score += 10
                            reasons.append(f"位于相关区域: {property_location}")

                    # 宠物政策匹配 (权重: 10分)
                    pets_allowed = property_dict.get("pets_allowed", False)
                    if tenant.has_pets and pets_allowed:
                        score += 10
                        reasons.append("允许宠物")
                    elif not tenant.has_pets:
                        score += 5
                        reasons.append("无宠物限制影响")
                    elif tenant.has_pets and not pets_allowed:
                        reasons.append("不允许宠物")

                    # 吸烟政策匹配 (权重: 5分)
                    smoking_allowed = property_dict.get("smoking_allowed", False)
                    if tenant.is_smoker and smoking_allowed:
                        score += 5
                        reasons.append("允许吸烟")
                    elif not tenant.is_smoker:
                        score += 2
                        reasons.append("无吸烟限制影响")
                    elif tenant.is_smoker and not smoking_allowed:
                        reasons.append("不允许吸烟")

                    # 学生友好 (权重: 5分)
                    student_friendly = property_dict.get("student_friendly", True)
                    if tenant.is_student and student_friendly:
                        score += 5
                        reasons.append("学生友好")
                    elif not tenant.is_student:
                        score += 2
                        reasons.append("非学生无特殊限制")

                    # 房产类型偏好 (权重: 10分)
                    property_type = property_dict.get("property_type", "")
                    if property_type:
                        # 根据租客特征推断房产类型偏好
                        if tenant.is_student and property_type.lower() in [
                            "apartment",
                            "studio",
                        ]:
                            score += 10
                            reasons.append(f"适合学生的{property_type}")
                        elif tenant.num_occupants > 2 and property_type.lower() in [
                            "house",
                            "townhouse",
                        ]:
                            score += 10
                            reasons.append(f"适合多人居住的{property_type}")
                        elif property_type.lower() in ["apartment", "condo"]:
                            score += 5
                            reasons.append(f"常见房产类型: {property_type}")

                    # 额外设施加分
                    amenities = property_dict.get("amenities", [])
                    if amenities:
                        amenity_score = 0
                        if "parking" in amenities:
                            amenity_score += 2
                            reasons.append("包含停车位")
                        if "gym" in amenities or "fitness" in amenities:
                            amenity_score += 1
                            reasons.append("包含健身设施")
                        if "pool" in amenities:
                            amenity_score += 1
                            reasons.append("包含游泳池")
                        score += min(amenity_score, 5)  # 最多5分设施加分

                    # 确保分数在0-100范围内
                    score = max(0, min(100, score))

                    if not reasons:
                        reasons.append("基础匹配评估")

                    return score, reasons

                except Exception as e:
                    logger.error(f"计算匹配分数时出错: {str(e)}")
                    return 0, ["计算出错"]

            best_match = None
            best_score = 0

            for property_model in all_properties:
                # 将PropertyModel转换为字典以便计算
                property_dict = property_model.to_dict()
                # 计算匹配分数
                score, reasons = calculate_property_match_score(tenant, property_dict)

                if score > best_score:
                    best_score = score
                    property_dict = await self._get_property_by_id(
                        property_dict["property_id"]
                    )
                    property_dict = property_dict.to_dict()
                    best_match = {
                        "property_id": property_dict.get("property_id"),
                        "property": property_dict,
                        "score": score,
                        "reasons": reasons,
                        "landlord_id": property_dict.get("landlord_id"),
                        # "landlord_name": property_dict.get("landlord_name", "未知房东"),
                        "monthly_rent": property_dict.get("price", 0),
                        "display_address": property_dict.get(
                            "display_address", "未知地址"
                        ),
                    }

            if best_match:
                logger.info(
                    f"为租客 {tenant.name} 找到最佳匹配房产: {best_match['property_id']} (分数: {best_score})"
                )
                return best_match
            else:
                logger.warning(f"未找到适合租客 {tenant.name} 的房产")
                return None

        except Exception as e:
            logger.error(f"为租客 {tenant_id} 匹配房产时出错: {str(e)}")
            return None

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取协商会话信息"""
        session = self.active_negotiations.get(session_id)
        if not session:
            return None

        # 转换为前端友好的格式
        tenant_data = session.get("tenant_data", {})
        landlord_data = session.get("landlord_data", {})
        property_data = session.get("property_data", {})

        return {
            "session_id": session.get("session_id"),
            "tenant_name": tenant_data.get("name", "Unknown Tenant"),
            "landlord_name": landlord_data.get("name", "Unknown Landlord"),
            "property_address": property_data.get("display_address", "Unknown Address"),
            "monthly_rent": property_data.get("monthly_rent", 0),
            "match_score": session.get("match_score", 0),
            "match_reasons": session.get("match_reasons", []),
            "status": session.get("status", "unknown"),
            "created_at": session.get("created_at"),
            "is_terminated": session.get("is_terminated", False),
            "termination_reason": session.get("termination_reason", ""),
            "messages": session.get("messages", []),
        }

    async def get_all_active_sessions(self) -> List[Dict[str, Any]]:
        """获取所有活跃的协商会话"""
        formatted_sessions = []
        for session_id in self.active_negotiations:
            session_info = await self.get_session_info(session_id)
            if session_info:
                formatted_sessions.append(session_info)
        return formatted_sessions

    def get_negotiation_stats(self) -> Dict[str, Any]:
        """获取协商统计信息"""
        active_count = len(
            [s for s in self.active_negotiations.values() if s["status"] == "active"]
        )
        completed_count = len(
            [s for s in self.active_negotiations.values() if s["status"] == "completed"]
        )

        if not self.active_negotiations:
            return {"active_sessions": 0, "completed_sessions": 0}

        # 计算平均消息数
        total_messages = sum(
            len(session["messages"]) for session in self.active_negotiations.values()
        )
        avg_messages = (
            total_messages / len(self.active_negotiations)
            if self.active_negotiations
            else 0
        )

        # 计算平均匹配分数
        total_score = sum(
            session["match_score"] for session in self.active_negotiations.values()
        )
        avg_score = (
            total_score / len(self.active_negotiations)
            if self.active_negotiations
            else 0
        )

        return {
            "active_sessions": active_count,
            "completed_sessions": completed_count,
            "total_sessions": len(self.active_negotiations),
            "total_messages": total_messages,
            "average_messages_per_session": round(avg_messages, 2),
            "average_match_score": round(avg_score, 2),
        }

    async def _get_tenant_by_id(self, tenant_id: str) -> Optional[TenantModel]:
        """根据ID获取租客信息"""
        try:
            results = self.tenants_db.fetch_documents(1, {"tenant_id": tenant_id})
            return results[0] if results else None
        except Exception as e:
            logger.error(f"获取租客失败: {str(e)}")
            return None

    async def _get_landlord_by_id(self, landlord_id: str) -> Optional[LandlordModel]:
        """根据ID获取房东信息"""
        try:
            results = self.landlords_db.fetch_documents(1, {"landlord_id": landlord_id})
            return results[0] if results else None
        except Exception as e:
            logger.error(f"获取房东失败: {str(e)}")
            return None

    async def _get_property_by_id(self, property_id: str) -> Optional[PropertyModel]:
        """根据ID获取房产信息"""
        try:
            results = self.properties_db.fetch_documents(
                1, {"property_id": property_id}
            )
            return results[0] if results else None
        except Exception as e:
            logger.error(f"获取房产失败: {str(e)}")
            return None

    async def _get_all_tenants(self, limit: int = 0) -> List[TenantModel]:
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

    async def _get_all_properties(self) -> List[PropertyModel]:
        """获取所有房产"""
        try:
            results = self.properties_db.fetch_documents(0, {})  # 0 means no limit
            return results  # MongoDB client now returns Pydantic models directly
        except Exception as e:
            logger.error(f"获取房产失败: {str(e)}")
            return []

    async def analyze_and_update_rental_states(self, session_id: str) -> Dict[str, Any]:
        """
        🎯 Integrated negotiation analysis and status update function

        Input: session_id (contains complete conversation history)
        Output: RentalStatus, PropertyRentalStatus, LandlordRentalStatus
        Process: LLM analysis → generate status objects → update database
        """
        try:
            # 1. Get session data
            session = self.active_negotiations.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            messages = session.get("messages", [])
            if not messages:
                raise ValueError("No conversation messages available for analysis")

            # 2. Build LLM analysis context
            tenant_data = session.get("tenant_data", {})
            landlord_data = session.get("landlord_data", {})
            property_data = session.get("property_data", {})

            # 3. Format conversation history
            conversation_text = "\n".join(
                [
                    f"[{i+1}] {'Tenant' if 'tenant' in msg.get('role', '').lower() else 'Landlord'}: {msg.get('content', '')}"
                    for i, msg in enumerate(messages)
                ]
            )

            # 4. Build analysis context
            context = f"""
Tenant: {tenant_data.get('name', 'Unknown')} (ID: {tenant_data.get('tenant_id')}, Budget: £{tenant_data.get('max_budget', 0)})
Landlord: {landlord_data.get('name', 'Unknown')} (ID: {landlord_data.get('landlord_id')})
Property: {property_data.get('display_address', 'Unknown')} (ID: {property_data.get('property_id')}, Original Price: £{property_data.get('monthly_rent', 0)})
"""
            llm_config = config.llm.get("default", {})
            llm = ChatOpenAI(
                api_key=llm_config.api_key,
                model=llm_config.model,
                base_url=llm_config.base_url,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
            )

            # 🎯 Modified prompt to output structured JSON data directly
            prompt = ChatPromptTemplate.from_template(
                """
You are a rental negotiation analysis expert. Analyze the conversation and generate three rental status objects in JSON format.

Background Information:
{context}

Conversation History:
{conversation}

You need to output a JSON object containing the following fields:

{{
    "negotiation_successful": boolean,
    "confidence_score": 0.0-1.0,
    "tenant_rental_status": {{
        "is_rented": boolean,
        "property_id": string or null,
        "landlord_id": string or null,
        "rental_price": number or null,
        "rental_start_date": "YYYY-MM-DD" or null,
        "contract_duration_months": number or null,
        "negotiation_session_id": string,
        "last_updated": string
    }},
    "property_rental_status": {{
        "is_rented": boolean,
        "tenant_id": string or null,
        "rental_price": number or null,
        "rental_start_date": "YYYY-MM-DD" or null,
        "contract_duration_months": number or null,
        "negotiation_session_id": string,
        "last_updated": string
    }},
    "landlord_rental_status": {{
        "total_properties": number,
        "rented_properties": number,
        "available_properties": number,
        "total_rental_income": number,
        "average_rental_price": number,
        "last_updated": string
    }}
}}

Analysis Requirements:
1. Carefully determine if the conversation explicitly reached a rental agreement
2. Only set negotiation_successful to true when both parties clearly agree to rental terms
3. Extract accurate final rent price, start date, and contract duration
4. If negotiation failed, set all is_rented fields to false
5. confidence_score reflects your certainty in the analysis result
6. landlord_rental_status needs to be recalculated based on landlord's current properties

Please output strictly in JSON format without any additional text or explanations.
"""
            )

            # 6. Execute LLM analysis - using structured output to ensure correct format
            structured_llm = llm.with_structured_output(NegotiationStatusUpdate)
            chain = prompt | structured_llm

            current_time = datetime.now().isoformat()

            result = await chain.ainvoke(
                {"context": context, "conversation": conversation_text}
            )

            # 7. Supplement necessary ID and timestamp fields
            if result.negotiation_successful:
                # On success, ensure all association IDs are correct
                result.tenant_rental_status.property_id = property_data.get(
                    "property_id"
                )
                result.tenant_rental_status.landlord_id = landlord_data.get(
                    "landlord_id"
                )
                result.tenant_rental_status.negotiation_session_id = session_id
                result.tenant_rental_status.last_updated = current_time

                result.property_rental_status.tenant_id = tenant_data.get("tenant_id")
                result.property_rental_status.negotiation_session_id = session_id
                result.property_rental_status.last_updated = current_time
            else:
                # On failure, clear rental status but keep timestamps
                result.tenant_rental_status.is_rented = False
                result.tenant_rental_status.property_id = None
                result.tenant_rental_status.landlord_id = None
                result.tenant_rental_status.rental_price = None
                result.tenant_rental_status.last_updated = current_time

                result.property_rental_status.is_rented = False
                result.property_rental_status.tenant_id = None
                result.property_rental_status.rental_price = None
                result.property_rental_status.last_updated = current_time

            # Ensure landlord statistics timestamp
            result.landlord_rental_status.last_updated = current_time

            # 8. Update database - directly use model_dump() to convert to JSON
            tenant_id = tenant_data.get("tenant_id")
            property_id = property_data.get("property_id")
            landlord_id = landlord_data.get("landlord_id")

            update_success = True
            update_results = []

            # Update tenant status
            if tenant_id:
                try:
                    tenant_status_json = result.tenant_rental_status.model_dump()
                    self.tenants_db.update_document(
                        {"tenant_id": tenant_id},
                        {"$set": {"rental_status": tenant_status_json}},
                    )
                    update_results.append(f"✅ Tenant status updated: {tenant_id}")
                    logger.info(f"✅ Tenant status updated: {tenant_id}")
                except Exception as e:
                    error_msg = f"❌ Tenant status update failed: {str(e)}"
                    update_results.append(error_msg)
                    logger.error(error_msg)
                    update_success = False

            # Update property status
            if property_id:
                try:
                    property_status_json = result.property_rental_status.model_dump()
                    self.properties_db.update_document(
                        {"property_id": property_id},
                        {"$set": {"rental_status": property_status_json}},
                    )
                    update_results.append(f"✅ Property status updated: {property_id}")
                    logger.info(f"✅ Property status updated: {property_id}")
                except Exception as e:
                    error_msg = f"❌ Property status update failed: {str(e)}"
                    update_results.append(error_msg)
                    logger.error(error_msg)
                    update_success = False

            # Update landlord statistics
            if landlord_id:
                try:
                    landlord_stats_json = result.landlord_rental_status.model_dump()
                    self.landlords_db.update_document(
                        {"landlord_id": landlord_id},
                        {"$set": {"rental_stats": landlord_stats_json}},
                    )
                    update_results.append(
                        f"✅ Landlord statistics updated: {landlord_id}"
                    )
                    logger.info(f"✅ Landlord statistics updated: {landlord_id}")
                except Exception as e:
                    error_msg = f"❌ Landlord statistics update failed: {str(e)}"
                    update_results.append(error_msg)
                    logger.error(error_msg)
                    update_success = False

            # 9. Log analysis results
            logger.info(f"🎯 Negotiation analysis completed - Session {session_id}")
            logger.info(f"   Negotiation successful: {result.negotiation_successful}")
            logger.info(f"   Confidence score: {result.confidence_score:.2f}")

            if (
                result.negotiation_successful
                and result.tenant_rental_status.rental_price
            ):
                logger.info(
                    f"   Final rent: £{result.tenant_rental_status.rental_price}/month"
                )

            # 10. Return complete JSON format result
            return {
                "success": True,
                "session_id": session_id,
                "negotiation_successful": result.negotiation_successful,
                "confidence_score": result.confidence_score,
                "database_updated": update_success,
                "update_results": update_results,
                # 🎯 Return JSON format status objects directly - convenient for storage and transmission
                "tenant_rental_status": result.tenant_rental_status.model_dump(),
                "property_rental_status": result.property_rental_status.model_dump(),
                "landlord_rental_status": result.landlord_rental_status.model_dump(),
                "timestamp": current_time,
            }

        except Exception as e:
            logger.error(
                f"❌ Negotiation analysis failed - Session {session_id}: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }
