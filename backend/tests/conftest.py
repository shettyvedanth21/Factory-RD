"""
Pytest configuration for async tests.
"""
import pytest

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


def pytest_configure(config):
    """Configure pytest-asyncio mode."""
    config.option.asyncio_mode = "auto"
