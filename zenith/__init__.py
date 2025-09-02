"""
Zenith Framework - Modern Python web framework with real-time features.

The perfect blend of:
- FastAPI's modern Python patterns and type safety
- Rails' developer experience and conventions
- Phoenix's real-time features and architecture

Build server-rendered interactive UIs with minimal JavaScript.
"""

from zenith.__version__ import __version__

__author__ = "Nick"

# Main framework classes
from zenith.core.application import Application
from zenith.core.config import Config

# Contexts
from zenith.core.context import Context as BaseContext

# Routing and dependency injection
from zenith.core.routing import Auth, Context, File, Router
from zenith.zenith import Zenith, create_app

__all__ = [
    # Core classes
    "Application",
    "Auth",
    # Base classes
    "BaseContext",
    "Config",
    "Context",
    "File",
    # Routing
    "Router",
    # Main entry points
    "Zenith",
    "create_app",
]
