"""Copy-ready MCP stdio client — replace `samm` bits with your server's package.

Usage:
    from stdio_client import SammClient
    async with SammClient(db_path="samm.db") as c:
        rec = await c.remember("ns", "agent", "content")
        fetched = await c.recall(rec["id"])
        hits = await c.search("ns", "query")
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# Package root so the spawned server can `import` the backend regardless of cwd.
_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SammClient:
    def __init__(self, db_path: str = "samm.db", python_exe: str | None = None) -> None:
        self.db_path = db_path
        self._python_exe = python_exe or sys.executable
        self._session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None

    async def connect(self) -> "SammClient":
        if self._session is not None:
            return self
        env = dict(os.environ)
        env["PYTHONPATH"] = _PKG_ROOT + os.pathsep + env.get("PYTHONPATH", "")
        # Launch a REAL stdio MCP server (NOT streamable-HTTP — that binds a port
        # and blocks the stdio client). Build your server and run transport='stdio'.
        launch = (
            "import sys; "
            "from samm.mcp_server import _build_server; "
            "srv=_build_server(db_path=sys.argv[1]); "
            "srv.run(transport='stdio')"
        )
        params = StdioServerParameters(
            command=self._python_exe, args=["-c", launch, self.db_path], env=env
        )
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def close(self) -> None:
        stack, self._stack = self._stack, None
        self._session = None
        if stack is not None:
            await stack.aclose()

    async def __aenter__(self) -> "SammClient":
        return await self.connect()

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _call(self, name: str, args: dict[str, Any]) -> Any:
        if self._session is None:
            await self.connect()
        result = await self._session.call_tool(name, args)  # type: ignore[union-attr]
        for block in getattr(result, "content", []):
            if getattr(block, "type", None) == "text":
                try:
                    return json.loads(block.text)
                except (json.JSONDecodeError, TypeError):
                    return {"raw": block.text}
        return {}

    async def remember(self, namespace: str, agent_id: str, content: str, type: str = "fact") -> dict:
        return await self._call("remember",
            {"namespace": namespace, "agent_id": agent_id, "content": content, "type": type})

    async def recall(self, memory_id: str) -> dict:
        return await self._call("recall", {"memory_id": memory_id})

    async def search(self, namespace: str, query: str, limit: int = 10) -> list:
        return await self._call("search", {"namespace": namespace, "query": query, "limit": limit})
