# solidity-fcg-tool

`solidity-fcg-tool` packages a Solidity static analysis workflow that extracts module/function source code and call graph data. The first release uses [Slither](https://github.com/crytic/slither) under the hood, while keeping the analysis engine pluggable so Tree-sitter, Solar, or other backends can be added later.

## Features
- **Engine abstraction** – `core.engine_base.AnalysisEngine` defines the contract for all engines and allows hot-swapping implementations.
- **Rich data model** – function source, parameters, state variable access, locations, and call relationships.
- **Service layer** – `services.query.QueryService` exposes Python APIs plus a JSON-emitting CLI for downstream tooling (e.g., AI assistants).
- **Extensible registry** – register additional engines without touching higher-level services.

## Installation
Once published, install via pip:
```bash
pip install solidity-fcg-tool
```

For local development:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .[dev]
```

> A compatible `solc` binary is required. Install with `py-solc-x` or reuse an existing compiler on your system.

## CLI Usage
### Function source lookup
```bash
python -m solidity_fcg_tool \
  --project samples/SimpleToken.sol \
  --engine slither \
  query \
  --contract SimpleToken \
  --function "transfer(address,uint256)"
```
Example (truncated) response:
```json
{
  "contract": "SimpleToken",
  "function": "transfer(address,uint256)",
  "source": "    function transfer(address to, uint256 amount) external returns (bool) {\n        _performTransfer(msg.sender, to, amount);\n        return true;\n    }\n",
  "location": {
    "file": "/absolute/path/to/solidity-fcg-tool/samples/SimpleToken.sol",
    "start_line": 17,
    "end_line": 20
  },
  "parameter": [
    { "name": "to", "type": "address" },
    { "name": "amount", "type": "uint256" }
  ],
  "calls": [
    {
      "file": "/absolute/path/to/solidity-fcg-tool/samples/SimpleToken.sol",
      "module": "SimpleToken",
      "function": "_performTransfer(address,address,uint256)"
    }
  ]
}
```

### Call graph extraction
```bash
python -m solidity_fcg_tool \
  --project samples/SimpleToken.sol \
  call-graph \
  --contract SimpleToken
```
Sample output:
```json
{
  "edges": [
    {
      "caller": "SimpleToken.transfer(address,uint256)",
      "callee": "SimpleToken._performTransfer(address,address,uint256)"
    }
  ],
  "metadata": {
    "engine": "slither"
  }
}
```

## Python API
```python
from solidity_fcg_tool.services.query import get_function_source

result = get_function_source(
    project_path="samples/SimpleToken.sol",
    contract="SimpleToken",
    function_signature="transfer(address,uint256)",
)
print(result["source"])
```

For repeated queries, keep the service instance alive:
```python
from solidity_fcg_tool.services.query import create_service

service = create_service("samples/SimpleToken.sol")
info = service.get_function_source("SimpleToken", "transfer(address,uint256)")
edges = service.get_call_graph(caller_contract="SimpleToken")
```

## Project Layout
- `solidity_fcg_tool/core` – engine abstractions and shared models.
- `solidity_fcg_tool/engines` – registry and the Slither-backed engine.
- `solidity_fcg_tool/services` – public query service and helpers.
- `samples/` – example Solidity contracts.
- `tests/` – pytest-based regression suite.

## Extending Engines
1. Implement `AnalysisEngine`, filling in `load()` and (optionally) `_iter_call_graph_impl()`.
2. Populate `ProjectModel` / `ContractInfo` / `FunctionInfo` with the new engine’s data.
3. Register the engine via `register_engine("my-engine", MyEngineClass)`.
4. Use it through `--engine my-engine` (CLI) or `create_service(..., engine_name="my-engine")`.

## Release Notes
See the [CHANGELOG](CHANGELOG.md) for a detailed history of updates.

## Development & Tests
```bash
pytest
```

> If Slither or `solc` is missing, API/CLI tests will be skipped with an informative message.

For more details in Chinese, please read `README_zh.md`.

## Publishing
To build and upload a release:
```bash
pip install -e .[dev]
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```
