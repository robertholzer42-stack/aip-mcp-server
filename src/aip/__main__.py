"""Entry point for running the AIP MCP server."""
from aip.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
