"""Simple registry for available analysis engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, TypeVar

from ..core.engine_base import AnalysisEngine, EngineCapabilities

EngineFactory = Callable[..., AnalysisEngine]
TAnalysisEngine = TypeVar("TAnalysisEngine", bound=AnalysisEngine)


@dataclass
class EngineRegistration:
    """Registered engine metadata."""

    name: str
    factory: EngineFactory
    description: str = ""
    capabilities: Optional[EngineCapabilities] = None


class EngineRegistry:
    """Holds named engine registrations."""

    def __init__(self) -> None:
        self._engines: Dict[str, EngineRegistration] = {}

    def register(self, registration: EngineRegistration, *, override: bool = False) -> None:
        if registration.name in self._engines and not override:
            raise ValueError(f"Engine {registration.name} already registered")
        self._engines[registration.name] = registration

    def get(self, name: str) -> EngineRegistration:
        try:
            return self._engines[name]
        except KeyError as exc:
            raise KeyError(f"Engine {name} is not registered") from exc

    def names(self) -> Iterable[str]:
        return self._engines.keys()

    def items(self) -> Iterable[EngineRegistration]:
        return self._engines.values()


ENGINE_REGISTRY = EngineRegistry()


def register_engine(
    name: str,
    factory: EngineFactory,
    *,
    description: str = "",
    capabilities: Optional[EngineCapabilities] = None,
    override: bool = False,
) -> None:
    """Register a new engine implementation."""
    ENGINE_REGISTRY.register(
        EngineRegistration(
            name=name,
            factory=factory,
            description=description,
            capabilities=capabilities,
        ),
        override=override,
    )


def resolve_engine(name: str) -> EngineRegistration:
    """Fetch a previously registered engine registration."""
    return ENGINE_REGISTRY.get(name)
