"""
Mixins for the main Zenith class to improve code organization.

These mixins separate different concerns of the main Zenith class:
- MiddlewareMixin: Middleware configuration methods
- RoutingMixin: HTTP route decorator methods  
- DocsMixin: OpenAPI/documentation methods
- ServicesMixin: Database and service registration methods
"""

from .middleware import MiddlewareMixin
from .routing import RoutingMixin
from .docs import DocsMixin
from .services import ServicesMixin

__all__ = [
    "MiddlewareMixin", 
    "RoutingMixin", 
    "DocsMixin", 
    "ServicesMixin"
]