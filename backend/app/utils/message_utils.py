"""
Message cleaning tool - Fix incomplete tool call messages
"""

from typing import List, Any
from loguru import logger


def clean_incomplete_tool_calls(messages: List[Any]) -> List[Any]:
    """
    Clean incomplete tool calls in message list
    
    OpenAI API requirement: Assistant messages containing tool_calls must be followed by corresponding tool response messages
    This function ensures all tool calls have corresponding responses, otherwise removes incomplete tool calls
    
    Args:
        messages: Original message list
        
    Returns:
        Cleaned message list
    """
    cleaned_messages = []
    
    i = 0
    while i < len(messages):
        message = messages[i]
        
        # Check if it's an assistant message containing tool calls
        if (hasattr(message, 'tool_calls') and message.tool_calls and 
            hasattr(message, 'role') and message.role == 'assistant'):
            
            # Find corresponding tool response messages
            tool_call_ids = [call.id for call in message.tool_calls]
            found_responses = []
            
            # Check if there are corresponding tool responses in subsequent messages
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
