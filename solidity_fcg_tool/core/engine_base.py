"""Abstract engine definition for solidity_fcg_tool."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Optional

from .models import CallGraphEdge, ContractInfo, FunctionIdentifier, FunctionInfo, ProjectModel


class EngineError(RuntimeError):
    """Base error for analysis engine failures."""


@dataclass(frozen=True)
class EngineCapabilities:
    """List the optional features supported by an engine implementation."""

    call_graph: bool = False
    state_modifiers: bool = False
    inheritance_resolution: bool = False


class AnalysisEngine(ABC):
    """Common interface implemented by all analysis engines."""

    name: str = "abstract"

    def __init__(self, project_path: str, *, solc_version: Optional[str] = None) -> None:
        self.project_path = project_path
        self.solc_version = solc_version
        self._project_model: Optional[ProjectModel] = None

    @property
    def capabilities(self) -> EngineCapabilities:
        """Return capabilities supported by the engine."""
        return EngineCapabilities()

    @abstractmethod
    def load(self) -> ProjectModel:
        """Parse the project and populate the internal project model."""

    def ensure_loaded(self) -> ProjectModel:
        """Lazily load project information."""
        if self._project_model is None:
            self._project_model = self.load()
        return self._project_model

    def get_contract(self, contract_name: str) -> Optional[ContractInfo]:
        """Retrieve contract metadata."""
        return self.ensure_loaded().get_contract(contract_name)

    def get_function(self, identifier: FunctionIdentifier) -> Optional[FunctionInfo]:
        """Retrieve function metadata."""
        contract = self.get_contract(identifier.contract)
        if contract is None:
            return None
        return contract.get_function(identifier.signature)

    def iter_contracts(self) -> Iterable[ContractInfo]:
        """Iterate through every contract provided by the engine."""
        return self.ensure_loaded().iter_contracts()

    def iter_call_graph(self) -> Iterable[CallGraphEdge]:
        """Iterate over call graph edges if supported."""
        if not self.capabilities.call_graph:
            raise EngineError(f"Engine {self.name} does not support call graph generation")
        return self._iter_call_graph_impl()

    def _iter_call_graph_impl(self) -> Iterable[CallGraphEdge]:
        """Internal implementation for call graph iteration."""
        raise EngineError("Call graph iteration not implemented by this engine")
