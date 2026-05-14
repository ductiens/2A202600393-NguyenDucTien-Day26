from __future__ import annotations

import asyncio
from pprint import pprint

from fastmcp import Client
from fastmcp.exceptions import ToolError

try:
    from .init_db import create_database
    from .mcp_server import mcp
except ImportError:
    from init_db import create_database
    from mcp_server import mcp


async def main() -> None:
    create_database(reset=True)

    async with Client(mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()

        print("Tools:", [t.name for t in tools])
        print("Resources:", [r.uri for r in resources])
        print("Resource templates:", [t.uriTemplate for t in templates])

        search_result = await client.call_tool(
            "search",
            {"table": "students", "filters": [{"column": "cohort", "op": "=", "value": "A1"}]},
        )
        print("\nsearch(students cohort=A1)")
        pprint(search_result.data)

        insert_result = await client.call_tool(
            "insert",
            {"table": "students", "values": {"name": "Lan", "cohort": "A1", "age": 23}},
        )
        print("\ninsert(students)")
        pprint(insert_result.data)

        aggregate_result = await client.call_tool(
            "aggregate",
            {"table": "enrollments", "metric": "avg", "column": "score", "group_by": ["course_id"]},
        )
        print("\naggregate(avg score by course_id)")
        pprint(aggregate_result.data)

        schema_result = await client.read_resource("schema://database")
        print("\nresource schema://database")
        pprint(schema_result)

        table_schema_result = await client.read_resource("schema://table/students")
        print("\nresource schema://table/students")
        pprint(table_schema_result)

        print("\nnegative case: unknown table")
        try:
            await client.call_tool("search", {"table": "missing_table"})
        except ToolError as exc:
            print("Expected error:", exc)


if __name__ == "__main__":
    asyncio.run(main())
