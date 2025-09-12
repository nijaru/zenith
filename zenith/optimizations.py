"""
Performance optimizations for Zenith framework.

This module provides drop-in performance enhancements including:
- uvloop for faster async I/O
- msgspec for ultra-fast JSON serialization
- orjson as a fallback JSON handler
"""

import sys
import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Track which optimizations are available
UVLOOP_AVAILABLE = False
MSGSPEC_AVAILABLE = False
ORJSON_AVAILABLE = False

# Try to import performance libraries
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    uvloop = None

try:
    import msgspec
    MSGSPEC_AVAILABLE = True
except ImportError:
    msgspec = None

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    orjson = None


def install_uvloop() -> bool:
    """
    Install uvloop as the default event loop policy.
    
    Returns:
        True if uvloop was installed, False otherwise
    """
    if not UVLOOP_AVAILABLE:
        logger.debug("uvloop not available, using default asyncio event loop")
        return False
    
    try:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("uvloop installed as default event loop")
        return True
    except Exception as e:
        logger.warning(f"Failed to install uvloop: {e}")
        return False


def get_optimized_json_encoder():
    """
    Get the best available JSON encoder.
    
    Priority:
    1. msgspec (fastest with validation)
    2. orjson (fastest pure JSON)
    3. standard json (fallback)
    """
    if MSGSPEC_AVAILABLE:
        return create_msgspec_encoder()
    elif ORJSON_AVAILABLE:
        return create_orjson_encoder()
    else:
        return None  # Use standard json


def create_msgspec_encoder():
    """Create a msgspec-based JSON encoder."""
    import msgspec
    from datetime import datetime, date, time
    from decimal import Decimal
    from uuid import UUID
    from pathlib import Path
    from enum import Enum
    
    # Custom encoder hook for non-standard types
    def encode_hook(obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, (Decimal, UUID, Path)):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, bytes):
            import base64
            return base64.b64encode(obj).decode('utf-8')
        elif isinstance(obj, set):
            return list(obj)
        # Let msgspec handle the rest
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    encoder = msgspec.json.Encoder(enc_hook=encode_hook)
    decoder = msgspec.json.Decoder()
    
    def dumps(obj, **kwargs):
        # msgspec returns bytes, convert to str for compatibility
        return encoder.encode(obj).decode('utf-8')
    
    def loads(data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        return decoder.decode(data)
    
    return {
        'dumps': dumps,
        'loads': loads,
        'name': 'msgspec'
    }


def create_orjson_encoder():
    """Create an orjson-based JSON encoder."""
    import orjson
    from datetime import datetime, date, time
    from decimal import Decimal
    from uuid import UUID
    from pathlib import Path
    from enum import Enum
    
    def default(obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, (Decimal, UUID, Path)):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, bytes):
            import base64
            return base64.b64encode(obj).decode('utf-8')
        elif isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def dumps(obj, **kwargs):
        # orjson returns bytes, convert to str for compatibility
        return orjson.dumps(obj, default=default).decode('utf-8')
    
    def loads(data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        return orjson.loads(data)
    
    return {
        'dumps': dumps,
        'loads': loads,
        'name': 'orjson'
    }


def optimize_zenith():
    """
    Apply all available optimizations to Zenith.
    
    This should be called before creating the Zenith application.
    """
    optimizations = []
    
    # Install uvloop if available
    if install_uvloop():
        optimizations.append("uvloop")
    
    # Check JSON optimization availability
    if MSGSPEC_AVAILABLE:
        optimizations.append("msgspec")
    elif ORJSON_AVAILABLE:
        optimizations.append("orjson")
    
    if optimizations:
        logger.info(f"Zenith optimizations enabled: {', '.join(optimizations)}")
    else:
        logger.info("No additional optimizations available")
    
    return optimizations


def get_optimization_status() -> dict:
    """
    Get the status of available optimizations.
    
    Returns:
        Dictionary with optimization availability
    """
    return {
        'uvloop': UVLOOP_AVAILABLE,
        'msgspec': MSGSPEC_AVAILABLE,
        'orjson': ORJSON_AVAILABLE,
        'event_loop': 'uvloop' if UVLOOP_AVAILABLE and isinstance(
            asyncio.get_event_loop_policy(), 
            uvloop.EventLoopPolicy if uvloop else type(None)
        ) else 'asyncio',
        'json_encoder': (
            'msgspec' if MSGSPEC_AVAILABLE else
            'orjson' if ORJSON_AVAILABLE else
            'standard'
        )
    }


# Auto-optimize on import if running as main application
if not any(test in sys.argv[0] for test in ['pytest', 'test']):
    # Don't auto-optimize during tests
    optimize_zenith()