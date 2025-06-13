"""
群体Agent沟通API服务
"""

from .group_negotiation import GroupNegotiationService
from .websocket import ConnectionManager

__all__ = [
    # 新的简化服务
    "GroupNegotiationService",
    "ConnectionManager"
]