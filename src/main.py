import asyncio
import hmac
import os
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager

from google.genai.errors import APIError

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from pydantic import BaseModel, ConfigDict, Field
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.engine import init_db, get_digimon_status, tick_active_session, feed_digimon
from src.agent import chat_with_digimon

MAX_REQUEST_BODY_BYTES = 16 * 1024
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMITS = {"/chat": 10}
DEFAULT_RATE_LIMIT = 60
MAX_RATE_LIMIT_BUCKETS = 4096
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DIGIFARM_CORS_ORIGINS", DEFAULT_CORS_ORIGINS
    ).split(",")
    if origin.strip()
]

if "*" in CORS_ORIGINS:
    raise RuntimeError("DIGIFARM_CORS_ORIGINS must list explicit origins, not '*'.")


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_REQUEST_BODY_BYTES:
                response = {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [(b"content-type", b"application/json")],
                }
                await send(response)
                await send(
                    {
                        "type": "http.response.body",
                        "body": b'{"detail":"Request body too large"}',
                    }
                )
                return
            if not message.get("more_body", False):
                break

        body_sent = False

        async def replay_body() -> Message:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay_body, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="DigiFarm Agent API", lifespan=lifespan)
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

_rate_limit_buckets: OrderedDict[tuple[str, str], deque[float]] = OrderedDict()
_rate_limit_lock = asyncio.Lock()


async def authenticate_and_rate_limit(request: Request) -> None:
    expected_token = os.environ.get("DIGIFARM_API_TOKEN", "")
    if len(expected_token) < 32:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured",
        )

    authorization = request.headers.get("Authorization", "")
    scheme, separator, supplied_token = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not hmac.compare_digest(supplied_token, expected_token)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    client_host = request.client.host if request.client else "unknown"
    keys_and_limits = [((client_host, "*"), DEFAULT_RATE_LIMIT)]
    if request.url.path in RATE_LIMITS:
        keys_and_limits.append(
            ((client_host, request.url.path), RATE_LIMITS[request.url.path])
        )
    now = time.monotonic()

    async with _rate_limit_lock:
        buckets = []
        for key, limit in keys_and_limits:
            bucket = _rate_limit_buckets.get(key)
            if bucket is None:
                if len(_rate_limit_buckets) >= MAX_RATE_LIMIT_BUCKETS:
                    _rate_limit_buckets.popitem(last=False)
                bucket = deque()
                _rate_limit_buckets[key] = bucket
            _rate_limit_buckets.move_to_end(key)

            while bucket and now - bucket[0] >= RATE_LIMIT_WINDOW_SECONDS:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(
                    1, int(RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0]))
                )
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )
            buckets.append(bucket)
        for bucket in buckets:
            bucket.append(now)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)


@app.get("/", dependencies=[Depends(authenticate_and_rate_limit)])
def read_root():
    frontend_url = os.environ.get("DIGIFARM_FRONTEND_URL")
    if frontend_url:
        return RedirectResponse(url=frontend_url)
    return {
        "name": "DigiFarm Agent API",
        "message": "The frontend is a separate application. See the README to run it.",
    }


@app.get("/app", include_in_schema=False)
@app.get("/app/", include_in_schema=False)
def redirect_to_frontend():
    frontend_url = os.environ.get("DIGIFARM_FRONTEND_URL")
    if not frontend_url:
        raise HTTPException(
            status_code=503,
            detail="The frontend URL is not configured",
        )
    return RedirectResponse(url=frontend_url)


@app.get("/status", dependencies=[Depends(authenticate_and_rate_limit)])
def status():
    """Returns the exact current stats with ZERO offline penalty"""
    return get_digimon_status()


@app.post("/tick", dependencies=[Depends(authenticate_and_rate_limit)])
def app_tick():
    """Called by the frontend app periodically ONLY while the app is open to advance time."""
    tick_active_session()
    return get_digimon_status()


@app.post("/feed", dependencies=[Depends(authenticate_and_rate_limit)])
def feed():
    feed_digimon()
    return {"message": "Fed your Digimon!", "status": get_digimon_status()}


@app.post("/chat", dependencies=[Depends(authenticate_and_rate_limit)])
def chat(request: ChatRequest):
    try:
        reply = chat_with_digimon(request.message)
        return {"reply": reply, "status": get_digimon_status()}
    except APIError as e:
        # Handle specific Gemini API errors (e.g. 503 Overloaded, 429 Rate Limit, etc.)
        error_message = e.message if hasattr(e, 'message') else str(e)
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            raise HTTPException(
                status_code=503, 
                detail="Botamon is resting right now because the AI servers are experiencing high traffic. Please try again in a few moments!"
            )
        raise HTTPException(status_code=502, detail=f"Gemini API Error: {error_message}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")