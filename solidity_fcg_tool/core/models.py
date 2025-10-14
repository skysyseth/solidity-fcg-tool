"""Data models shared across solidity_fcg_tool components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class SourceLocation:
    """Precise location for a fragment in source code."""

    file: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class FunctionIdentifier:
    """Uniquely identify a function by contract/module and signature."""

    contract: str
    signature: str

    def display_name(self) -> str:
        """Human readable identifier."""
        return f"{self.contract}.{self.signature}"


@dataclass
class FunctionInfo:
    """Metadata for a Solidity function."""

    identifier: FunctionIdentifier
    visibility: str
    mutability: Optional[str]
    state_variables_read: List[str] = field(default_factory=list)
    state_variables_written: List[str] = field(default_factory=list)
    source: str = ""
    location: Optional[SourceLocation] = None
    calls: List[FunctionIdentifier] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        """Serialize into a JSON friendly dictionary."""
        return {
            "contract": self.identifier.contract,
            "function": self.identifier.signature,
            "visibility": self.visibility,
            "mutability": self.mutability,
            "source": self.source,
            "location": None
            if self.location is None
            else {
                "file": self.location.file,
                "start_line": self.location.start_line,
                "start_column": self.location.start_column,
                "end_line": self.location.end_line,
                "end_column": self.location.end_column,
            },
            "calls": [call.display_name() for call in self.calls],
            "reads": list(self.state_variables_read),
            "writes": list(self.state_variables_written),
        }


@dataclass
class ContractInfo:
    """Representation of a Solidity contract/library/interface."""

    name: str
    kind: str
    filepath: str
    inheritance: List[str] = field(default_factory=list)
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    raw_source: Optional[str] = None

    def get_function(self, signature: str) -> Optional[FunctionInfo]:
        """Fetch a function by signature if available."""
        return self.functions.get(signature)

    def iter_functions(self) -> Iterable[FunctionInfo]:
        """Iterate over all functions in insertion order."""
        return self.functions.values()


@dataclass
class ProjectModel:
    """Complete view of a parsed Solidity project."""

    contracts: Dict[str, ContractInfo] = field(default_factory=dict)
    engine_metadata: Dict[str, object] = field(default_factory=dict)

    def get_contract(self, name: str) -> Optional[ContractInfo]:
        return self.contracts.get(name)

    def register_contract(self, contract: ContractInfo) -> None:
        self.contracts[contract.name] = contract

    def iter_contracts(self) -> Iterable[ContractInfo]:
        return self.contracts.values()


@dataclass(frozen=True)
class CallGraphEdge:
    """Edge in the function call graph."""

    caller: FunctionIdentifier
    callee: FunctionIdentifier
