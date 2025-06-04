"""
Opik integration utilities for rental agent monitoring.
Provides simple tracking and dataset management for LLM operations.
"""

import os
from typing import Optional, Dict, Any, List

import opik
from loguru import logger
from opik.configurator.configure import OpikConfigurator

from app.config import config


def configure() -> None:
    """Configure Opik client with settings from config."""
    opik_config = config.opik
    if not opik_config:
        logger.warning(
            "Opik configuration not found. Set opik settings in config.toml to enable monitoring."
        )
        return

    try:
        # Try to get default workspace
        try:
            client = OpikConfigurator(api_key=opik_config.api_key)
            default_workspace = client._get_default_workspace()
        except Exception:
            logger.warning(
                "Default workspace not found. Setting workspace to None and enabling interactive mode."
            )
            default_workspace = None

        # Set project name in environment
        os.environ["OPIK_PROJECT_NAME"] = opik_config.project_name

        # Configure Opik
        opik.configure(
            api_key=opik_config.api_key,
            workspace=default_workspace or opik_config.workspace,
            use_local=opik_config.use_local,
            force=True,
        )
        
        logger.info(
            f"Opik configured successfully using workspace '{default_workspace or opik_config.workspace}'"
        )
        
    except Exception as e:
        logger.warning(
            f"Couldn't configure Opik: {e}. Check your OPIK settings in config.toml"
        )


def get_dataset(name: str) -> Optional[opik.Dataset]:
    """Get dataset by name, returns None if not found."""
    client = opik.Opik()
    try:
        dataset = client.get_dataset(name=name)
        return dataset
    except Exception:
        return None


def create_dataset(name: str, description: str, items: List[Dict[str, Any]]) -> opik.Dataset:
    """Create or replace dataset with given items."""
    client = opik.Opik()

    # Delete existing dataset if it exists
    try:
        client.delete_dataset(name=name)
    except Exception:
        pass  # Dataset doesn't exist, that's fine

    # Create new dataset
    dataset = client.create_dataset(name=name, description=description)
    dataset.insert(items)

    logger.info(f"Created dataset '{name}' with {len(items)} items")
    return dataset


def track_llm_call(name: Optional[str] = None):
    """Decorator to track LLM calls with Opik."""
    def decorator(func):
        if name:
            return opik.track(name=name)(func)
        return opik.track()(func)
    
    return decorator
