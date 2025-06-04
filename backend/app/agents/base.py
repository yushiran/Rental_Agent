from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timedelta
import json

from autogen import ConversableAgent
from loguru import logger
from pydantic import BaseModel, Field

from app.mongodb.client import AsyncMongoClientWrapper


class AgentMemoryModel(BaseModel):
    """Agent 记忆数据模型"""
    id: Optional[str] = None
    agent_name: str
    memory_type: str  # 'interaction', 'preference', 'market_data', 'decision'
    content: dict
    timestamp: datetime = Field(default_factory=datetime.now)
    importance: int = Field(default=5, ge=1, le=10)
    tags: List[str] = Field(default_factory=list)


class ConversationMemoryModel(BaseModel):
    """对话记忆数据模型"""
    id: Optional[str] = None
    conversation_id: str
    agent_name: str
    message_content: str
    message_type: str = 'text'
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class RAGQueryModel(BaseModel):
    """RAG 查询记录模型"""
    id: Optional[str] = None
    agent_name: str
    query: str
    response: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class EnhancedRentalAgent(ConversableAgent):
    """增强的租房 Agent 基类，集成异步 MongoDB 支持和 AutoGen RAG"""
    
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
        
        # 异步 MongoDB 客户端
        self.memory_client = None
        self.conversation_client = None
        self.rag_query_client = None
        self.initialized = False
        
        # RAG 系统配置
        self.enable_rag = enable_rag
        self.rag_system = None
        
        # 本地缓存
        self.memory_cache: List[AgentMemoryModel] = []
        self.conversation_cache: List[ConversationMemoryModel] = []
        
    async def initialize_database(self):
        """初始化数据库连接"""
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
            
            # 初始化 RAG 系统
            if self.enable_rag:
                await self._initialize_rag_system()
            
            self.initialized = True
            logger.info(f"Database and RAG system initialized for agent: {self.name}")

    async def _initialize_rag_system(self):
        """初始化 RAG 系统"""
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
        """异步保存记忆"""
        if not self.initialized:
            await self.initialize_database()
            
        memory = AgentMemoryModel(
            agent_name=self.name,
            memory_type=memory_type,
            content=content,
            importance=importance,
            tags=tags or []
        )
        
        # 保存到数据库
        memory_id = await self.memory_client.insert_one(memory)
        
        # 添加到本地缓存
        memory.id = memory_id
        self.memory_cache.append(memory)
        
        # 保持缓存大小
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
        """异步获取记忆"""
        if not self.initialized:
            await self.initialize_database()
            
        # 构建查询过滤器
        filter_dict = {"agent_name": self.name}
        if memory_type:
            filter_dict["memory_type"] = memory_type
        if importance_threshold > 1:
            filter_dict["importance"] = {"$gte": importance_threshold}
            
        # 优先使用缓存
        if use_cache and memory_type is None:
            cached_memories = [
                m for m in self.memory_cache 
                if m.importance >= importance_threshold
            ]
            if len(cached_memories) >= limit:
                return sorted(cached_memories, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        # 从数据库查询
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
        """保存对话记忆"""
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
        
        # 添加到本地缓存
        conv_memory.id = memory_id
        self.conversation_cache.append(conv_memory)
        
        logger.debug(f"{self.name} saved conversation memory")
        return memory_id

    async def get_conversation_history(
        self, 
        conversation_id: str, 
        limit: int = 50
    ) -> List[ConversationMemoryModel]:
        """获取对话历史"""
        if not self.initialized:
            await self.initialize_database()
            
        history = await self.conversation_client.find_many_sorted(
            {"conversation_id": conversation_id},
            [("timestamp", 1)],
            limit
        )
        
        return history

    async def update_memory_importance(self, memory_id: str, new_importance: int):
        """更新记忆重要性"""
        if not self.initialized:
            await self.initialize_database()
            
        await self.memory_client.update_one(
            {"_id": memory_id},
            {"importance": new_importance}
        )

    async def search_memories(self, search_terms: List[str], limit: int = 10) -> List[AgentMemoryModel]:
        """搜索记忆"""
        if not self.initialized:
            await self.initialize_database()
            
        # 构建文本搜索查询
        search_query = {
            "agent_name": self.name,
            "$or": [
                {"tags": {"$in": search_terms}},
                {"memory_type": {"$in": search_terms}}
            ]
        }
        
        memories = await self.memory_client.find_many_sorted(
            search_query,
            [("importance", -1), ("timestamp", -1)],
            limit
        )
        
        return memories

    async def get_memory_summary(self) -> Dict[str, Any]:
        """获取记忆摘要统计"""
        if not self.initialized:
            await self.initialize_database()
            
        # 使用聚合查询获取统计信息
        pipeline = [
            {"$match": {"agent_name": self.name}},
            {"$group": {
                "_id": "$memory_type",
                "count": {"$sum": 1},
                "avg_importance": {"$avg": "$importance"}
            }}
        ]
        
        stats = await self.memory_client.aggregate(pipeline)
        
        summary = {
            "total_memories": len(self.memory_cache),
            "memory_types": {stat["_id"]: stat for stat in stats},
            "last_updated": datetime.now().isoformat()
        }
        
        return summary

    async def cleanup_old_memories(self, days_old: int = 30, min_importance: int = 3):
        """清理旧的低重要性记忆"""
        if not self.initialized:
            await self.initialize_database()
            
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        filter_dict = {
            "agent_name": self.name,
            "timestamp": {"$lt": cutoff_date},
            "importance": {"$lt": min_importance}
        }
        
        deleted_count = await self.memory_client.delete_many(filter_dict)
        logger.info(f"{self.name} cleaned up {deleted_count} old memories")
        
        return deleted_count

    async def close_database_connections(self):
        """关闭数据库连接"""
        if self.memory_client:
            await self.memory_client.close()
        if self.conversation_client:
            await self.conversation_client.close()
        if self.rag_query_client:
            await self.rag_query_client.close()
        
        self.initialized = False
        logger.info(f"Database connections closed for agent: {self.name}")

    async def query_rag_system(
        self, 
        query: str, 
        context: Dict[str, Any] = None,
        save_query: bool = True
    ) -> str:
        """查询 RAG 系统获取增强信息"""
        if not self.enable_rag or not self.rag_system:
            return "RAG system not available"
        
        if not self.initialized:
            await self.initialize_database()
        
        try:
            # 查询 RAG 系统
            response = await self.rag_system.ask_question(query, context)
            
            # 保存查询记录
            if save_query:
                await self._save_rag_query(query, response, context)
            
            logger.debug(f"{self.name} RAG query successful")
            return response
            
        except Exception as e:
            logger.error(f"RAG query failed for {self.name}: {e}")
            return f"RAG query error: {str(e)}"

    async def _save_rag_query(
        self, 
        query: str, 
        response: str, 
        context: Dict[str, Any] = None
    ):
        """保存 RAG 查询记录"""
        rag_query = RAGQueryModel(
            agent_name=self.name,
            query=query,
            response=response,
            context=context or {}
        )
        
        await self.rag_query_client.insert_one(rag_query)

    async def get_rag_history(self, limit: int = 20) -> List[RAGQueryModel]:
        """获取 RAG 查询历史"""
        if not self.initialized:
            await self.initialize_database()
        
        return await self.rag_query_client.find_many_sorted(
            {"agent_name": self.name},
            [("timestamp", -1)],
            limit
        )

    async def analyze_with_rag(self, data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """使用 RAG 系统分析数据"""
        if not self.enable_rag:
            return {"error": "RAG system not enabled"}
        
        # 构建分析查询
        query = f"Analyze this {analysis_type} data and provide insights: {json.dumps(data, indent=2)}"
        
        # 获取 RAG 响应
        rag_response = await self.query_rag_system(query, {"analysis_type": analysis_type})
        
        # 保存分析结果作为记忆
        await self.save_memory(
            f"rag_analysis_{analysis_type}",
            {
                "input_data": data,
                "rag_response": rag_response,
                "analysis_type": analysis_type
            },
            importance=7
        )
        
        return {
            "analysis_type": analysis_type,
            "input_data": data,
            "rag_insights": rag_response,
            "timestamp": datetime.now().isoformat()
        }

    @abstractmethod
    async def process_message_async(self, message: str, sender: str, context: Dict[str, Any] = None) -> str:
        """异步处理消息的抽象方法"""
        pass

    @abstractmethod
    async def make_decision_async(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """异步决策的抽象方法"""
        pass

    @abstractmethod
    async def process_message_with_rag(
        self, 
        message: str, 
        sender: str, 
        context: Dict[str, Any] = None,
        use_rag: bool = True
    ) -> str:
        """使用 RAG 增强的消息处理抽象方法"""
        pass

    @abstractmethod
    async def make_decision_with_rag(
        self, 
        context: Dict[str, Any],
        decision_type: str = None
    ) -> Dict[str, Any]:
        """使用 RAG 增强的决策抽象方法"""
        pass
