from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Iterable

from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response

# Load environment variables from .env file
load_dotenv()

ADK_BASE_URL = os.getenv("ADK_BASE_URL", "http://127.0.0.1:8021").rstrip("/")
INTERNAL_TOKEN = os.getenv("AGENT_INTERNAL_TOKEN", "").strip()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not INTERNAL_TOKEN:
        raise RuntimeError("AGENT_INTERNAL_TOKEN must be set for the agents proxy")
    yield


app = FastAPI(title="MetroSense Agents Proxy", lifespan=lifespan)


def _require_internal_token(header_value: str | None) -> None:
    if not header_value or header_value != INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid internal token")


def _filtered_request_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    blocked = {"host", "content-length", "connection", "x-internal-token"}
    return {key: value for key, value in headers if key.lower() not in blocked}


def _filtered_response_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    blocked = {
        "content-length",
        "connection",
        "transfer-encoding",
        "content-encoding",
    }
    return {key: value for key, value in headers if key.lower() not in blocked}


@app.get("/health")
async def health() -> Response:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{ADK_BASE_URL}/health")
    response_headers = _filtered_response_headers(response.headers.items())
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )


@app.api_route(
    "/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)
async def proxy(
    request: Request,
    path: str,
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> Response:
    _require_internal_token(x_internal_token)
    target_url = f"{ADK_BASE_URL}/{path}"
    body = await request.body()
    headers = _filtered_request_headers(request.headers.items())

    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.request(
            request.method,
            target_url,
            params=request.query_params,
            content=body,
            headers=headers,
        )

    response_headers = _filtered_response_headers(response.headers.items())
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )
