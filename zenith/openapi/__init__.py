"""
OpenAPI 3.0 specification generation for Zenith applications.

Automatically generates OpenAPI specs from route definitions,
type hints, and Pydantic models.
"""

from .docs import setup_docs_routes
from .generator import OpenAPIGenerator, generate_openapi_spec

__all__ = ["OpenAPIGenerator", "generate_openapi_spec", "setup_docs_routes"]
