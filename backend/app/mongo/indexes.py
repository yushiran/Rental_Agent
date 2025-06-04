from typing import Optional
from pymongo.collection import Collection

from .client import MongoClientWrapper


def create_fulltext_search_index(
    collection: Collection,
    field: str,
    index_name: str
) -> None:
    """Create a fulltext search index on MongoDB collection.
    
    Args:
        collection: MongoDB collection instance
        field: Field name to create index on
        index_name: Name for the index
    """
    try:
        # Create a text index for full-text search
        collection.create_index([(field, "text")], name=index_name)
    except Exception as e:
        # If index already exists, ignore the error
        if "already exists" not in str(e):
            raise


class MongoIndex:
    def __init__(
        self,
        retriever: Optional[any] = None,
        mongodb_client: Optional[MongoClientWrapper] = None,
    ) -> None:
        self.retriever = retriever
        self.mongodb_client = mongodb_client

    def create(
        self,
        embedding_dim: int,
        is_hybrid: bool = False,
    ) -> None:
        """Create search indexes for the MongoDB collection.
        
        Args:
            embedding_dim: Dimension of embeddings for vector search
            is_hybrid: Whether to create hybrid search indexes
        """
        if not self.mongodb_client:
            raise ValueError("MongoDB client is required")
            
        if self.retriever and hasattr(self.retriever, 'vectorstore'):
            vectorstore = self.retriever.vectorstore
            
            # Create vector search index if vectorstore supports it
            if hasattr(vectorstore, 'create_vector_search_index'):
                vectorstore.create_vector_search_index(
                    dimensions=embedding_dim,
                )
            
            # Create fulltext search index for hybrid search
            if is_hybrid and hasattr(vectorstore, '_text_key'):
                create_fulltext_search_index(
                    collection=self.mongodb_client.collection,
                    field=vectorstore._text_key,
                    index_name=getattr(self.retriever, 'search_index_name', 'default_search_index'),
                )
        else:
            # Basic text index creation when no retriever is provided
            if is_hybrid:
                create_fulltext_search_index(
                    collection=self.mongodb_client.collection,
                    field="text",  # Default field name
                    index_name="text_search_index",
                )
