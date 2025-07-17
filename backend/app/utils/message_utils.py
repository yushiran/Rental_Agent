"""
消息清理工具 - 修复不完整的工具调用消息
"""

from typing import List, Any
from loguru import logger


def clean_incomplete_tool_calls(messages: List[Any]) -> List[Any]:
    """
    清理消息列表中不完整的工具调用
    
    OpenAI API 要求：包含 tool_calls 的助手消息必须跟随相应的工具响应消息
    此函数确保所有工具调用都有对应的响应，否则移除不完整的工具调用
    
    Args:
        messages: 原始消息列表
        
    Returns:
        清理后的消息列表
    """
    cleaned_messages = []
    
    i = 0
    while i < len(messages):
        message = messages[i]
        
        # 检查是否是包含工具调用的助手消息
        if (hasattr(message, 'tool_calls') and message.tool_calls and 
            hasattr(message, 'role') and message.role == 'assistant'):
            
            # 查找对应的工具响应消息
            tool_call_ids = [call.id for call in message.tool_calls]
            found_responses = []
            
            # 检查后续消息中是否有对应的工具响应
            j = i + 1
            while j < len(messages) and len(found_responses) < len(tool_call_ids):
                next_msg = messages[j]
                if (hasattr(next_msg, 'role') and next_msg.role == 'tool' and
                    hasattr(next_msg, 'tool_call_id') and 
                    next_msg.tool_call_id in tool_call_ids):
                    found_responses.append(next_msg)
                elif hasattr(next_msg, 'role') and next_msg.role != 'tool':
                    # 遇到非工具消息，停止查找
                    break
                j += 1
            
            # 只有当所有工具调用都有对应响应时才包含这组消息
            if len(found_responses) == len(tool_call_ids):
                cleaned_messages.append(message)
                cleaned_messages.extend(found_responses)
                i = j
            else:
                # 跳过不完整的工具调用
                logger.warning(
                    f"🚨 Skipping incomplete tool call: "
                    f"{len(found_responses)}/{len(tool_call_ids)} responses found. "
                    f"Tool call IDs: {[call.id for call in message.tool_calls]}"
                )
                i += 1
        else:
            # 普通消息直接添加
            cleaned_messages.append(message)
            i += 1
    
    if len(cleaned_messages) != len(messages):
        logger.info(f"🧹 Cleaned messages: {len(messages)} -> {len(cleaned_messages)}")
    
    return cleaned_messages
