from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.conversation_service import tenant_tools
from app.config import config
from app.conversation_service.prompt import (
    TENANT_AGENT_PROMPT,
    PROPERTY_MATCHING_PROMPT,
    VIEWING_FEEDBACK_ANALYSIS_PROMPT,
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


def get_tenant_agent_chain(tenant_info=None, conversation_data=None, debug_prompt=False):
    """
    Get the chain for tenant agent responses with proper variable handling
    
    Args:
        tenant_info (dict): Contains tenant details (id, name, income, etc.)
        conversation_data (dict): Context and summary of the conversation
        debug_prompt (bool): If True, will print the formatted prompt for debugging
    """
    model = get_chat_model()
    model = model.bind_tools(tenant_tools)
    
    # Default values to prevent errors when variables are missing
    tenant_info = tenant_info or {}
    conversation_data = conversation_data or {}
    
    # Create a template context with all variables the prompt might need
    template_context = {
        "tenant_id": tenant_info.get("tenant_id", ""),
        "tenant_name": tenant_info.get("name", ""),
        "email": tenant_info.get("email", ""),
        "phone": tenant_info.get("phone", ""),
        "annual_income": tenant_info.get("annual_income", 0),
        "has_guarantor": tenant_info.get("has_guarantor", False),
        "max_budget": tenant_info.get("max_budget", 0),
        "min_bedrooms": tenant_info.get("min_bedrooms", 1),
        "max_bedrooms": tenant_info.get("max_bedrooms", 3),
        "preferred_locations": tenant_info.get("preferred_locations", []),
        "is_student": tenant_info.get("is_student", False),
        "has_pets": tenant_info.get("has_pets", False),
        "is_smoker": tenant_info.get("is_smoker", False),
        "num_occupants": tenant_info.get("num_occupants", 1),
        "search_criteria": tenant_info.get("search_criteria", {}),
        "viewed_properties": tenant_info.get("viewed_properties", []),
        "interested_properties": tenant_info.get("interested_properties", []),
        "conversation_context": conversation_data.get("conversation_context", "No previous context"),
        "summary": conversation_data.get("summary", ""),
        "negotiation_round": conversation_data.get("negotiation_round", 1)
    }
    
    # Create the prompt template with the system message including all variables
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", TENANT_AGENT_PROMPT.get_prompt(**template_context)),
            MessagesPlaceholder(variable_name="messages"),
        ],
        template_format="jinja2",
    )
    
    # Bind the template context to the prompt
    formatted_prompt = prompt.partial(**template_context)
    
    return formatted_prompt | model


def get_property_matching_chain(tenant_info=None, properties=None, debug_prompt=False):
    """
    Get the chain for property matching analysis
    
    Args:
        tenant_info (dict): Contains tenant requirements (budget, bedrooms, etc.)
        properties (list): Available properties to match
        debug_prompt (bool): If True, will print the formatted prompt for debugging
    """
    model = get_chat_model()
    
    # Default values to prevent errors when variables are missing
    tenant_info = tenant_info or {}
    properties = properties or []
    
    # Create a template context with all variables the prompt might need
    template_context = {
        "max_budget": tenant_info.get("max_budget", 0),
        "min_bedrooms": tenant_info.get("min_bedrooms", 1),
        "max_bedrooms": tenant_info.get("max_bedrooms", 3),
        "preferred_locations": tenant_info.get("preferred_locations", []),
        "is_student": tenant_info.get("is_student", False),
        "has_pets": tenant_info.get("has_pets", False),
        "is_smoker": tenant_info.get("is_smoker", False),
        "num_occupants": tenant_info.get("num_occupants", 1),
        "has_guarantor": tenant_info.get("has_guarantor", False),
        "properties": properties
    }
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", PROPERTY_MATCHING_PROMPT.get_prompt(**template_context)),
        ],
        template_format="jinja2",
    )

    # Bind the template context to the prompt
    formatted_prompt = prompt.partial(**template_context)
    
    return formatted_prompt | model


def get_viewing_feedback_analysis_chain(viewing_info=None, feedback_data=None, debug_prompt=False):
    """
    Get the chain for analyzing property viewing feedback
    
    Args:
        viewing_info (dict): Information about the property viewing
        feedback_data (dict): Tenant feedback and concerns
        debug_prompt (bool): If True, will print the formatted prompt for debugging
    """
    model = get_chat_model()
    
    # Default values to prevent errors when variables are missing
    viewing_info = viewing_info or {}
    feedback_data = feedback_data or {}
    
    # Create a template context with all variables the prompt might need
    template_context = {
        "property_address": viewing_info.get("property_address", "Not specified"),
        "viewing_date": viewing_info.get("viewing_date", "Not specified"),
        "attendees": viewing_info.get("attendees", "Not specified"),
        "tenant_feedback": feedback_data.get("tenant_feedback", "No feedback provided"),
        "interests": feedback_data.get("interests", "None"),
        "concerns": feedback_data.get("concerns", "None"),
        "questions": feedback_data.get("questions", "None")
    }
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", VIEWING_FEEDBACK_ANALYSIS_PROMPT.prompt),
        ],
        template_format="jinja2",
    )

    # Bind the template context to the prompt
    formatted_prompt = prompt.partial(**template_context)
    
    return formatted_prompt | model


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
