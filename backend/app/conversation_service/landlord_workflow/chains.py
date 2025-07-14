from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.conversation_service import tools
from app.config import config
from app.conversation_service.prompt import (
    LANDLORD_AGENT_PROMPT,
    RENTAL_SUMMARY_PROMPT,
)

def get_chat_model(temperature: float = 0.7, model_name: str = "default") -> ChatOpenAI:
    llm_config = config.llm.get(model_name, config.llm["default"])
    return ChatOpenAI(
        api_key=llm_config.api_key,
        model=llm_config.model,
        base_url=llm_config.base_url,
        temperature=temperature,
        max_tokens=llm_config.max_tokens,
    )


# def get_landlord_agent_chain():
#     """Get the chain for landlord agent responses"""
#     model = get_chat_model()
#     model = model.bind_tools(tools)
    
#     prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", LANDLORD_AGENT_PROMPT.prompt),
#             MessagesPlaceholder(variable_name="messages"),
#         ],
#         template_format="jinja2",
#     )

#     return prompt | model


def get_landlord_agent_chain(landlord_info=None, property_info=None, conversation_data=None):
    """
    Get the chain for landlord agent responses with proper variable handling
    
    Args:
        landlord_info (dict): Contains landlord details (id, name, branch, etc.)
        property_info (dict): Information about the property being discussed
        conversation_data (dict): Context and summary of the conversation
    """
    model = get_chat_model()
    model = model.bind_tools(tools)
    
    # Default values to prevent errors when variables are missing
    landlord_info = landlord_info or {}
    property_info = property_info or {}
    conversation_data = conversation_data or {}
    
    # Create a template context with all variables the prompt might need
    template_context = {
        "landlord_id": landlord_info.get("landlord_id", ""),
        "landlord_name": landlord_info.get("name", ""),
        "branch_name": landlord_info.get("branch_name", ""),
        "phone": landlord_info.get("phone", ""),
        "properties": landlord_info.get("properties", "No properties listed"),
        "preferences": landlord_info.get("preferences", "No specific preferences"),
        "current_property_focus": property_info.get("address", "Not specified"),
        "conversation_context": conversation_data.get("conversation_context", "No previous context"),
        "summary": conversation_data.get("summary", "")
    }
    
    # Create the prompt template with the system message including all variables
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", LANDLORD_AGENT_PROMPT.get_prompt(**template_context)),
            MessagesPlaceholder(variable_name="messages"),
        ],
        template_format="jinja2",
    )
    
    # Bind the template context to the prompt
    formatted_prompt = prompt.partial(**template_context)

    # print(f"Formatted Prompt: {formatted_prompt}")

    return formatted_prompt | model


# Property matching chain removed - tenant is now responsible for all matching


def get_rental_conversation_summary_chain(conversation_data=None, debug_prompt=False):
    """
    Get the chain for summarizing rental conversations
    
    Args:
        conversation_data (dict): Contains conversation context and existing summary
        debug_prompt (bool): If True, will print the formatted prompt for debugging
    """
    model = get_chat_model()
    
    conversation_data = conversation_data or {}
    
    template_context = {
        "conversation_context": conversation_data.get("conversation_context", "No previous context"),
        "summary": conversation_data.get("summary", "")
    }
    
    prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="messages"),
            ("human", RENTAL_SUMMARY_PROMPT.get_prompt(**template_context)),
        ],
        template_format="jinja2",
    )
    
    formatted_prompt = prompt.partial(**template_context)
    
    return formatted_prompt | model
