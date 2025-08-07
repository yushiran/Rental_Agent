import openai
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable, RunnableConfig
from typing import List, Any

# Define OpenAI exception types that need retry
RETRYABLE_EXCEPTIONS = (
    openai.APIError,
    openai.APITimeoutError,
    openai.APIConnectionError,
    openai.RateLimitError,
    openai.InternalServerError,
)

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=lambda retry_state: logger.warning(
        f"🚨 LLM call failed, retrying... "
        f"Attempt: {retry_state.attempt_number}, "
        f"Wait: {retry_state.next_action.sleep:.2f}s, "
        f"Exception: {retry_state.outcome.exception()}"
    )
)
async def invoke_llm_with_backoff(llm: ChatOpenAI, messages: List[BaseMessage]) -> Any:
    """
    Invoke LLM asynchronously using exponential backoff strategy.
    Automatically retries if retryable API errors occur.
    """
    return await llm.ainvoke(messages)

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=lambda retry_state: logger.warning(
        f"🚨 LLM call failed, retrying... "
        f"Attempt: {retry_state.attempt_number}, "
        f"Wait: {retry_state.next_action.sleep:.2f}s, "
        f"Exception: {retry_state.outcome.exception()}"
    )
)
def invoke_llm_sync_with_backoff(llm: ChatOpenAI, messages: List[BaseMessage]) -> Any:
    """
    Invoke LLM synchronously using exponential backoff strategy.
    """
    return llm.invoke(messages)


@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(6),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=lambda retry_state: logger.warning(
        f"🚨 Chain call failed, retrying... "
        f"Attempt: {retry_state.attempt_number}, "
        f"Wait: {retry_state.next_action.sleep:.2f}s, "
        f"Exception: {retry_state.outcome.exception()}"
    )
)
async def invoke_chain_with_backoff(chain: Runnable, input_data: dict, config: RunnableConfig = None) -> Any:
    """
    Invoke LangChain chain asynchronously using exponential backoff strategy.
    Automatically retries if retryable API errors occur.
    """
    if config:
        return await chain.ainvoke(input_data, config)
    return await chain.ainvoke(input_data)
