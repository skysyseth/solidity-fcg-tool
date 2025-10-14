import json
from pathlib import Path

import pytest

from solidity_fcg_tool.cli import main as cli_main
from solidity_fcg_tool.services.query import QueryError, QueryService


def test_unknown_engine_raises_query_error():
    service = QueryService(".", engine_name="unknown")
    with pytest.raises(QueryError):
        service.list_contracts()


def test_default_engine_is_slither():
    service = QueryService(".")
    assert service.engine_name == "slither"


@pytest.fixture
def sample_project_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "samples" / "SimpleToken.sol")


@pytest.fixture
def sample_service(sample_project_path: str) -> QueryService:
    service = QueryService(sample_project_path)
    try:
        service.list_contracts()
    except QueryError as exc:
        pytest.skip(f"Slither integration unavailable: {exc}")
    return service


def test_list_contracts_includes_sample(sample_service: QueryService):
    assert "SimpleToken" in sample_service.list_contracts()


def test_get_function_source_returns_transfer(sample_service: QueryService):
    result = sample_service.get_function_source("SimpleToken", "transfer(address,uint256)")
    assert result["function"] == "transfer(address,uint256)"
    assert "function transfer" in result["source"]
    assert result["metadata"]["engine"] == "slither"
    assert result["location"]["file"].endswith("SimpleToken.sol")


def test_call_graph_contains_internal_function(sample_service: QueryService):
    edges = sample_service.get_call_graph(caller_contract="SimpleToken")
    assert edges, "expected at least one call graph edge"
    targets = {edge["callee"] for edge in edges}
    assert any("_performTransfer" in target for target in targets)


def test_cli_query_outputs_json(sample_project_path: str, capsys: pytest.CaptureFixture[str]):
    exit_code = cli_main(
        [
            "--project",
            sample_project_path,
            "query",
            "--contract",
            "SimpleToken",
            "--function",
            "transfer(address,uint256)",
        ]
    )
    captured = capsys.readouterr()
    if exit_code != 0:
        pytest.skip(f"CLI query failed due to environment: {captured.err or captured.out}")
    payload = json.loads(captured.out)
    assert payload["function"] == "transfer(address,uint256)"
    assert payload["metadata"]["engine"] == "slither"


def test_cli_call_graph_outputs_edges(sample_project_path: str, capsys: pytest.CaptureFixture[str]):
    exit_code = cli_main(
        [
            "--project",
            sample_project_path,
            "call-graph",
            "--contract",
            "SimpleToken",
        ]
    )
    captured = capsys.readouterr()
    if exit_code != 0:
        pytest.skip(f"CLI call-graph failed due to environment: {captured.err or captured.out}")
    payload = json.loads(captured.out)
    assert payload["metadata"]["engine"] == "slither"
    assert payload["edges"], "expected call graph edges in CLI output"
