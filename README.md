# solidity-fcg-tool

Solidity Function Call Graph (FCG) 工具，提供模块/函数级别的解析能力，为 AI 框架或上层分析服务提供结构化数据。首版基于 [Slither](https://github.com/crytic/slither)，并预留了解析引擎的抽象层，后续可替换或并存 Tree-sitter、Solar 等实现。

## 特性
- 统一引擎接口：`core.engine_base.AnalysisEngine` 定义抽象，支持可插拔解析器。
- 丰富数据模型：函数源码、状态变量读写、调用关系、位置信息等。
- 高层服务接口：`services.query.QueryService` 提供 Python API；CLI 输出 JSON。
- 可扩展架构：引擎注册表支持未来新增 Tree-sitter/Solar，业务层无需改动。

## 安装
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> 需要本地安装对应版本的 `solc`。可通过 `py-solc-x` 下载或使用系统已有编译器。

## CLI 示例
```bash
python -m solidity_fcg_tool \
  --project samples/SimpleToken.sol \
  --engine slither \
  query \
  --contract SimpleToken \
  --function "transfer(address,uint256)"
```
返回数据包含函数源码、位置、调用关系及元信息。

生成调用图：
```bash
python -m solidity_fcg_tool \
  --project samples/SimpleToken.sol \
  call-graph \
  --contract SimpleToken
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

或使用 `QueryService` 保持引擎实例：
```python
from solidity_fcg_tool.services.query import create_service

service = create_service("samples/SimpleToken.sol")
info = service.get_function_source("SimpleToken", "transfer(address,uint256)")
edges = service.get_call_graph(caller_contract="SimpleToken")
```

## 项目结构
- `docs/requirements.md`：需求与设计文档。
- `solidity_fcg_tool/core`：引擎抽象与数据模型。
- `solidity_fcg_tool/engines`：引擎注册表与 Slither 适配器。
- `solidity_fcg_tool/services`：对外查询服务。
- `samples/`：示例 Solidity 合约。
- `tests/`：基础单元测试与回归入口。

## 扩展引擎指南
实现自定义解析器时：
1. 继承 `AnalysisEngine`，实现 `load()`、`_iter_call_graph_impl()` 等接口。
2. 将解析结果写入 `ProjectModel`/`ContractInfo`/`FunctionInfo` 数据结构。
3. 在 `solidity_fcg_tool/engines/__init__.py` 或自定义模块中调用 `register_engine("name", EngineClass)`.
4. 通过 CLI 的 `--engine name` 或 `create_service(..., engine_name="name")` 使用。

## 开发与测试
```bash
pytest
```

> 若未安装 Slither，可先运行不依赖引擎的测试；与 Slither 相关的功能在运行时会给出友好提示。
