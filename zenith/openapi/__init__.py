"""
OpenAPI 3.0 specification generation for Zenith applications.

Automatically generates OpenAPI specs from route definitions,
type hints, and Pydantic models.
"""

from .generator import OpenAPIGenerator, generate_openapi_spec
from .docs import setup_docs_routes

__all__ = [
    "OpenAPIGenerator",
    "generate_openapi_spec", 
    "setup_docs_routes"
]