"""
Mixins for the main Zenith class to improve code organization.

These mixins separate different concerns of the main Zenith class:
- MiddlewareMixin: Middleware configuration methods
- RoutingMixin: HTTP route decorator methods
- DocsMixin: OpenAPI/documentation methods
- ServicesMixin: Database and service registration methods
"""

from .docs import DocsMixin
from .middleware import MiddlewareMixin
from .routing import RoutingMixin
from .services import ServicesMixin

__all__ = ["DocsMixin", "MiddlewareMixin", "RoutingMixin", "ServicesMixin"]
