from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timedelta
import json

from autogen import ConversableAgent
from loguru import logger
from pydantic import BaseModel, Field


class EnhancedRentalAgent(ConversableAgent):
    """Enhanced Rental Agent Base Class, integrating async MongoDB support and AutoGen RAG"""
    
    def __init__(
        self,
        name: str,
        llm_config: Dict[str, Any],
        system_message: str = "",
        enable_rag: bool = True,
        **kwargs
    ):
        super().__init__(
            name=name,
            llm_config=llm_config,
            system_message=system_message,
            **kwargs
        )
        
        # Async MongoDB client
        self.memory_client = None
        self.conversation_client = None
        self.rag_query_client = None
        self.initialized = False
        
        # RAG system configuration
        self.enable_rag = enable_rag
        self.rag_system = None
        
        # Local cache
        self.memory_cache: List[AgentMemoryModel] = []
        self.conversation_cache: List[ConversationMemoryModel] = []
        
    async def initialize_database(self):
        """Initialize database connections"""
        if not self.initialized:
            self.memory_client = AsyncMongoClientWrapper(
                AgentMemoryModel, 
                f"agent_memories_{self.name.lower()}"
            )
            self.conversation_client = AsyncMongoClientWrapper(
                ConversationMemoryModel,
                "conversation_memories"
            )
            self.rag_query_client = AsyncMongoClientWrapper(
                RAGQueryModel,
                f"rag_queries_{self.name.lower()}"
            )
            
            await self.memory_client.connect()
            await self.conversation_client.connect()
            await self.rag_query_client.connect()
            
            # Initialize RAG system
            if self.enable_rag:
                await self._initialize_rag_system()
            
            self.initialized = True
            logger.info(f"Database and RAG system initialized for agent: {self.name}")

    async def _initialize_rag_system(self):
        """Initialize RAG system"""
        try:
            from app.mongodb.autogen_integration import get_rental_rag
            self.rag_system = await get_rental_rag()
            logger.info(f"RAG system initialized for agent: {self.name}")
        except Exception as e:
            logger.warning(f"Failed to initialize RAG system for {self.name}: {e}")
            self.enable_rag = False

    async def save_memory(
        self, 
        memory_type: str, 
        content: Dict[str, Any], 
        importance: int = 5,
        tags: List[str] = None
    ) -> str:
        """Asynchronously save memory"""
        if not self.initialized:
            await self.initialize_database()
            
        memory = AgentMemoryModel(
            agent_name=self.name,
            memory_type=memory_type,
            content=content,
            importance=importance,
            tags=tags or []
        )
        
        # Save to database
        memory_id = await self.memory_client.insert_one(memory)
        
        # Add to local cache
        memory.id = memory_id
        self.memory_cache.append(memory)
        
        # Maintain cache size
        if len(self.memory_cache) > 100:
            self.memory_cache = self.memory_cache[-50:]
            
        logger.debug(f"{self.name} saved memory: {memory_type}")
        return memory_id

    async def get_memories(
        self, 
        memory_type: str = None, 
        importance_threshold: int = 1,
        limit: int = 20,
        use_cache: bool = True
    ) -> List[AgentMemoryModel]:
        """Asynchronously retrieve memories"""
        if not self.initialized:
            await self.initialize_database()
            
        # Build query filter
        filter_dict = {"agent_name": self.name}
        if memory_type:
            filter_dict["memory_type"] = memory_type
        if importance_threshold > 1:
            filter_dict["importance"] = {"$gte": importance_threshold}
            
        # Prioritize cache
        if use_cache and memory_type is None:
            cached_memories = [
                m for m in self.memory_cache 
                if m.importance >= importance_threshold
            ]
            if len(cached_memories) >= limit:
                return sorted(cached_memories, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        # Query from database
        memories = await self.memory_client.find_many_sorted(
            filter_dict,
            [("timestamp", -1)],
            limit
        )
        
        logger.debug(f"{self.name} retrieved {len(memories)} memories")
        return memories

    async def save_conversation_memory(
        self,
        conversation_id: str,
        message_content: str,
        message_type: str = 'text',
        context: Dict[str, Any] = None
    ) -> str:
        """Save conversation memory"""
        if not self.initialized:
            await self.initialize_database()
            
        conv_memory = ConversationMemoryModel(
            conversation_id=conversation_id,
            agent_name=self.name,
            message_content=message_content,
            message_type=message_type,
            context=context or {}
        )
        
        memory_id = await self.conversation_client.insert_one(conv_memory)
        
        # Add to local cache
        conv_memory.id = memory_id
        self.conversation_cache.append(conv_memory)
        
        logger.debug(f"{self.name} saved conversation memory")
        return memory_id

    async def get_conversation_history(
        self, 
        conversation_id: str, 
        limit: int = 50
    ) -> List[ConversationMemoryModel]:
        """Get conversation history"""
        if not self.initialized:
            await self.initialize_database()
            
        history = await self.conversation_client.find_many_sorted(
            {"conversation_id": conversation_id},
            [("timestamp", 1)],
            limit
        )
        
        return history

    async def update_memory_importance(self, memory_id: str, new_importance: int):
        """Update memory importance"""
        if not self.initialized:
            await self.initialize_database()
            
        await self.memory_client.update_one(
            {"_id": memory_id},
            {"importance": new_importance}
        )

    async def search_memories(self, search_terms: List[str], limit: int = 10) -> List[AgentMemoryModel]:
        """Search memories"""
        if not self.initialized:
            await self.initialize_database()
            
        # Build text search query
        search_query = {
            "agent_name": self.name,
            "$or": [
                {"tags": {"$in": search_terms}},
                {"memory_type": {"$in": search_terms}}
            ]
        }
        
        memories = await self.memory_client.find_many_sorted(
            search_query,
            [("timestamp", -1)],
            limit
        )
        
        return memories

    async def get_memory_summary(self) -> Dict[str, Any]:
        """Get memory statistics summary"""
        if not self.initialized:
            await self.initialize_database()
            
        pipeline = [
            {"$match": {"agent_name": self.name}},
            {"$group": {
                "_id": "$memory_type",
                "count": {"$sum": 1},
                "avg_importance": {"$avg": "$importance"}
            }}
        ]
        
        summary = await self.memory_client.aggregate(pipeline)
        
        return {
            "total_memories": len(self.memory_cache),
            "type_stats": summary
        }

    async def cleanup_old_memories(self, days_old: int = 30, min_importance: int = 3):
        """Clean up old memories with low importance"""
        if not self.initialized:
            await self.initialize_database()
            
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        delete_filter = {
            "agent_name": self.name,
            "timestamp": {"$lt": cutoff_date},
            "importance": {"$lt": min_importance}
        }
        
        deleted_count = await self.memory_client.delete_many(delete_filter)
        logger.info(f"Cleaned up {deleted_count} old memories for {self.name}")

    async def close_database_connections(self):
        """Close all database connections"""
        if self.initialized:
            await self.memory_client.close()
            await self.conversation_client.close()
            await self.rag_query_client.close()
            self.initialized = False
            logger.info(f"Closed database connections for agent: {self.name}")

    async def query_rag_system(
        self, 
        query: str, 
        context: Dict[str, Any] = None,
        save_query: bool = True
    ) -> str:
        """Query the RAG system"""
        if not self.enable_rag or not self.rag_system:
            return "RAG system is not enabled or initialized"
            
        try:
            response = await self.rag_system.aquery(query, context)
            
            if save_query:
                await self._save_rag_query(query, response, context)
                
            return response
            
        except Exception as e:
            logger.error(f"RAG query failed for {self.name}: {e}")
            return f"RAG query failed: {str(e)}"

    async def _save_rag_query(
        self, 
        query: str, 
        response: str, 
        context: Dict[str, Any] = None
    ):
        """Save RAG query and response"""
        if not self.initialized:
            await self.initialize_database()
            
        rag_query = RAGQueryModel(
            agent_name=self.name,
            query=query,
            response=response,
            context=context or {}
        )
        
        await self.rag_query_client.insert_one(rag_query)

    async def get_rag_history(self, limit: int = 20) -> List[RAGQueryModel]:
        """Get RAG query history"""
        if not self.initialized:
            await self.initialize_database()
            
        history = await self.rag_query_client.find_many_sorted(
            {"agent_name": self.name},
            [("timestamp", -1)],
            limit
        )
        
        return history

    async def analyze_with_rag(self, data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Analyze data using RAG system"""
        if not self.enable_rag or not self.rag_system:
            return {"error": "RAG system is not enabled or initialized"}
            
        try:
            # Format data for analysis
            data_str = json.dumps(data, indent=2)
            query = f"Please analyze this {analysis_type} data:\n{data_str}"
            
            # Get RAG response
            response = await self.query_rag_system(
                query,
                context={"analysis_type": analysis_type}
            )
            
            return {
                "analysis_type": analysis_type,
                "raw_data": data,
                "analysis_result": response
            }
            
        except Exception as e:
            logger.error(f"RAG analysis failed for {self.name}: {e}")
            return {"error": str(e)}

    @abstractmethod
    async def process_message_async(self, message: str, sender: str, context: Dict[str, Any] = None) -> str:
        """Process message asynchronously"""
        pass

    @abstractmethod
    async def make_decision_async(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Make decision asynchronously"""
        pass

    @abstractmethod
    async def process_message_with_rag(
        self, 
        message: str, 
        sender: str, 
        context: Dict[str, Any] = None,
        use_rag: bool = True
    ) -> str:
        """Process message with RAG support"""
        pass

    @abstractmethod
    async def make_decision_with_rag(
        self, 
        context: Dict[str, Any],
        decision_type: str = None
    ) -> Dict[str, Any]:
        """Make decision with RAG support"""
        pass
