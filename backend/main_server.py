"""
多Agent租房系统主启动文件
"""

import asyncio
import uvicorn
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config import LLMSettings, get_project_root, config
from app.api_service.rental_api import RentalAPI
from loguru import logger


def get_llm_config() -> dict:
    """获取LLM配置"""
    # 从配置文件读取LLM配置
    default_llm = config.llm.get("default")
    if not default_llm:
        raise ValueError("Default LLM configuration not found in config file")
    
    return {
        "model": default_llm.model,
        "api_key": default_llm.api_key,
        "base_url": default_llm.base_url,
        "temperature": default_llm.temperature,
        "max_tokens": default_llm.max_tokens,
    }


def create_app():
    """创建FastAPI应用"""
    llm_config = get_llm_config()
    api = RentalAPI(llm_config)
    return api.get_app()


async def main():
    """主函数"""
    logger.info("启动多Agent租房系统...")
    
    # 创建应用
    app = create_app()
    
    # 配置服务器
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )
    
    server = uvicorn.Server(config)
    
    logger.info("服务器启动在 http://localhost:8000")
    logger.info("API文档地址: http://localhost:8000/docs")
    logger.info("WebSocket测试: ws://localhost:8000/ws/your_client_id")
    
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
