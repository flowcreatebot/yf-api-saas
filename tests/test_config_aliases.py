import pytest

from app.config import Settings

pytestmark = [pytest.mark.integration]


@pytest.mark.parametrize(
    "canonical_key,alias_key,canonical_value,alias_value,field_name",
    [
        ("STRIPE_SECRET_KEY", "STRIPE_API_KEY", "sk_test_canonical", "sk_test_alias", "stripe_secret_key"),
        ("STRIPE_PRICE_ID_MONTHLY", "STRIPE_PRICE_ID", "price_canonical", "price_alias", "stripe_price_id_monthly"),
        (
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_ENDPOINT_SECRET",
            "whsec_canonical",
            "whsec_alias",
            "stripe_webhook_secret",
        ),
    ],
)
def test_canonical_stripe_env_values_take_precedence(
    monkeypatch,
    canonical_key: str,
    alias_key: str,
    canonical_value: str,
    alias_value: str,
    field_name: str,
):
    monkeypatch.setenv(canonical_key, canonical_value)
    monkeypatch.setenv(alias_key, alias_value)

    settings = Settings(_env_file=None)

    assert getattr(settings, field_name) == canonical_value


@pytest.mark.parametrize(
    "canonical_key,alias_key,alias_value,field_name",
    [
        ("STRIPE_SECRET_KEY", "STRIPE_API_KEY", "sk_test_alias", "stripe_secret_key"),
        ("STRIPE_SECRET_KEY", "STRIPE_KEY", "sk_test_alias_2", "stripe_secret_key"),
        ("STRIPE_SECRET_KEY", "STRIPE_SECRET", "sk_test_alias_3", "stripe_secret_key"),
        ("STRIPE_PRICE_ID_MONTHLY", "STRIPE_PRICE_ID", "price_alias", "stripe_price_id_monthly"),
        ("STRIPE_PRICE_ID_MONTHLY", "STRIPE_MONTHLY_PRICE_ID", "price_alias_2", "stripe_price_id_monthly"),
        (
            "STRIPE_PRICE_ID_MONTHLY",
            "STRIPE_PRICE_ID_STARTER_MONTHLY",
            "price_alias_3",
            "stripe_price_id_monthly",
        ),
        ("STRIPE_PRICE_ID_MONTHLY", "STRIPE_MONTHLY_PRICE", "price_alias_4", "stripe_price_id_monthly"),
        ("STRIPE_PRICE_ID_MONTHLY", "STRIPE_PRICE", "price_alias_5", "stripe_price_id_monthly"),
        ("STRIPE_WEBHOOK_SECRET", "STRIPE_ENDPOINT_SECRET", "whsec_alias", "stripe_webhook_secret"),
        (
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_WEBHOOK_ENDPOINT_SECRET",
            "whsec_alias_2",
            "stripe_webhook_secret",
        ),
        ("STRIPE_WEBHOOK_SECRET", "STRIPE_SIGNING_SECRET", "whsec_alias_3", "stripe_webhook_secret"),
        (
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_WEBHOOK_SIGNING_SECRET",
            "whsec_alias_4",
            "stripe_webhook_secret",
        ),
    ],
)
def test_stripe_env_aliases_fill_when_canonical_missing(
    monkeypatch,
    canonical_key: str,
    alias_key: str,
    alias_value: str,
    field_name: str,
):
    monkeypatch.delenv(canonical_key, raising=False)
    monkeypatch.setenv(alias_key, alias_value)

    settings = Settings(_env_file=None)

    assert getattr(settings, field_name) == alias_value


def test_stripe_price_alias_resolution_prefers_first_non_empty_candidate(monkeypatch):
    monkeypatch.delenv("STRIPE_PRICE_ID_MONTHLY", raising=False)
    monkeypatch.setenv("STRIPE_PRICE_ID", "   ")
    monkeypatch.setenv("STRIPE_MONTHLY_PRICE_ID", "price_monthly_alias")
    monkeypatch.setenv("STRIPE_PRICE", "price_generic_alias")

    settings = Settings(_env_file=None)

    assert settings.stripe_price_id_monthly == "price_monthly_alias"


def test_blank_alias_does_not_override_defaults(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.setenv("STRIPE_API_KEY", "   ")

    settings = Settings(_env_file=None)

    assert settings.stripe_secret_key == ""
