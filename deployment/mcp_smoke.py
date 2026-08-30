#!/usr/bin/env python3
"""Authenticated public-route MCP smoke test used after deployment."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

from fastmcp import Client


async def main() -> int:
    endpoint = os.environ.get("BRAIN_PUBLIC_MCP_URL", "")
    token = os.environ.get("BRAIN_SMOKE_TOKEN", "")
    query = os.environ.get("BRAIN_SMOKE_QUERY", "Brain OS retrieval status")
    if not endpoint:
        print(json.dumps({"ok": False, "error": "BRAIN_PUBLIC_MCP_URL is required"}))
        return 2
    if not token:
        print(json.dumps({"ok": False, "error": "BRAIN_SMOKE_TOKEN is required"}))
        return 2

    unauth_rejected = False
    try:
        async with Client(endpoint) as client:
            await client.call_tool("brain_status", {})
    except Exception:
        unauth_rejected = True

    started = time.perf_counter()
    async with Client(endpoint, auth=token) as client:
        status_result = await client.call_tool("brain_status", {})
        context_result = await client.call_tool(
            "brain_context",
            {"query": query, "max_context_units": 256, "mode": "compact"},
        )
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    status = status_result.data
    context = context_result.data
    ok = bool(
        unauth_rejected
        and isinstance(status, dict)
        and status.get("fts_available")
        and isinstance(context, dict)
        and context.get("coverage", {}).get("returned_context_units", 0) <= 256
        and context.get("retrieval_metrics")
    )
    print(json.dumps({
        "ok": ok,
        "unauthenticated_rejected": unauth_rejected,
        "status_received": isinstance(status, dict),
        "bounded_context": context.get("coverage", {}) if isinstance(context, dict) else {},
        "retrieval_metrics_present": bool(context.get("retrieval_metrics")) if isinstance(context, dict) else False,
        "latency_ms": latency_ms,
    }, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
