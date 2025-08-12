#!/usr/bin/env python3
"""Custom Supabase MCP Server for Kiro DevSync AI."""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List

# Add project path to use existing database connection
sys.path.append("/Users/asakohayase/kiro-devsync-ai")


# MCP Protocol implementation
class SupabaseMCPServer:
    def __init__(self):
        # Use the existing database connection from the project
        from devsync_ai.database.connection import get_database

        self.get_database = get_database

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "kiro-supabase-mcp", "version": "1.0.0"},
                    },
                }

            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "query_table",
                                "description": "Query a Supabase table",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "table": {"type": "string", "description": "Table name"},
                                        "columns": {
                                            "type": "string",
                                            "description": "Columns to select (default: *)",
                                        },
                                        "filters": {
                                            "type": "object",
                                            "description": "Filter conditions",
                                        },
                                    },
                                    "required": ["table"],
                                },
                            },
                            {
                                "name": "list_tables",
                                "description": "List all tables in the database",
                                "inputSchema": {"type": "object", "properties": {}},
                            },
                            {
                                "name": "insert_data",
                                "description": "Insert data into a table",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "table": {"type": "string", "description": "Table name"},
                                        "data": {"type": "object", "description": "Data to insert"},
                                    },
                                    "required": ["table", "data"],
                                },
                            },
                            {
                                "name": "update_data",
                                "description": "Update data in a table",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "table": {"type": "string", "description": "Table name"},
                                        "data": {"type": "object", "description": "Data to update"},
                                        "filters": {
                                            "type": "object",
                                            "description": "Filter conditions",
                                        },
                                    },
                                    "required": ["table", "data", "filters"],
                                },
                            },
                            {
                                "name": "delete_data",
                                "description": "Delete data from a table",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "table": {"type": "string", "description": "Table name"},
                                        "filters": {
                                            "type": "object",
                                            "description": "Filter conditions",
                                        },
                                    },
                                    "required": ["table", "filters"],
                                },
                            },
                            {
                                "name": "drop_table",
                                "description": "Drop/delete a table from the database",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "table": {
                                            "type": "string",
                                            "description": "Table name to drop",
                                        },
                                        "cascade": {
                                            "type": "boolean",
                                            "description": "Use CASCADE option",
                                            "default": True,
                                        },
                                    },
                                    "required": ["table"],
                                },
                            },
                        ]
                    },
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if tool_name == "query_table":
                    result = await self.query_table(arguments)
                elif tool_name == "list_tables":
                    result = await self.list_tables()
                elif tool_name == "insert_data":
                    result = await self.insert_data(arguments)
                elif tool_name == "update_data":
                    result = await self.update_data(arguments)
                elif tool_name == "delete_data":
                    result = await self.delete_data(arguments)
                elif tool_name == "drop_table":
                    result = await self.drop_table(arguments)
                else:
                    raise ValueError(f"Unknown tool: {tool_name}")

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            }

    async def query_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Query a Supabase table using existing database connection."""
        table = args.get("table")
        columns = args.get("columns", "*")
        filters = args.get("filters", {})

        try:
            db = await self.get_database()

            # Use the SupabaseClient select method
            result = await db.select(
                table=table, filters=filters if filters else None, select_fields=columns
            )

            return {"table": table, "count": len(result), "data": result}

        except Exception as e:
            return {"error": f"Database query failed: {str(e)}"}

    async def list_tables(self) -> Dict[str, Any]:
        """List all tables (simplified - returns known tables)."""
        # For now, return the tables we know exist
        # Only show tables we decided to use in our enhanced mapping approach
        active_tables = ["pr_ticket_mappings"]  # Main table for PR → JIRA ticket mapping

        return {"tables": active_tables}

    async def drop_table(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Drop a table from the database."""
        table = args.get("table")
        cascade = args.get("cascade", True)

        try:
            db = await self.get_database()

            # Build the DROP TABLE SQL
            cascade_option = "CASCADE" if cascade else "RESTRICT"
            sql_query = f"DROP TABLE IF EXISTS {table} {cascade_option};"

            # Execute the DROP TABLE command
            # Note: This uses raw SQL execution which might not be available in all Supabase clients
            # We'll try to use the database connection's execute method

            # For now, return the SQL that should be executed
            return {
                "action": "drop_table",
                "table": table,
                "sql": sql_query,
                "status": "SQL generated - execute manually in Supabase SQL editor",
                "warning": "This is a destructive operation!",
            }

        except Exception as e:
            return {"error": f"Failed to drop table {table}: {str(e)}"}

    async def insert_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data into a table."""
        table = args.get("table")
        data = args.get("data")

        try:
            db = await self.get_database()

            # SupabaseClient.insert returns List[Dict] directly
            result = await db.insert(table=table, data=data)

            return {
                "action": "insert",
                "table": table,
                "status": "SUCCESS",
                "inserted_data": result,
            }

        except Exception as e:
            return {"error": f"Failed to insert data into {table}: {str(e)}"}

    async def update_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Update data in a table."""
        table = args.get("table")
        data = args.get("data")
        filters = args.get("filters")

        try:
            db = await self.get_database()

            # SupabaseClient.update returns List[Dict] directly
            result = await db.update(table=table, data=data, filters=filters)

            return {
                "action": "update",
                "table": table,
                "status": "SUCCESS",
                "updated_data": result,
            }

        except Exception as e:
            return {"error": f"Failed to update data in {table}: {str(e)}"}

    async def delete_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete data from a table."""
        table = args.get("table")
        filters = args.get("filters")

        try:
            db = await self.get_database()

            # SupabaseClient.delete returns List[Dict] directly
            result = await db.delete(table=table, filters=filters)

            return {
                "action": "delete",
                "table": table,
                "status": "SUCCESS",
                "deleted_count": len(result) if result else 0,
                "deleted_data": result,
            }

        except Exception as e:
            return {"error": f"Failed to delete data from {table}: {str(e)}"}


async def main():
    """Main MCP server loop."""
    try:
        server = SupabaseMCPServer()

        # Read from stdin and write to stdout (MCP protocol)
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line.strip())
                response = await server.handle_request(request)

                print(json.dumps(response))
                sys.stdout.flush()

            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32603, "message": f"Server initialization failed: {str(e)}"},
        }
        print(json.dumps(error_response))
        sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
