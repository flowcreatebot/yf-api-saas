from pathlib import Path
import time

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import SessionLocal, initialize_database, sync_configured_api_keys, verify_database_connection
from .models import UsageLog
from .routes.billing import router as billing_router
from .routes.customer_dashboard import router as customer_dashboard_router
from .routes.market import router as market_router

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Yahoo Finance-compatible API wrapper for no-code tools.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def record_usage_logs(request: Request, call_next):
    is_market_call = request.url.path.startswith("/v1/") and request.url.path != "/v1/health"
    if not is_market_call:
        return await call_next(request)

    started = time.perf_counter()
    status_code = 500
    response = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        api_key_id = getattr(request.state, "authenticated_api_key_id", None)
        if api_key_id:
            elapsed_ms = max(1, int((time.perf_counter() - started) * 1000))
            route = request.scope.get("route")
            route_path = getattr(route, "path", None)
            endpoint = route_path if isinstance(route_path, str) else request.url.path

            with SessionLocal() as db:
                db.add(
                    UsageLog(
                        api_key_id=api_key_id,
                        endpoint=endpoint,
                        status_code=status_code,
                        response_ms=elapsed_ms,
                    )
                )
                db.commit()


app.include_router(market_router)
app.include_router(billing_router)
app.include_router(customer_dashboard_router)

CUSTOMER_DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "web" / "customer-dashboard"

if CUSTOMER_DASHBOARD_DIR.exists():
    app.mount(
        "/dashboard",
        StaticFiles(directory=str(CUSTOMER_DASHBOARD_DIR), html=True),
        name="customer-dashboard",
    )


@app.on_event("startup")
def startup() -> None:
    verify_database_connection()
    initialize_database()
    sync_configured_api_keys()


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation failed",
            "errors": jsonable_encoder(exc.errors()),
        },
    )


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/customer", include_in_schema=False)
def customer_root_legacy_redirect():
    return RedirectResponse(url="/dashboard")


@app.get("/internal", include_in_schema=False)
def internal_root_legacy_redirect():
    return RedirectResponse(url="/dashboard")


@app.get("/internal/{path:path}", include_in_schema=False)
def internal_path_legacy_redirect(path: str):
    return RedirectResponse(url=f"/dashboard/{path}")
