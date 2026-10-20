"""Production HTTP entry point: same-origin PWA and authenticated Gemini API."""

import asyncio
import logging
import os
import secrets
import time
from threading import Lock
from collections import defaultdict, deque
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.genai import errors
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from catalog import VERSION, build_catalog
from consultation import CUSTOM_BODY_PART, MODEL, OBJECTIONS, PATIENT_TYPES, STAGES, build_prompt, generate_guide
from syndrome_kb import load_syndromes

api = FastAPI(title="生生優動板橋｜診間溝通工作台", version=VERSION, docs_url=None, redoc_url=None, openapi_url=None)
allowed_origins = [value.strip().rstrip("/") for value in os.getenv("ALLOWED_ORIGINS", "").split(",") if value.strip()]
if allowed_origins:
    api.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])

requests_by_client: dict[str, deque] = defaultdict(deque)
generation_slots = asyncio.Semaphore(2)
limiter_lock = Lock()
SESSION_SECONDS = 12 * 60 * 60


@api.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # FastAPI's default validation response echoes rejected field values.
    return JSONResponse({"detail": "輸入資料不完整或超出限制，請檢查欄位後重試。"}, status_code=422, headers={"Cache-Control": "no-store"})


def configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip() and os.getenv("CLINIC_ACCESS_CODE", "").strip())


def signer() -> URLSafeTimedSerializer:
    code = os.getenv("CLINIC_ACCESS_CODE", "").strip()
    if not code:
        raise HTTPException(503, "診所服務尚未完成設定，請聯絡管理員。")
    return URLSafeTimedSerializer(code, salt="clinic-mobile-session-v1")


def rate_limit(client: str, limit: int, seconds: int = 60) -> None:
    with limiter_lock:
        now = time.monotonic()
        # Bound the single-worker in-memory limiter; never store patient inputs.
        for key in list(requests_by_client):
            entries = requests_by_client[key]
            while entries and entries[0] <= now - seconds:
                entries.popleft()
            if not entries:
                del requests_by_client[key]
        if len(requests_by_client) >= 2000 and client not in requests_by_client:
            raise HTTPException(429, "目前使用人數較多，請稍後再試。")
        entries = requests_by_client[client]
        if len(entries) >= limit:
            raise HTTPException(429, "操作較頻繁，請稍候一分鐘再試。", headers={"Retry-After": "60"})
        entries.append(now)


def require_session(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "請先輸入診所使用碼。")
    try:
        session = signer().loads(authorization[7:], max_age=SESSION_SECONDS)
        return session["session"]
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        raise HTTPException(401, "使用授權已到期，請重新輸入診所使用碼。") from None


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=256)


class GuideInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    syndrome_id: int = Field(ge=1, le=50, strict=True)
    symptom: str = Field(default="", max_length=500)
    stage: str = Field(max_length=100)
    objection: str = Field(max_length=100)
    patient_type: str = Field(max_length=100)


@api.middleware("http")
async def response_headers(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method == "POST":
        length = request.headers.get("content-length")
        try:
            if length is None or int(length) > 12000 or int(length) < 0:
                return JSONResponse({"detail": "輸入內容過長或無法讀取，請縮短後重試。"}, status_code=413, headers={"Cache-Control": "no-store"})
        except ValueError:
            return JSONResponse({"detail": "無效的請求格式。"}, status_code=400, headers={"Cache-Control": "no-store"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.url.path.endswith(("/", ".html", "sw.js", "config.json", "manifest.webmanifest")):
        response.headers["Cache-Control"] = "no-cache"
    return response


@api.get("/api/health")
def health():
    records = load_syndromes()
    return {"status": "ok", "version": VERSION, "syndrome_count": len(records), "generation_enabled": configured(), "model": MODEL}


@api.get("/api/catalog")
def catalog():
    return build_catalog()


@api.post("/api/session")
def login(payload: LoginInput, request: Request):
    rate_limit("login:" + (request.client.host if request.client else "unknown"), 5)
    expected = os.getenv("CLINIC_ACCESS_CODE", "").strip()
    if not configured():
        raise HTTPException(503, "診所 AI 服務尚未完成設定，知識庫仍可使用。")
    if not secrets.compare_digest(payload.code.encode(), expected.encode()):
        raise HTTPException(401, "使用碼不正確，請向診所管理員確認。")
    return {"token": signer().dumps({"session": secrets.token_urlsafe(24)}), "expires_in": SESSION_SECONDS}


@api.post("/api/generate")
async def generate(payload: GuideInput, request: Request):
    session = require_session(request)
    if not configured():
        raise HTTPException(503, "診所 AI 服務尚未完成設定，請稍後再試。")
    if payload.stage not in STAGES or payload.objection not in OBJECTIONS or payload.patient_type not in PATIENT_TYPES:
        raise HTTPException(422, "請使用選單提供的溝通情境。")
    rate_limit("generate:" + session, 8)
    record = next(record for record in load_syndromes() if record.id == payload.syndrome_id)
    symptom = payload.symptom.strip() or "症狀待評估（以所選症候群建立溝通情境）"
    prompt = build_prompt(symptom, payload.stage, payload.objection, payload.patient_type, CUSTOM_BODY_PART, syndrome=record)
    try:
        async with generation_slots:
            guide = await run_in_threadpool(generate_guide, os.environ["GEMINI_API_KEY"], prompt)
    except (httpx.TimeoutException, TimeoutError):
        raise HTTPException(504, "生成逾時，請稍後再試。") from None
    except errors.APIError as exc:
        if str(exc.code) == "429":
            raise HTTPException(429, "AI 服務暫時達到用量限制，請稍後重試。") from None
        raise HTTPException(502, "AI 服務暫時無法回應，請管理員確認模型、金鑰與配額。") from None
    except (httpx.RequestError, ValueError):
        raise HTTPException(502, "目前無法取得完整話術，請稍後重試。") from None
    except Exception as exc:
        logging.getLogger(__name__).error("Guide generation failed (%s)", type(exc).__name__)
        raise HTTPException(502, "話術生成暫時無法完成，請稍後重試。") from None
    return {"guide": guide, "syndrome_id": record.id, "syndrome": record.title, "model": MODEL}


api.mount("/", StaticFiles(directory=Path(__file__).with_name("docs"), html=True), name="pwa")
