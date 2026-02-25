from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import initialize_database, sync_configured_api_keys, verify_database_connection
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
