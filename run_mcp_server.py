#!/usr/bin/env python3
"""Entry point for running the MCP server."""

import asyncio
from src.mcp.server import mcp, initialize_mcp_server, cleanup_mcp_server


async def main():
    """Main entry point for MCP server."""
    try:
        # Initialize server dependencies
        await initialize_mcp_server()

        # Run the MCP server
        # Note: fastmcp's run() method handles the event loop
        # We just need to ensure cleanup happens
        mcp.run()

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error running MCP server: {e}")
        raise
    finally:
        await cleanup_mcp_server()


if __name__ == "__main__":
    # Note: fastmcp.run() manages its own event loop
    # For proper cleanup, we use a wrapper
    try:
        asyncio.run(initialize_mcp_server())
        mcp.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        asyncio.run(cleanup_mcp_server())
