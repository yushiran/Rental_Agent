from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode

from app.conversation_service.tenant_workflow import (
    get_tenant_agent_chain,
    get_property_matching_chain,
    get_viewing_feedback_analysis_chain,
    get_rental_conversation_summary_chain,
)
from app.conversation_service.tenant_workflow import TenantState
from app.conversation_service import tools
from app.config import config

retriever_node = ToolNode(tools)


async def tenant_agent_node(state: TenantState, config: RunnableConfig):
    """Handle tenant agent conversations"""
    summary = state.get("summary", "")
    tenant_chain = get_tenant_agent_chain()

    response = await tenant_chain.ainvoke(
        {
            "messages": state["messages"],
            "tenant_id": state.get("tenant_id", ""),
            "tenant_name": state.get("tenant_name", ""),
            "email": state.get("email", ""),
            "phone": state.get("phone", ""),
            "annual_income": state.get("annual_income", 0),
            "has_guarantor": state.get("has_guarantor", False),
            "max_budget": state.get("max_budget", 0),
            "min_bedrooms": state.get("min_bedrooms", 1),
            "max_bedrooms": state.get("max_bedrooms", 3),
            "preferred_locations": state.get("preferred_locations", []),
            "is_student": state.get("is_student", False),
            "has_pets": state.get("has_pets", False),
            "is_smoker": state.get("is_smoker", False),
            "num_occupants": state.get("num_occupants", 1),
            "conversation_context": state.get("conversation_context", ""),
            "search_criteria": state.get("search_criteria", {}),
            "viewed_properties": state.get("viewed_properties", []),
            "interested_properties": state.get("interested_properties", []),
            "summary": summary,
        },
        config,
    )
    
    return {"messages": response}


async def property_matching_node(state: TenantState, config: RunnableConfig):
    """Handle property matching analysis for tenant"""
    matching_chain = get_property_matching_chain()
    
    # 获取所有可用的房产
    available_properties = state.get("properties", [])
    
    if not available_properties:
        # 如果没有可用房产，返回一条消息说明情况
        no_properties_msg = "非常抱歉，目前没有可用的房产可以匹配。请稍后再试或修改您的搜索条件。"
        return {
            "messages": [{"role": "assistant", "content": no_properties_msg}],
            "matched_properties": [],
            "match_score": 0,
            "match_reasons": ["没有可用房产"],
            "matched_landlord": {}
        }
    
    response = await matching_chain.ainvoke(
        {
            "max_budget": state.get("max_budget", 0),
            "min_bedrooms": state.get("min_bedrooms", 1),
            "max_bedrooms": state.get("max_bedrooms", 3),
            "preferred_locations": state.get("preferred_locations", []),
            "is_student": state.get("is_student", False),
            "has_pets": state.get("has_pets", False),
            "is_smoker": state.get("is_smoker", False),
            "num_occupants": state.get("num_occupants", 1),
            "has_guarantor": state.get("has_guarantor", False),
            "properties": available_properties,
        },
        config,
    )
    
    # 进行房产匹配逻辑
    matched_result = []
    for prop in available_properties:
        # 实现一个简单的匹配算法
        match_score = 0
        match_reasons = []
        
        # 预算匹配
        if prop.get("monthly_rent", 0) <= state.get("max_budget", 0):
            match_score += 20
            match_reasons.append("房租在预算范围内")
        
        # 卧室数量匹配
        bedrooms = prop.get("bedrooms", 0)
        if bedrooms >= state.get("min_bedrooms", 1) and bedrooms <= state.get("max_bedrooms", 3):
            match_score += 20
            match_reasons.append(f"卧室数量符合要求: {bedrooms}间")
        
        # 位置匹配
        location = prop.get("location", "").lower()
        for preferred in state.get("preferred_locations", []):
            if preferred.lower() in location or preferred.lower() in location.lower():
                match_score += 15
                match_reasons.append(f"位于偏好区域: {preferred}")
                break
        
        # 其他特性匹配
        if state.get("has_pets", False) and prop.get("pets_allowed", False):
            match_score += 10
            match_reasons.append("允许宠物")
        
        if state.get("is_student", False) and prop.get("suitable_for_students", False):
            match_score += 10
            match_reasons.append("适合学生")
        
        # 如果分数达到阈值，认为匹配成功
        if match_score >= 35:
            matched_result.append({
                "property": prop,
                "score": match_score,
                "reasons": match_reasons
            })
    
    # 按匹配分数排序
    matched_result.sort(key=lambda x: x["score"], reverse=True)
    matched_properties = matched_result[:3]  # 取前3个最佳匹配
    
    # 如果没有匹配的房产但有可用房产，选择一个最接近的
    if not matched_properties and available_properties:
        # 找到租金最接近预算的房产
        closest_property = min(available_properties, key=lambda p: abs(p.get("monthly_rent", 0) - state.get("max_budget", 0)))
        matched_properties = [{
            "property": closest_property,
            "score": 40,
            "reasons": ["没有完全符合条件的房产，这是最接近的选择"]
        }]
    
    # 生成匹配结果消息
    match_msg = "根据您的需求，我找到了以下适合您的房产:\n\n"
    
    if not matched_properties:
        match_msg = "很遗憾，根据您的需求条件，我没有找到完全符合的房产。您是否可以考虑调整一些条件，比如增加预算或扩大搜索区域？"
        return {
            "messages": [{"role": "assistant", "content": match_msg}],
            "matched_properties": [],
            "match_score": 0,
            "match_reasons": ["无匹配结果"],
            "matched_landlord": {}
        }
    else:
        for i, match in enumerate(matched_properties, 1):
            prop = match["property"]
            match_msg += f"{i}. {prop.get('display_address', '未知地址')} - £{prop.get('monthly_rent', 0):,.0f}/月\n"
            match_msg += f"   {prop.get('bedrooms', 0)}间卧室, {prop.get('bathrooms', 0)}间浴室\n"
            match_msg += f"   匹配理由: {', '.join(match['reasons'])}\n"
            match_msg += f"   匹配度: {match['score']}\n\n"
        
        # 选择最佳匹配
        best_match = matched_properties[0]
        prop = best_match["property"]
        
        # 获取房东信息
        landlord = {
            "landlord_id": prop.get("landlord_id", ""),
            "landlord_name": prop.get("landlord_name", "未知房东")
        }
        
        match_msg += f"\n我认为第一个选项最适合您，这是由{landlord.get('landlord_name')}出租的房产。您想联系这位房东了解更多信息吗？"
        
        # 返回匹配结果、匹配的房产列表和房东信息
        return {
            "messages": [{"role": "assistant", "content": match_msg}],
            "matched_properties": matched_properties,
            "match_score": best_match["score"],
            "match_reasons": best_match["reasons"],
            "matched_landlord": landlord
        }


async def viewing_feedback_analysis_node(state: TenantState, config: RunnableConfig):
    """Handle property viewing feedback analysis"""
    feedback_chain = get_viewing_feedback_analysis_chain()

    # Get the latest message which should contain viewing feedback
    latest_message = state["messages"][-1] if state["messages"] else None
    
    response = await feedback_chain.ainvoke(
        {
            "property_address": "",  # To be extracted from context
            "viewing_date": "",      # To be extracted from context
            "attendees": [state.get("tenant_name", "")],
            "tenant_feedback": latest_message.content if latest_message else "",
            "interests": "",         # To be extracted from feedback
            "concerns": "",          # To be extracted from feedback
            "questions": "",         # To be extracted from feedback
        },
        config,
    )
    
    return {"messages": response}


async def summarize_conversation_node(state: TenantState):
    """Summarize tenant conversation and remove old messages"""
    summary = state.get("summary", "")
    summary_chain = get_rental_conversation_summary_chain(summary)

    response = await summary_chain.ainvoke(
        {
            "messages": state["messages"],
            "conversation_context": state.get("conversation_context", ""),
            "summary": summary,
        }
    )

    # Get the number of messages to keep after summary from config
    messages_after_summary = 5
    if config.agents and config.agents.total_messages_after_summary:
        messages_after_summary = config.agents.total_messages_after_summary

    delete_messages = [
        RemoveMessage(id=m.id)
        for m in state["messages"][: -messages_after_summary]
    ]
    return {"summary": response.content, "messages": delete_messages}


async def connector_node(state: TenantState):
    """Connector node for tenant workflow routing"""
    return {}
