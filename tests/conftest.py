"""
Pytest configuration and fixtures for Zenith tests.
"""

import warnings

import pytest


@pytest.fixture(autouse=True)
def suppress_sqlalchemy_gc_warnings():
    """
    Suppress SQLAlchemy GC cleanup warnings in test environment.

    These warnings occur because pytest-asyncio creates new event loops per test,
    and when the interpreter shuts down, the garbage collector finds connections
    that weren't explicitly closed. This doesn't affect production code where
    connections are properly managed through the application lifecycle.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="The garbage collector is trying to clean up",
            category=Warning,
        )
        yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_sqlalchemy_on_exit():
    """Ensure SQLAlchemy engines are disposed at session end."""
    yield
    # Force garbage collection to clean up before interpreter shutdown
    import gc

    gc.collect()
