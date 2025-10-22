"""High-level query interface wrapping analysis engines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

from ..core.engine_base import AnalysisEngine, EngineError
from ..core.models import CallGraphEdge, FunctionIdentifier, FunctionInfo, ProjectModel
from ..engines import resolve_engine

DEFAULT_ENGINE_NAME = "slither"


class QueryError(RuntimeError):
    """Raised when a query cannot be satisfied."""


@dataclass
class CallGraphRecord:
    """Serializable representation of a call graph edge."""

    caller: str
    callee: str

    @classmethod
    def from_edge(cls, edge: CallGraphEdge) -> "CallGraphRecord":
        return cls(caller=edge.caller.display_name(), callee=edge.callee.display_name())

    def as_dict(self) -> Dict[str, str]:
        return {"caller": self.caller, "callee": self.callee}


class QueryService:
    """Entrypoint for querying Solidity analysis data."""

    def __init__(
        self,
        project_path: str,
        *,
        engine_name: str = DEFAULT_ENGINE_NAME,
        engine_kwargs: Optional[Dict[str, object]] = None,
    ) -> None:
        self.project_path = project_path
        self.engine_name = engine_name
        self.engine_kwargs = engine_kwargs or {}
        self._engine: Optional[AnalysisEngine] = None
        self._project: Optional[ProjectModel] = None

        project_root = Path(project_path).resolve()
        if project_root.is_file():
            project_root = project_root.parent
        self._project_root = project_root

    def _ensure_engine(self) -> AnalysisEngine:
        if self._engine is None:
            try:
                registration = resolve_engine(self.engine_name)
            except KeyError as exc:
                raise QueryError(f"Engine {self.engine_name} is not registered") from exc
            try:
                self._engine = registration.factory(
                    self.project_path, **self.engine_kwargs
                )
            except TypeError as exc:
                raise QueryError(
                    f"Engine {self.engine_name} does not accept provided parameters: {exc}"
                ) from exc
        return self._engine

    def _ensure_project(self) -> ProjectModel:
        if self._project is None:
            engine = self._ensure_engine()
            try:
                self._project = engine.ensure_loaded()
            except EngineError as exc:
                raise QueryError(str(exc)) from exc
        return self._project

    def list_contracts(self) -> List[str]:
        """Return the list of contract/module names."""
        project = self._ensure_project()
        return [contract.name for contract in project.iter_contracts()]

    def get_function(self, contract: str, function_signature: str) -> FunctionInfo:
        """Retrieve a function metadata structure."""
        engine = self._ensure_engine()
        identifier = FunctionIdentifier(contract, function_signature)
        function = engine.get_function(identifier)
        if function is None:
            raise QueryError(
                f"Function {function_signature} not found in contract {contract}"
            )
        return function

    def get_function_source(
        self, contract: str, function_signature: str
    ) -> Dict[str, object]:
        """Return function information as a serializable dictionary."""
        project = self._ensure_project()
        function = self.get_function(contract, function_signature)
        return function.as_dict(project, self._format_path)

    def iter_call_graph(
        self,
        *,
        caller_contract: Optional[str] = None,
        caller_signature: Optional[str] = None,
    ) -> Iterator[CallGraphRecord]:
        """Iterate over call graph edges with optional filtering."""
        self._ensure_project()
        engine = self._ensure_engine()
        try:
            edges: Iterable[CallGraphEdge] = engine.iter_call_graph()
        except EngineError as exc:
            raise QueryError(str(exc)) from exc

        for edge in edges:
            if caller_contract and edge.caller.contract != caller_contract:
                continue
            if caller_signature and edge.caller.signature != caller_signature:
                continue
            yield CallGraphRecord.from_edge(edge)

    def get_call_graph(
        self,
        *,
        caller_contract: Optional[str] = None,
        caller_signature: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Materialize call graph edges as dictionaries."""
        return [
            record.as_dict()
            for record in self.iter_call_graph(
                caller_contract=caller_contract, caller_signature=caller_signature
            )
        ]

    def _format_path(self, raw_path: str) -> str:
        if not raw_path:
            return raw_path
        path = Path(raw_path)
        try:
            resolved = path.resolve(strict=False)
        except OSError:
            resolved = path

        return str(resolved)


def create_service(
    project_path: str,
    *,
    engine_name: str = DEFAULT_ENGINE_NAME,
    engine_kwargs: Optional[Dict[str, object]] = None,
) -> QueryService:
    """Helper to instantiate a QueryService."""
    return QueryService(
        project_path,
        engine_name=engine_name,
        engine_kwargs=engine_kwargs,
    )


def get_function_source(
    project_path: str,
    contract: str,
    function_signature: str,
    *,
    engine_name: str = DEFAULT_ENGINE_NAME,
    engine_kwargs: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """One-shot helper mirroring the QueryService API."""
    service = create_service(
        project_path,
        engine_name=engine_name,
        engine_kwargs=engine_kwargs,
    )
    return service.get_function_source(contract, function_signature)
