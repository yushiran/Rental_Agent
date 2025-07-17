import json
import os
from datetime import datetime
from typing import Dict, Any
from loguru import logger
from app.conversation_service.meta_controller import (
    MetaState,
    ExtendedMetaState,
    stream_conversation_with_state_update,
    meta_controller_graph,
)

async def save_conversation_history(
    session_id: str, session_state: ExtendedMetaState, analysis_result: Dict[str, Any]
) -> None:
    """
    保存对话历史到 workspace/history 文件夹
    
    Args:
        session_id: 会话ID
        session_state: 会话状态
        analysis_result: 分析结果
    """
    try:
        # 创建 workspace/history 目录
        history_dir = os.path.join("workspace", "history")
        os.makedirs(history_dir, exist_ok=True)
        
        # 获取参与者信息
        tenant_data = session_state.get("tenant_data", {})
        landlord_data = session_state.get("landlord_data", {})
        property_data = session_state.get("property_data", {})
        messages = session_state.get("messages", [])
        
        # 构建保存的对话记录
        conversation_log = {
            "session_info": {
                "session_id": session_id,
                "created_at": session_state.get("created_at", datetime.now().isoformat()),
                "completed_at": datetime.now().isoformat(),
                "status": session_state.get("status", "unknown"),
                "termination_reason": session_state.get("termination_reason", ""),
                "match_score": session_state.get("match_score", 0),
                "match_reasons": session_state.get("match_reasons", [])
            },
            
            "participants": {
                "tenant": {
                    "tenant_id": tenant_data.get("tenant_id", "unknown"),
                    "name": tenant_data.get("name", "Unknown Tenant"),
                    "email": tenant_data.get("email", ""),
                    "phone": tenant_data.get("phone", ""),
                    "annual_income": tenant_data.get("annual_income", 0),
                    "max_budget": tenant_data.get("max_budget", 0),
                    "min_bedrooms": tenant_data.get("min_bedrooms", 0),
                    "max_bedrooms": tenant_data.get("max_bedrooms", 0),
                    "preferred_locations": tenant_data.get("preferred_locations", []),
                    "is_student": tenant_data.get("is_student", False),
                    "has_pets": tenant_data.get("has_pets", False),
                    "is_smoker": tenant_data.get("is_smoker", False),
                    "num_occupants": tenant_data.get("num_occupants", 1)
                },
                
                "landlord": {
                    "landlord_id": landlord_data.get("landlord_id", "unknown"),
                    "name": landlord_data.get("name", "Unknown Landlord"),
                    "phone": landlord_data.get("phone", ""),
                    "branch_name": landlord_data.get("branch_name", ""),
                    "preferences": landlord_data.get("preferences", {})
                },
                
                "property": {
                    "property_id": property_data.get("property_id", "unknown"),
                    "display_address": property_data.get("display_address", "Unknown Address"),
                    "monthly_rent": property_data.get("monthly_rent", 0),
                    "bedrooms": property_data.get("bedrooms", 0),
                    "bathrooms": property_data.get("bathrooms", 0),
                    "property_type": property_data.get("property_type", ""),
                    "district": property_data.get("district", ""),
                    "pets_allowed": property_data.get("pets_allowed", False),
                    "smoking_allowed": property_data.get("smoking_allowed", False),
                    "student_friendly": property_data.get("student_friendly", True),
                    "amenities": property_data.get("amenities", [])
                }
            },
            
            "conversation_history": [],
            
            "analysis_result": analysis_result
        }
        
        # 格式化对话历史
        for i, msg in enumerate(messages):
            # 安全地获取消息内容
            if isinstance(msg, dict):
                content = msg.get("content", "")
                role = msg.get("role", "unknown")
                timestamp = msg.get("timestamp", "")
            elif hasattr(msg, 'content'):
                content = msg.content
                role = msg.__class__.__name__.lower().replace('message', '')
                timestamp = ""
            else:
                content = str(msg)
                role = "unknown"
                timestamp = ""
            
            # 判断发言者
            if i % 2 == 0:  # 偶数索引为租客
                speaker = "tenant"
                speaker_name = tenant_data.get("name", "Unknown Tenant")
            else:  # 奇数索引为房东
                speaker = "landlord"
                speaker_name = landlord_data.get("name", "Unknown Landlord")
            
            conversation_log["conversation_history"].append({
                "turn": i + 1,
                "speaker": speaker,
                "speaker_name": speaker_name,
                "role": role,
                "content": content,
                "timestamp": timestamp if timestamp else datetime.now().isoformat()
            })
        
        # 添加统计信息
        conversation_log["statistics"] = {
            "total_messages": len(messages),
            "tenant_messages": len([m for i, m in enumerate(messages) if i % 2 == 0]),
            "landlord_messages": len([m for i, m in enumerate(messages) if i % 2 == 1]),
            "conversation_duration_estimate": f"{len(messages) * 2} minutes",  # 假设每条消息2分钟
            "negotiation_successful": analysis_result.get("negotiation_successful", False),
            "confidence_score": analysis_result.get("confidence_score", 0)
        }
        
        # 生成文件名和路径
        filename = f"{session_id}.json"
        file_path = os.path.join(history_dir, filename)
        
        # 保存到JSON文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_log, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📁 Conversation history saved: {file_path}")
        logger.info(f"   - Session: {session_id}")
        logger.info(f"   - Participants: {tenant_data.get('name', 'Unknown')} ↔ {landlord_data.get('name', 'Unknown')}")
        logger.info(f"   - Messages: {len(messages)}")
        logger.info(f"   - Property: {property_data.get('display_address', 'Unknown')}")
        logger.info(f"   - Result: {'Success' if analysis_result.get('negotiation_successful', False) else 'Failed'}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save conversation history for session {session_id}: {str(e)}")
        logger.error(f"   Error details: {e}")
