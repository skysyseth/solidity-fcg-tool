"""Command line interface for solidity_fcg_tool."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

from .services.query import (
    DEFAULT_ENGINE_NAME,
    QueryError,
    create_service,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Solidity function call graph and source extraction tool.",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Path to the Solidity project or single .sol file.",
    )
    parser.add_argument(
        "--engine",
        default=DEFAULT_ENGINE_NAME,
        help="Registered engine name to use (default: slither).",
    )
    parser.add_argument(
        "--solc-version",
        dest="solc_version",
        help="Optional explicit solc version passed to the engine.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    query_parser = subparsers.add_parser(
        "query",
        help="Fetch function source by contract and function signature.",
    )
    query_parser.add_argument("--contract", required=True, help="Contract or module name.")
    query_parser.add_argument(
        "--function",
        required=True,
        dest="function_signature",
        help="Function signature, e.g. transfer(address,uint256).",
    )

    call_graph_parser = subparsers.add_parser(
        "call-graph", help="Emit call graph edges optionally filtered by caller."
    )
    call_graph_parser.add_argument("--contract", help="Filter by caller contract.")
    call_graph_parser.add_argument(
        "--function",
        dest="function_signature",
        help="Filter by caller function signature.",
    )

    return parser


def _engine_kwargs_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if args.solc_version:
        kwargs["solc_version"] = args.solc_version
    return kwargs


def handle_query(args: argparse.Namespace) -> Dict[str, Any]:
    service = create_service(
        args.project,
        engine_name=args.engine,
        engine_kwargs=_engine_kwargs_from_args(args),
    )
    return service.get_function_source(args.contract, args.function_signature)


def handle_call_graph(args: argparse.Namespace) -> Dict[str, Any]:
    service = create_service(
        args.project,
        engine_name=args.engine,
        engine_kwargs=_engine_kwargs_from_args(args),
    )
    edges = service.get_call_graph(
        caller_contract=args.contract,
        caller_signature=args.function_signature,
    )
    return {"edges": edges, "metadata": {"engine": args.engine}}


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "query":
            result = handle_query(args)
        elif args.command == "call-graph":
            result = handle_call_graph(args)
        else:  # pragma: no cover - defensive
            parser.error(f"Unknown command {args.command}")
            return 2
    except QueryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
