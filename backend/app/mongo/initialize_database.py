async def initialize_database():
    """清理所有数据并重新初始化"""
    from app.mongo import MongoClientWrapper
    from app.config import config
    from pymongo import MongoClient
    from loguru import logger
    
    logger.info("开始清理和初始化MongoDB数据...")
    
    # 1. 首先重置对话状态
    try:
        from app.conversation_service.reset_conversation import reset_conversation_state
        result = await reset_conversation_state()
        logger.info(f"对话状态重置结果: {result}")
    except Exception as e:
        logger.error(f"重置对话状态失败: {e}")

    # 2. 清理所有其他集合
    try:
        # 获取数据库连接
        client = MongoClient(config.mongodb.connection_string)
        db = client[config.mongodb.database]
        
        # 获取所有集合名称
        all_collections = db.list_collection_names()
        
        # 排除系统集合
        user_collections = [coll for coll in all_collections 
                           if not coll.startswith("system.")]
        
        # 清理每个集合
        for collection_name in user_collections:
            db.drop_collection(collection_name)
            logger.info(f"已删除集合: {collection_name}")
            
        client.close()
        logger.info("成功清理所有MongoDB集合")
    except Exception as e:
        logger.error(f"清理MongoDB集合时发生错误: {e}")
    
    # 3. 初始化基础数据
    try:
        from app.agents import AgentDataInitializer
        initializer = AgentDataInitializer()
        rightmove_file = f"{config.root_path}/dataset/rent_cast_data/processed/rightmove_data_processed.json"
        initializer.initialize_all_data(rightmove_file, tenant_count=50)
        logger.info("成功初始化所有基础数据")
    except Exception as e:
        logger.error(f"初始化基础数据时发生错误: {e}")
        
    logger.info("MongoDB初始化完成")