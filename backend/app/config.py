import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional
import tomllib
from pydantic import BaseModel, Field


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).resolve().parent.parent

PROJECT_ROOT = get_project_root()

class LLMSettings(BaseModel):
    model: str = Field(..., description="Model name")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key")
    max_tokens: int = Field(4096, description="Maximum number of tokens per request")
    max_input_tokens: Optional[int] = Field(
        None,
        description="Maximum input tokens to use across all requests (None for unlimited)",
    )
    temperature: float = Field(1.0, description="Sampling temperature")
    api_type: str = Field(..., description="Azure, Openai, or Ollama")
    api_version: str = Field(..., description="Azure Openai version if AzureOpenai")

class RAW_RENTAL_DATA_API_SETTINGS(BaseModel):
    api_src: str = Field(...,
        description="API source URL for Rightmove data",
    )
    api_key: str = Field(...,
        description="API key for accessing the Rightmove data",
    )
    data_path: str = Field(str(PROJECT_ROOT / "dataset" / "rent_cast_data"),
        description="Path to save the rental data",
    )

class MongoDBSettings(BaseModel):
    host: str = Field("localhost", description="MongoDB host")
    port: int = Field(27017, description="MongoDB port")
    username: str = Field("", description="MongoDB username")
    password: str = Field("", description="MongoDB password")
    database: str = Field(..., description="MongoDB database name")
    auth_source: str = Field("admin", description="Authentication database")
    
    # Collection names
    mongo_state_checkpoint_collection: str = Field("state_checkpoints", description="State checkpoint collection name")
    mongo_state_writes_collection: str = Field("state_writes", description="State writes collection name")
    mongo_long_term_memory_collection: str = Field("long_term_memory", description="Long term memory collection name")
    
    @property
    def connection_string(self) -> str:
        """Generate MongoDB connection string"""
        if self.username and self.password:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?authSource={self.auth_source}"
        else:
            return f"mongodb://{self.host}:{self.port}/{self.database}"

class RAGSettings(BaseModel):
    text_embedding_model_id: str = Field("sentence-transformers/all-MiniLM-L6-v2", description="Text embedding model identifier")
    text_embedding_model_dim: int = Field(384, description="Text embedding model dimension")
    top_k: int = Field(3, description="Number of top documents to retrieve")
    device: str = Field("cpu", description="Device to run embedding model on")
    chunk_size: int = Field(256, description="Size of text chunks for processing")

class OpikSettings(BaseModel):
    api_key: str = Field(..., description="Opik API key")
    workspace: str = Field(..., description="Opik workspace name")
    project_name: str = Field("rental_agent", description="Opik project name")
    use_local: bool = Field(False, description="Use local Opik instance")
    base_url: Optional[str] = Field(None, description="Base URL for Opik API (if using local)")
    
    class Config:
        env_prefix = "OPIK_"

class LangSmithSettings(BaseModel):
    api_key: str = Field("", description="LangSmith API key")
    project_name: str = Field("rental_agent", description="LangSmith project name")
    endpoint: Optional[str] = Field("https://api.smith.langchain.com", description="LangSmith API endpoint")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set the API key as environment variable after initialization
        if self.api_key:
            os.environ["LANGSMITH_API_KEY"] = self.api_key

class AgentsSettings(BaseModel):
    total_messages_summary_trigger: int = Field(30, description="Number of messages that trigger a conversation summary")
    total_messages_after_summary: int = Field(5, description="Number of messages to keep after summarization")

class AppConfig(BaseModel):
    llm: Dict[str, LLMSettings]
    raw_rental_data_api: Optional[RAW_RENTAL_DATA_API_SETTINGS] = Field(None, description="API settings for raw rental data")
    mongodb: Optional[MongoDBSettings] = Field(None, description="MongoDB settings")
    rag: Optional[RAGSettings] = Field(None, description="RAG settings")
    opik: Optional[OpikSettings] = Field(None, description="Opik settings")
    langsmith: Optional[LangSmithSettings] = Field(None, description="LangSmith settings")
    agents: Optional[AgentsSettings] = Field(None, description="Agents configuration settings")

    class Config:
        arbitrary_types_allowed = True

class Config:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config = None
                    self._load_initial_config()
                    self._initialized = True

    @staticmethod
    def _get_config_path() -> Path:
        root = PROJECT_ROOT
        config_path = root / "config" / "config.toml"
        if config_path.exists():
            return config_path
        example_path = root / "config" / "config.example.toml"
        if example_path.exists():
            return example_path
        raise FileNotFoundError("No configuration file found in config directory")

    def _load_config(self) -> dict:
        config_path = self._get_config_path()
        with config_path.open("rb") as f:
            return tomllib.load(f)

    def _load_initial_config(self):
        raw_config = self._load_config()
        base_llm = raw_config.get("llm", {})
        llm_overrides = {
            k: v for k, v in raw_config.get("llm", {}).items() if isinstance(v, dict)
        }

        default_settings = {
            "model": base_llm.get("model"),
            "base_url": base_llm.get("base_url"),
            "api_key": base_llm.get("api_key"),
            "max_tokens": base_llm.get("max_tokens", 4096),
            "max_input_tokens": base_llm.get("max_input_tokens"),
            "temperature": base_llm.get("temperature", 1.0),
            "api_type": base_llm.get("api_type", ""),
            "api_version": base_llm.get("api_version", ""),
        }
    
        raw_rental_data_api_config = raw_config.get("raw_rental_data_api", {})
        raw_rental_data_api_settings = RAW_RENTAL_DATA_API_SETTINGS(**raw_rental_data_api_config) if raw_rental_data_api_config else None

        mongodb_config = raw_config.get("mongodb", {})
        mongodb_settings = MongoDBSettings(**mongodb_config) if mongodb_config else None

        rag_config = raw_config.get("rag", {})
        rag_settings = RAGSettings(**rag_config) if rag_config else None

        opik_config = raw_config.get("opik", {})
        opik_settings = OpikSettings(**opik_config) if opik_config else None

        langsmith_config = raw_config.get("langsmith", {})
        langsmith_settings = LangSmithSettings(**langsmith_config) if langsmith_config else None

        agents_config = raw_config.get("agents", {})
        agents_settings = AgentsSettings(**agents_config) if agents_config else None

        config_dict = {
            "llm": {
                "default": default_settings,
                **{
                    name: {**default_settings, **override_config}
                    for name, override_config in llm_overrides.items()
                },
            },
            "raw_rental_data_api": raw_rental_data_api_settings,
            "mongodb": mongodb_settings,
            "rag": rag_settings,
            "opik": opik_settings,
            "langsmith": langsmith_settings,
            "agents": agents_settings,
        }

        self._config = AppConfig(**config_dict)

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        assert self._config is not None
        return self._config.llm
    
    @property
    def raw_rental_data_api(self) -> Optional[RAW_RENTAL_DATA_API_SETTINGS]:
        assert self._config is not None
        return self._config.raw_rental_data_api

    @property
    def mongodb(self) -> Optional[MongoDBSettings]:
        assert self._config is not None
        return self._config.mongodb

    @property
    def rag(self) -> Optional[RAGSettings]:
        assert self._config is not None
        return self._config.rag

    @property
    def opik(self) -> Optional[OpikSettings]:
        assert self._config is not None
        return self._config.opik

    @property
    def langsmith(self) -> Optional[LangSmithSettings]:
        assert self._config is not None
        return self._config.langsmith

    @property
    def agents(self) -> Optional[AgentsSettings]:
        assert self._config is not None
        return self._config.agents

    @property
    def root_path(self) -> Path:
        """Get the root path of the application"""
        return PROJECT_ROOT

config = Config()