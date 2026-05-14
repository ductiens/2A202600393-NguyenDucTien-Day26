from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from fastmcp import Client
from fastmcp.exceptions import ToolError

try:
    from implementation.init_db import create_database
    from implementation.db import SQLiteAdapter
    from implementation import mcp_server as mcp_server_module
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from implementation.init_db import create_database
    from implementation.db import SQLiteAdapter
    from implementation import mcp_server as mcp_server_module


mcp = mcp_server_module.mcp


def run(coro):
    return asyncio.run(coro)


@contextmanager
def isolated_test_db():
    temp_dir = Path(tempfile.mkdtemp(prefix="sqlite_lab_test_"))
    db_path = temp_dir / "lab_test.db"
    create_database(db_path=db_path, reset=True)

    old_adapter = mcp_server_module.adapter
    mcp_server_module.adapter = SQLiteAdapter(db_path)
    try:
        yield
    finally:
        mcp_server_module.adapter = old_adapter
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_discovery_and_resources() -> None:
    async def scenario() -> None:
        with isolated_test_db():
            async with Client(mcp) as client:
                tools = await client.list_tools()
                tool_names = {t.name for t in tools}
                assert {"search", "insert", "aggregate"} <= tool_names

                resources = await client.list_resources()
                resource_uris = {str(r.uri) for r in resources}
                assert "schema://database" in resource_uris

                templates = await client.list_resource_templates()
                template_uris = {str(t.uriTemplate) for t in templates}
                assert "schema://table/{table_name}" in template_uris

                schema = await client.read_resource("schema://database")
                assert schema

                table_schema = await client.read_resource("schema://table/students")
                assert table_schema

    run(scenario())


def test_search_insert_aggregate_success() -> None:
    async def scenario() -> None:
        with isolated_test_db():
            async with Client(mcp) as client:
                search_result = await client.call_tool(
                    "search",
                    {
                        "table": "students",
                        "filters": [{"column": "cohort", "op": "=", "value": "A1"}],
                        "order_by": "id",
                        "limit": 10,
                        "offset": 0,
                    },
                )
                assert search_result.data["returned"] >= 1

                insert_result = await client.call_tool(
                    "insert",
                    {
                        "table": "students",
                        "values": {"name": "Hoa", "cohort": "C3", "age": 24},
                    },
                )
                assert insert_result.data["inserted"]["name"] == "Hoa"
                assert "id" in insert_result.data["inserted"]

                aggregate_result = await client.call_tool(
                    "aggregate",
                    {
                        "table": "enrollments",
                        "metric": "avg",
                        "column": "score",
                        "group_by": ["course_id"],
                    },
                )
                assert len(aggregate_result.data["rows"]) >= 1

    run(scenario())


def test_validation_errors() -> None:
    async def scenario() -> None:
        with isolated_test_db():
            async with Client(mcp) as client:
                try:
                    await client.call_tool("search", {"table": "not_exists"})
                    assert False, "Expected ToolError for unknown table"
                except ToolError:
                    pass

                try:
                    await client.call_tool(
                        "search",
                        {
                            "table": "students",
                            "filters": [{"column": "cohort", "op": "DROP", "value": "A1"}],
                        },
                    )
                    assert False, "Expected ToolError for unsupported operator"
                except ToolError:
                    pass

                try:
                    await client.call_tool(
                        "aggregate",
                        {"table": "enrollments", "metric": "median", "column": "score"},
                    )
                    assert False, "Expected ToolError for unsupported metric"
                except ToolError:
                    pass

                try:
                    await client.call_tool("insert", {"table": "students", "values": {}})
                    assert False, "Expected ToolError for empty insert payload"
                except ToolError:
                    pass

    run(scenario())
