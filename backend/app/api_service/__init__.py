"""
Multi-Agent Communication API Service
"""

from .group_negotiation import GroupNegotiationService
from .websocket import ConnectionManager

__all__ = [
    # New simplified service
    "GroupNegotiationService",
    "ConnectionManager"
]