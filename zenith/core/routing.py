"""
Zenith routing system with dependency injection.

This module provides the main routing interface and re-exports everything
from the refactored routing package structure for backward compatibility.
"""

# Re-export everything from the routing package
from zenith.core.routing import *  # noqa: F403

# This ensures backward compatibility while allowing the internal
# structure to be refactored into separate modules
