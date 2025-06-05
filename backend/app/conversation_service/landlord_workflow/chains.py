from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.conversation_service.landlord_workflow import tools
from app.config import config
from app.conversation_service.prompt import (
    LANDLORD_AGENT_PROMPT,
    PROPERTY_MATCHING_PROMPT,
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


def get_landlord_agent_chain():
    """Get the chain for landlord agent responses"""
    model = get_chat_model()
    model = model.bind_tools(tools)
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", LANDLORD_AGENT_PROMPT.prompt),
            MessagesPlaceholder(variable_name="messages"),
        ],
        template_format="jinja2",
    )

    return prompt | model


def get_property_matching_chain():
    """Get the chain for property matching analysis"""
    model = get_chat_model()
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("human", PROPERTY_MATCHING_PROMPT.prompt),
        ],
        template_format="jinja2",
    )

    return prompt | model


def get_rental_conversation_summary_chain(summary: str = ""):
    """Get the chain for summarizing rental conversations"""
    model = get_chat_model()

    prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="messages"),
            ("human", RENTAL_SUMMARY_PROMPT.prompt),
        ],
        template_format="jinja2",
    )

    return prompt | model
