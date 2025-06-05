import uuid
from typing import Any, AsyncGenerator, Union

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver
from opik.integrations.langchain import OpikTracer

from app.conversation_service.tenant_workflow.graph import create_tenant_workflow_graph
from app.conversation_service.landlord_workflow.graph import create_landlord_workflow_graph
from app.config import config


def _format_messages(
    messages: Union[str, list[str], list[dict[str, Any]]],
) -> list[Union[HumanMessage, AIMessage]]:
    """Convert various message formats to a list of LangChain message objects.

    Args:
        messages: Can be one of:
            - A single string message
            - A list of string messages
            - A list of dictionaries with 'role' and 'content' keys

    Returns:
        List[Union[HumanMessage, AIMessage]]: A list of LangChain message objects
    """
    if isinstance(messages, str):
        return [HumanMessage(content=messages)]

    if isinstance(messages, list):
        if not messages:
            return []

        if (
            isinstance(messages[0], dict)
            and "role" in messages[0]
            and "content" in messages[0]
        ):
            result = []
            for msg in messages:
                if msg["role"] == "user":
                    result.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    result.append(AIMessage(content=msg["content"]))
            return result

        return [HumanMessage(content=message) for message in messages]

    return []

async def get_tenant_streaming_response(
    messages: str | list[str] | list[dict[str, Any]],
    tenant_id: str,
    tenant_name: str,
    budget_info: dict[str, Any],
    preferences: dict[str, Any],
    new_thread: bool = False,
) -> AsyncGenerator[str, None]:
    """Streaming response function for tenant agent.
    
    Args:
        messages: User messages in various formats
        tenant_id: Unique identifier for the tenant
        tenant_name: Name of the tenant
        budget_info: Budget related information (annual_income, max_budget, etc.)
        preferences: Tenant preferences (bedrooms, locations, etc.)
        new_thread: Whether to create a new conversation thread
        
    Yields:
        Chunks of the response as they become available
    """
    try:
        graph_builder = create_tenant_workflow_graph()
        
        async with AsyncMongoDBSaver.from_conn_string(
            conn_string=config.mongodb.connection_string,
            db_name=config.mongodb.database,
            checkpoint_collection_name=config.mongodb.mongo_state_checkpoint_collection,
            writes_collection_name=config.mongodb.mongo_state_writes_collection,
        ) as checkpointer:
            graph = graph_builder.compile(checkpointer=checkpointer)
            opik_tracer = OpikTracer(graph=graph.get_graph(xray=True))

            thread_id = (
                tenant_id if not new_thread else f"{tenant_id}-{uuid.uuid4()}"
            )
            config_dict = {
                "configurable": {"thread_id": thread_id},
                "callbacks": [opik_tracer],
            }

            # Prepare tenant input data
            input_data = {
                "messages": _format_messages(messages=messages),
                "tenant_id": tenant_id,
                "tenant_name": tenant_name,
                **budget_info,
                **preferences,
                "conversation_context": "",
                "summary": "",
                "search_criteria": {},
                "viewed_properties": [],
                "interested_properties": []
            }

            async for chunk in graph.astream(
                input=input_data,
                config=config_dict,
                stream_mode="messages",
            ):
                if chunk[1]["langgraph_node"] == "tenant_agent_node" and isinstance(
                    chunk[0], AIMessageChunk
                ):
                    yield chunk[0].content

    except Exception as e:
        raise RuntimeError(
            f"Error running streaming tenant conversation workflow: {str(e)}"
        ) from e


async def get_landlord_streaming_response(
    messages: str | list[str] | list[dict[str, Any]],
    landlord_id: str,
    landlord_name: str,
    properties: list[dict[str, Any]],
    business_info: dict[str, Any],
    new_thread: bool = False,
) -> AsyncGenerator[str, None]:
    """Streaming response function for landlord agent.
    
    Args:
        messages: User messages in various formats
        landlord_id: Unique identifier for the landlord
        landlord_name: Name of the landlord
        properties: List of available properties
        business_info: Business related information (branch_name, preferences, etc.)
        new_thread: Whether to create a new conversation thread
        
    Yields:
        Chunks of the response as they become available
    """
    try:
        graph_builder = create_landlord_workflow_graph()
        
        async with AsyncMongoDBSaver.from_conn_string(
            conn_string=config.mongodb.connection_string,
            db_name=config.mongodb.database,
            checkpoint_collection_name=config.mongodb.mongo_state_checkpoint_collection,
            writes_collection_name=config.mongodb.mongo_state_writes_collection,
        ) as checkpointer:
            graph = graph_builder.compile(checkpointer=checkpointer)
            opik_tracer = OpikTracer(graph=graph.get_graph(xray=True))

            thread_id = (
                landlord_id if not new_thread else f"{landlord_id}-{uuid.uuid4()}"
            )
            config_dict = {
                "configurable": {"thread_id": thread_id},
                "callbacks": [opik_tracer],
            }

            # Prepare landlord input data
            input_data = {
                "messages": _format_messages(messages=messages),
                "landlord_id": landlord_id,
                "landlord_name": landlord_name,
                "properties": properties,
                "conversation_context": "",
                "summary": "",
                "current_property_focus": None,
                "tenant_requirements": {},
                **business_info
            }

            async for chunk in graph.astream(
                input=input_data,
                config=config_dict,
                stream_mode="messages",
            ):
                if chunk[1]["langgraph_node"] == "landlord_agent_node" and isinstance(
                    chunk[0], AIMessageChunk
                ):
                    yield chunk[0].content

    except Exception as e:
        raise RuntimeError(
            f"Error running streaming landlord conversation workflow: {str(e)}"
        ) from e
