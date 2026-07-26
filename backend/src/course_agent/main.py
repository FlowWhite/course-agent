"""FastAPI application assembly point.

Feature endpoints live in ``course_agent.api.routers``. This module keeps
only cross-cutting concerns: application lifecycle, CORS, rate limiting,
response encoding, and router registration.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routers import (
    auth_router,
    chat_router,
    courses_router,
    files_router,
    insights_router,
    plans_router,
    tasks_router,
)
from .postgres_database import ensure_application_schema
from .rate_limit import InMemoryRateLimiter


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize persistent schema before serving requests."""
    ensure_application_schema()
    yield


app = FastAPI(title="Course Agent API", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limiter = InMemoryRateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate-limit each client IP and request path."""
    if request.url.path == "/health":
        return await call_next(request)
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"{client_ip}:{request.url.path}"
    allowed, retry_after = rate_limiter.check(rate_limit_key)
    if not allowed:
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content={
                "success": False,
                "data": None,
                "error": "请求过于频繁，请稍后再试",
            },
        )
    return await call_next(request)


@app.middleware("http")
async def add_utf8_charset(request: Request, call_next):
    """Explicitly declare UTF-8 for JSON responses."""
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("application/json") and "charset=" not in content_type.lower():
        response.headers["content-type"] = f"{content_type}; charset=utf-8"
    return response


@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Check whether the API service is available."""
    return {
        "success": True,
        "data": {"service": "course-agent", "status": "ok"},
        "error": None,
    }


for router in (
    auth_router,
    courses_router,
    tasks_router,
    files_router,
    plans_router,
    insights_router,
    chat_router,
):
    app.include_router(router)
