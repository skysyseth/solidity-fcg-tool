"""Slither-based engine implementation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

from ..core.engine_base import AnalysisEngine, EngineCapabilities, EngineError
from ..core.models import (
    CallGraphEdge,
    ContractInfo,
    FunctionIdentifier,
    FunctionParameter,
    FunctionInfo,
    ProjectModel,
    SourceLocation,
)
from .registry import register_engine


class SlitherEngine(AnalysisEngine):
    """Adapter around slither-analyzer."""

    name = "slither"
    DEFAULT_CAPABILITIES = EngineCapabilities(
        call_graph=True,
        state_modifiers=True,
        inheritance_resolution=True,
    )

    def __init__(self, project_path: str, *, solc_version: Optional[str] = None) -> None:
        super().__init__(project_path, solc_version=solc_version)
        self._slither = None
        self._call_graph_cache: Optional[Tuple[CallGraphEdge, ...]] = None

    @property
    def capabilities(self) -> EngineCapabilities:
        return self.DEFAULT_CAPABILITIES

    def load(self) -> ProjectModel:
        slither = self._build_slither()
        project = ProjectModel(
            engine_metadata={
                "engine": self.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        project.engine_metadata.update(self._collect_engine_metadata(slither))

        for contract in slither.contracts:
            project.register_contract(self._convert_contract(contract))

        self._slither = slither
        self._call_graph_cache = tuple(self._collect_call_edges(project))
        self._project_model = project
        return project

    def _build_slither(self):
        try:
            from slither.slither import Slither as SlitherAnalyzer
        except ImportError as exc:
            raise EngineError(
                "Slither engine requires the slither-analyzer package. "
                "Install via `pip install slither-analyzer`."
            ) from exc

        kwargs = {}
        if self.solc_version:
            kwargs["solc"] = self.solc_version

        try:
            return SlitherAnalyzer(self.project_path, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            raise EngineError(f"Failed to analyze project with Slither: {exc}") from exc

    def _collect_engine_metadata(self, slither) -> dict:
        metadata = {}
        compilation_unit = getattr(slither, "compilation_unit", None)
        if compilation_unit is not None:
            compiler_version = getattr(compilation_unit, "compiler_version", None)
            if compiler_version:
                metadata["solc_version"] = compiler_version
        metadata["slither_version"] = getattr(slither, "__version__", None)
        return metadata

    def _convert_contract(self, contract) -> ContractInfo:
        source_mapping = getattr(contract, "source_mapping", None)
        filepath = self._resolve_filename(source_mapping)
        inheritance = [base_contract.name for base_contract in getattr(contract, "inheritance", [])]
        raw_source = getattr(contract, "source_code", None)
        contract_info = ContractInfo(
            name=contract.name,
            kind=getattr(contract, "contract_kind", "contract"),
            filepath=filepath or getattr(contract, "source_path", ""),
            inheritance=inheritance,
            raw_source=raw_source,
        )

        functions = self._iter_contract_functions(contract)
        for function in functions:
            function_info = self._convert_function(function)
            contract_info.functions[function_info.identifier.signature] = function_info
        return contract_info

    @staticmethod
    def _iter_contract_functions(contract) -> Iterable:
        """Yield declared functions, including constructors and fallback."""
        declared = getattr(contract, "functions_declared", None)
        if declared is not None:
            return declared
        return getattr(contract, "functions", [])

    def _convert_function(self, function) -> FunctionInfo:
        signature = self._extract_signature(function)
        identifier = FunctionIdentifier(function.contract.name, signature)

        location = self._build_location(getattr(function, "source_mapping", None))
        source_code = (getattr(function, "source_code", None) or "").strip()
        if not source_code and location is not None:
            source_code = self._read_source_snippet(location)

        reads = self._normalize_state_variables(getattr(function, "state_variables_read", []))
        writes = self._normalize_state_variables(getattr(function, "state_variables_written", []))

        calls = self._extract_calls(function)
        parameters = self._convert_parameters(function)

        return FunctionInfo(
            identifier=identifier,
            visibility=getattr(function, "visibility", "public"),
            mutability=getattr(function, "view", None) or getattr(function, "mutability", None),
            parameters=parameters,
            state_variables_read=reads,
            state_variables_written=writes,
            source=source_code,
            location=location,
            calls=calls,
        )

    def _extract_signature(self, function) -> str:
        # Prefer the Solidity signature without the leading keyword.
        for attr in ("signature_str", "canonical_name", "name"):
            value = getattr(function, attr, None)
            if not value:
                continue
            if attr == "canonical_name" and "." in value:
                # canonical_name looks like Contract.function(type)
                value = value.split(".", 1)[1]
            return self._normalize_signature(value)
        return self._normalize_signature(getattr(function, "name", "<unknown>"))

    @staticmethod
    def _normalize_signature(signature: str) -> str:
        if not signature:
            return signature
        marker = " returns"
        if marker in signature:
            signature = signature.split(marker, 1)[0].strip()
        return signature.strip()

    def _build_location(self, source_mapping) -> Optional[SourceLocation]:
        if source_mapping is None:
            return None

        filename = self._resolve_filename(source_mapping)
        lines = list(getattr(source_mapping, "lines", []) or [])
        lines.sort()
        start_line = lines[0] if lines else -1
        end_line = lines[-1] if lines else -1

        start_column = getattr(source_mapping, "start_column", 1)
        end_column = getattr(source_mapping, "end_column", 1)
        if start_column is None:
            start_column = 1
        if end_column is None:
            end_column = 1

        return SourceLocation(
            file=filename or "",
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
        )

    @staticmethod
    def _resolve_filename(source_mapping) -> Optional[str]:
        if source_mapping is None:
            return None
        filename = getattr(source_mapping, "filename", None)
        if not filename:
            return None
        for attr in ("absolute", "full_path", "path"):
            value = getattr(filename, attr, None)
            if value:
                return value
        return str(filename)

    def _read_source_snippet(self, location: SourceLocation) -> str:
        if not location.file or location.start_line < 0 or location.end_line < 0:
            return ""
        try:
            with open(location.file, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
        except FileNotFoundError:
            return ""

        start_idx = max(location.start_line - 1, 0)
        end_idx = max(location.end_line, start_idx + 1)
        return "".join(lines[start_idx:end_idx])

    def _normalize_state_variables(self, variables: Sequence) -> List[str]:
        results: List[str] = []
        for variable in variables or []:
            name = getattr(variable, "canonical_name", None) or getattr(variable, "name", None)
            if name:
                results.append(str(name))
        return results

    def _extract_calls(self, function) -> List[FunctionIdentifier]:
        calls: List[FunctionIdentifier] = []
        seen = set()

        def append_call(callee) -> None:
            if callee is None:
                return

            target = callee
            for attr in ("function", "called", "function_called", "function_callee"):
                candidate = getattr(target, attr, None)
                if candidate is not None:
                    target = candidate
                    break

            contract_obj = getattr(target, "contract", None)
            if contract_obj is None:
                return

            signature = self._extract_signature(target)
            identifier = (contract_obj.name, signature)
            if identifier in seen:
                return
            seen.add(identifier)
            calls.append(FunctionIdentifier(*identifier))

        for callee in self._iterate_attribute(
            function, ("all_internal_calls", "internal_calls", "functions_called")
        ):
            append_call(callee)

        for callee in self._iterate_attribute(function, ("external_calls_as_functions",)):
            append_call(callee)

        return calls

    def _convert_parameters(self, function) -> List[FunctionParameter]:
        parameters = []
        for parameter in getattr(function, "parameters", []) or []:
            param_type = getattr(parameter, "type", None)
            param_name = getattr(parameter, "name", None)
            parameters.append(
                FunctionParameter(
                    name=str(param_name) if param_name else "",
                    type=str(param_type) if param_type else "",
                )
            )
        return parameters

    @staticmethod
    def _iterate_attribute(obj, names: Tuple[str, ...]) -> Iterable:
        for name in names:
            value = getattr(obj, name, None)
            if value is None:
                continue
            if callable(value):
                try:
                    value = value()
                except TypeError:
                    continue
            if value is None:
                continue
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    yield item
            else:
                yield value

    def _collect_call_edges(self, project: ProjectModel) -> List[CallGraphEdge]:
        edges: List[CallGraphEdge] = []
        for contract in project.iter_contracts():
            for function in contract.iter_functions():
                for callee in function.calls:
                    edges.append(CallGraphEdge(function.identifier, callee))
        return edges

    def _iter_call_graph_impl(self) -> Iterable[CallGraphEdge]:
        if self._call_graph_cache is None:
            raise EngineError("Call graph not available before loading the project")
        return self._call_graph_cache


register_engine(
    SlitherEngine.name,
    SlitherEngine,
    description="Solidity static analysis powered by slither-analyzer.",
    capabilities=SlitherEngine.DEFAULT_CAPABILITIES,
    override=True,
)
