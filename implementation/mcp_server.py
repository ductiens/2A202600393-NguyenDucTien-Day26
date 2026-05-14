from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

try:
    from .db import SQLiteAdapter, ValidationError
    from .init_db import DB_PATH, create_database
except ImportError:
    from db import SQLiteAdapter, ValidationError
    from init_db import DB_PATH, create_database


SERVER_NAME = "SQLite Lab MCP Server"

mcp = FastMCP(SERVER_NAME)

if not Path(DB_PATH).exists():
    create_database(reset=True)

adapter = SQLiteAdapter(DB_PATH)


def _tool_error(exc: Exception) -> ValueError:
    return ValueError(str(exc))


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows in a table with safe filtering, sorting, and pagination."""
    try:
        rows = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
    except ValidationError as exc:
        raise _tool_error(exc) from exc

    return {
        "table": table,
        "columns": columns,
        "limit": limit,
        "offset": offset,
        "returned": len(rows),
        "rows": rows,
    }


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a table using parameterized SQL."""
    try:
        payload = adapter.insert(table=table, values=values)
    except ValidationError as exc:
        raise _tool_error(exc) from exc

    return {"table": table, "inserted": payload}


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    group_by: list[str] | None = None,
) -> dict[str, Any]:
    """Run aggregate queries (count, avg, sum, min, max)."""
    try:
        rows = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
    except ValidationError as exc:
        raise _tool_error(exc) from exc

    return {
        "table": table,
        "metric": metric,
        "column": column,
        "group_by": group_by or [],
        "rows": rows,
    }


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return full database schema as JSON text."""
    schema = adapter.get_database_schema()
    return json.dumps(schema, indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return one table schema as JSON text."""
    try:
        schema = adapter.get_table_schema(table_name)
    except ValidationError as exc:
        raise _tool_error(exc) from exc

    return json.dumps({"table": table_name, "columns": schema}, indent=2)


if __name__ == "__main__":
    mcp.run()
