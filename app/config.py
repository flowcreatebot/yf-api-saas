from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field(default="Y Finance API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    market_cache_ttl_seconds: int = Field(default=30, alias="MARKET_CACHE_TTL_SECONDS")
    market_cache_stale_window_seconds: int = Field(default=300, alias="MARKET_CACHE_STALE_WINDOW_SECONDS")

    api_master_key: str = Field(default="replace-me", alias="API_MASTER_KEY")
    api_valid_keys: str = Field(default="", alias="API_VALID_KEYS")

    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id_monthly: str = Field(default="", alias="STRIPE_PRICE_ID_MONTHLY")
    billing_allowed_redirect_hosts: str = Field(default="", alias="BILLING_ALLOWED_REDIRECT_HOSTS")
    billing_starter_plan_id: str = Field(default="starter-monthly", alias="BILLING_STARTER_PLAN_ID")
    billing_starter_plan_name: str = Field(default="Starter", alias="BILLING_STARTER_PLAN_NAME")
    billing_starter_plan_price_usd: float = Field(default=4.99, alias="BILLING_STARTER_PLAN_PRICE_USD")
    billing_starter_plan_interval: str = Field(default="month", alias="BILLING_STARTER_PLAN_INTERVAL")
    billing_starter_plan_description: str = Field(
        default="Yahoo Finance API access for no-code workflows",
        alias="BILLING_STARTER_PLAN_DESCRIPTION",
    )

    database_url: str = Field(default="sqlite:///./dev.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    default_rate_limit: str = Field(default="60/minute", alias="DEFAULT_RATE_LIMIT")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
