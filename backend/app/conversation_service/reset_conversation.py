from loguru import logger
from pymongo import MongoClient

from app.config import config


async def reset_conversation_state() -> dict:
    """Deletes all conversation state data from MongoDB.

    This function removes all stored conversation checkpoints and writes,
    effectively resetting all philosopher conversations.

    Returns:
        dict: Status message indicating success or failure with details
              about which collections were deleted

    Raises:
        Exception: If there's an error connecting to MongoDB or deleting collections
    """
    try:
        # Check if MongoDB configuration exists
        if not config.mongodb:
            raise Exception("MongoDB configuration not found")
        
        mongodb_config = config.mongodb
        client = MongoClient(mongodb_config.connection_string)
        db = client[mongodb_config.database]

        collections_deleted = []

        # Delete state checkpoint collection
        if mongodb_config.mongo_state_checkpoint_collection in db.list_collection_names():
            db.drop_collection(mongodb_config.mongo_state_checkpoint_collection)
            collections_deleted.append(mongodb_config.mongo_state_checkpoint_collection)
            logger.info(
                f"Deleted collection: {mongodb_config.mongo_state_checkpoint_collection}"
            )

        # Delete state writes collection
        if mongodb_config.mongo_state_writes_collection in db.list_collection_names():
            db.drop_collection(mongodb_config.mongo_state_writes_collection)
            collections_deleted.append(mongodb_config.mongo_state_writes_collection)
            logger.info(f"Deleted collection: {mongodb_config.mongo_state_writes_collection}")

        client.close()

        if collections_deleted:
            return {
                "status": "success",
                "message": f"Successfully deleted collections: {', '.join(collections_deleted)}",
            }
        else:
            return {
                "status": "success",
                "message": "No collections needed to be deleted",
            }

    except Exception as e:
        logger.error(f"Failed to reset conversation state: {str(e)}")
        raise Exception(f"Failed to reset conversation state: {str(e)}")
