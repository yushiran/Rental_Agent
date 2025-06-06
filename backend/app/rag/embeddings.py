from langchain_openai import OpenAIEmbeddings
from app.config import config

EmbeddingsModel = OpenAIEmbeddings


def get_embedding_model(
    model_id: str,
    device: str = "gpu",
) -> EmbeddingsModel:
    """Gets an instance of an OpenAI embedding model.

    Args:
        model_id (str): The ID/name of the OpenAI embedding model to use
        device (str): The compute device parameter (not used for OpenAI models).
            Kept for compatibility with existing interface.

    Returns:
        EmbeddingsModel: A configured OpenAI embeddings model instance
    """
    return get_openai_embedding_model(model_id)


def get_openai_embedding_model(
    model_id: str
) -> OpenAIEmbeddings:
    """Gets an OpenAI embedding model instance.

    Args:
        model_id (str): The ID/name of the OpenAI embedding model to use

    Returns:
        OpenAIEmbeddings: A configured OpenAI embeddings model instance
    """
    # Get OpenAI settings from config
    llm_config = config.llm.get("default")
    
    return OpenAIEmbeddings(
        model=model_id,
        openai_api_key=llm_config.api_key,
        openai_api_base=llm_config.base_url if llm_config.base_url else None,
    )
