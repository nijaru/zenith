"""
Custom JSON encoder for Zenith framework.

Handles datetime objects and other non-JSON-serializable types.
Automatically uses the fastest available JSON library (msgspec > orjson > standard).
"""

import json
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

# Try to import optimized JSON handlers
_json_handler = None


def _setup_json_handler():
    """Setup the best available JSON handler."""
    global _json_handler

    if _json_handler is not None:
        return _json_handler

    try:
        from zenith.optimizations import get_optimized_json_encoder

        handler = get_optimized_json_encoder()
        if handler:
            _json_handler = handler
            return _json_handler
    except ImportError:
        pass

    # Fallback to standard json
    _json_handler = {"name": "standard", "dumps": None, "loads": None}
    return _json_handler


class ZenithJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles common Python types.

    Supports:
    - datetime, date, time objects (ISO format)
    - Decimal (as string to preserve precision)
    - UUID (as string)
    - Path (as string)
    - Enum (as value)
    - Pydantic models (via model_dump)
    - bytes (as base64)
    """

    def default(self, obj: Any) -> Any:
        """Convert non-JSON-serializable objects."""
        # Datetime types
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()

        # Numeric types
        elif isinstance(obj, (Decimal, UUID, Path)):
            return str(obj)

        # Enums
        elif isinstance(obj, Enum):
            return obj.value

        # Pydantic models
        elif isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")

        # Binary data
        elif isinstance(obj, bytes):
            import base64

            return base64.b64encode(obj).decode("utf-8")

        # Sets (convert to list)
        elif isinstance(obj, set):
            return list(obj)

        # Fall back to default
        return super().default(obj)


def _json_dumps(obj: Any, **kwargs) -> str:
    """
    Serialize obj to JSON string using the best available JSON encoder.

    Uses msgspec > orjson > standard json based on availability.

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments for json.dumps

    Returns:
        JSON string
    """
    handler = _setup_json_handler()

    # Use optimized handler if available
    if handler["dumps"]:
        try:
            return handler["dumps"](obj)
        except (TypeError, ValueError, OverflowError, RecursionError):
            # Fall back to standard if optimized handler fails
            pass

    # Standard JSON fallback
    kwargs.setdefault("cls", ZenithJSONEncoder)
    kwargs.setdefault("ensure_ascii", False)  # Support Unicode
    return json.dumps(obj, **kwargs)


def _json_loads(data: str | bytes) -> Any:
    """
    Deserialize JSON string using the best available JSON decoder.

    Uses msgspec > orjson > standard json based on availability.

    Args:
        data: JSON string or bytes to deserialize

    Returns:
        Deserialized object
    """
    handler = _setup_json_handler()

    # Use optimized handler if available
    if handler["loads"]:
        try:
            return handler["loads"](data)
        except (TypeError, ValueError, UnicodeDecodeError):
            # Fall back to standard if optimized handler fails
            pass

    # Standard JSON fallback
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return json.loads(data)
