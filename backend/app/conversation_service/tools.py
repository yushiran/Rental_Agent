from langchain.tools.retriever import create_retriever_tool
from app.rag import get_retriever
from app.config import config

retriever = get_retriever(
    embedding_model_id=config.rag.text_embedding_model_id,
    k=config.rag.top_k,
    device=config.rag.device
)

retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_rental_context",
    "Search and return information about rental properties, market data, landlord preferences, or tenant requirements. Use this tool when you need to access rental-related information from the knowledge base.",
)

tools = [retriever_tool]
