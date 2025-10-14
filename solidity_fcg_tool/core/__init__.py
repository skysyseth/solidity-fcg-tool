"""Core abstractions for solidity_fcg_tool."""

from .engine_base import AnalysisEngine, EngineCapabilities, EngineError
from .models import (
    CallGraphEdge,
    ContractInfo,
    FunctionIdentifier,
    FunctionInfo,
    ProjectModel,
    SourceLocation,
)

__all__ = [
    "AnalysisEngine",
    "EngineCapabilities",
    "EngineError",
    "CallGraphEdge",
    "ContractInfo",
    "FunctionIdentifier",
    "FunctionInfo",
    "ProjectModel",
    "SourceLocation",
]
