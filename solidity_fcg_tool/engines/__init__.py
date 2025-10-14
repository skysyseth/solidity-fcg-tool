"""Engine implementations and registry."""

from .registry import (
    ENGINE_REGISTRY,
    EngineFactory,
    EngineRegistration,
    register_engine,
    resolve_engine,
)

__all__ = [
    "ENGINE_REGISTRY",
    "EngineFactory",
    "EngineRegistration",
    "register_engine",
    "resolve_engine",
]

# Ensure default engines are registered on import.
from . import slither_engine  # noqa: F401,E402
