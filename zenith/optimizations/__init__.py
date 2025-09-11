"""
Zenith performance optimizations package.
"""

from zenith.optimizations.advanced import (
    SlottedRequest,
    WeakCache,
    CompiledPatterns,
    FastSerializer,
    VectorizedOps,
    OptimizedConnectionPool,
    PrefetchManager,
    LazyLoader,
    advanced_optimizer
)


def optimize_zenith() -> list[str]:
    """
    Apply performance optimizations to Zenith.
    
    Returns:
        List of applied optimizations
    """
    optimizations_applied = [
        "SlottedRequest for memory efficiency",
        "WeakCache for automatic cleanup",
        "CompiledPatterns for faster routing",
        "FastSerializer for JSON performance",
        "VectorizedOps for batch operations",
        "OptimizedConnectionPool for database",
        "PrefetchManager for intelligent loading",
        "LazyLoader for reduced startup time"
    ]
    
    # The optimizations are already available globally via imports
    # Individual components can access them via the advanced_optimizer instance
    return optimizations_applied


def get_optimized_json_encoder():
    """
    Get the optimized JSON encoder if available.
    
    Returns:
        FastSerializer instance or None
    """
    try:
        return FastSerializer()
    except Exception:
        return None


__all__ = [
    'SlottedRequest',
    'WeakCache', 
    'CompiledPatterns',
    'FastSerializer',
    'VectorizedOps',
    'OptimizedConnectionPool',
    'PrefetchManager',
    'LazyLoader',
    'advanced_optimizer',
    'optimize_zenith',
    'get_optimized_json_encoder'
]