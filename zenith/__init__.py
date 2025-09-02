"""
Zenith Framework - Modern Python web framework with real-time features.

The perfect blend of:
- FastAPI's modern Python patterns and type safety
- Rails' developer experience and conventions
- Phoenix's real-time features and architecture

Build server-rendered interactive UIs with minimal JavaScript.
"""

__version__ = "0.0.1-dev"
__author__ = "Nick"

# Main framework classes
from zenith.zenith import Zenith, create_app
from zenith.core.application import Application
from zenith.core.config import Config

# Routing and dependency injection
from zenith.core.routing import Router, Context, Auth, File

# Contexts
from zenith.core.context import Context as BaseContext

__all__ = [
    # Main entry points
    "Zenith",
    "create_app",
    # Core classes
    "Application",
    "Config",
    # Routing
    "Router",
    "Context",
    "Auth",
    "File",
    # Base classes
    "BaseContext",
]
