from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routes.billing import router as billing_router
from .routes.customer_dashboard import router as customer_dashboard_router
from .routes.internal_dashboard import router as internal_dashboard_router
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
app.include_router(internal_dashboard_router)
app.include_router(customer_dashboard_router)

DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "web" / "dashboard"
DASHBOARD_V2_DIR = Path(__file__).resolve().parents[1] / "web" / "dashboard-react"

if DASHBOARD_V2_DIR.exists():
    app.mount(
        "/internal/dashboard",
        StaticFiles(directory=str(DASHBOARD_V2_DIR), html=True),
        name="internal-dashboard",
    )
    app.mount(
        "/dashboard",
        StaticFiles(directory=str(DASHBOARD_V2_DIR), html=True),
        name="customer-dashboard",
    )

if DASHBOARD_DIR.exists():
    app.mount(
        "/internal/dashboard-legacy",
        StaticFiles(directory=str(DASHBOARD_DIR), html=True),
        name="internal-dashboard-legacy",
    )


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


@app.get("/internal", include_in_schema=False)
def internal_root():
    if DASHBOARD_V2_DIR.exists():
        return RedirectResponse(url="/internal/dashboard/")
    if DASHBOARD_DIR.exists():
        return RedirectResponse(url="/internal/dashboard-legacy/")
    return RedirectResponse(url="/docs")


@app.get("/customer", include_in_schema=False)
def customer_root_legacy_redirect():
    return RedirectResponse(url="/dashboard")
