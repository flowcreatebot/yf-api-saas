from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import settings
from .routes.market import router as market_router
from .routes.billing import router as billing_router

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


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
