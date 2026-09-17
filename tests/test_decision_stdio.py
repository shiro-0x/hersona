"""Real JSON-RPC initialize/list/call, with an explicitly key-free subprocess."""

import asyncio
import json
import os
import sys

import pytest

pytest.importorskip("mcp")
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_stdio_no_key():
    async def exercise():
        env = {
            k: os.environ[k]
            for k in ("PATH", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "SYSTEMROOT")
            if k in os.environ
        }
        # Explicit empty value prevents SDK configuration inherited by any launcher.
        env["TYPESAFE_API_KEY"] = ""
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "hersona.mcp.server"], env=env
        )
        async with asyncio.timeout(20):
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    names = {t.name for t in (await client.list_tools()).tools}
                    assert {"evaluate_decision", "blend", "export", "measure_intensity"} <= names
                    result = await client.call_tool(
                        "evaluate_decision", {"names": ["kuudere"], "user_message": "hello"}
                    )
                    data = json.loads(result.content[0].text)
                    assert data["error"]["code"] == "provider_not_configured"
                    assert data["gate"] == "block" and data["executed"] is False
                    blended = await client.call_tool("blend", {"names": ["kuudere"]})
                    assert not blended.isError

    asyncio.run(exercise())


def test_real_fastmcp_dispatch_keeps_event_loop_responsive(monkeypatch):
    from threading import Event

    from hersona.core import decision
    from hersona.mcp.server import build_server

    started, release = Event(), Event()
    finished = []

    def slow_evaluate(*args, **kwargs):
        started.set()
        released = release.wait(timeout=2)
        finished.append(released)
        return {"executed": False, "gate": "review"}, 0

    monkeypatch.setattr(decision, "decision_payload", slow_evaluate)
    server = build_server()

    async def exercise():
        task = asyncio.create_task(
            server.call_tool("evaluate_decision", {"names": ["kuudere"], "user_message": "hello"})
        )
        try:
            async with asyncio.timeout(5):
                while not started.is_set():
                    await asyncio.sleep(0.001)
                # This real tool dispatch must complete while evaluation is waiting.
                await server.call_tool("blend", {"names": ["kuudere"]})
                assert not finished, "synchronous decision evaluation blocked the MCP event loop"
        finally:
            release.set()
            await task
        assert finished == [True]

    asyncio.run(exercise())
