from __future__ import annotations

from fastapi import APIRouter, Query

from .internal_dashboard import (
    ActivityStatus,
    CreateKeyRequest,
    MetricsRange,
    OverviewRange,
    activate_dashboard_key,
    create_dashboard_key,
    get_dashboard_activity,
    get_dashboard_keys,
    get_dashboard_metrics,
    get_dashboard_overview,
    revoke_dashboard_key,
    rotate_dashboard_key,
)

router = APIRouter(prefix="/dashboard/api", tags=["customer-dashboard"])


@router.get("/overview")
def get_customer_dashboard_overview(range: OverviewRange = Query(default="24h")):
    payload = get_dashboard_overview(range)
    return {
        **payload,
        "source": "customer-placeholder",
    }


@router.get("/metrics")
def get_customer_dashboard_metrics(range: MetricsRange = Query(default="24h")):
    payload = get_dashboard_metrics(range)
    return {
        **payload,
        "source": "customer-placeholder",
    }


@router.get("/activity")
def get_customer_dashboard_activity(
    status: ActivityStatus | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
):
    payload = get_dashboard_activity(status=status, action=action, limit=limit)
    return {
        **payload,
        "source": "customer-placeholder",
    }


@router.get("/keys")
def get_customer_dashboard_keys():
    payload = get_dashboard_keys()
    return {
        **payload,
        "source": "customer-mock-store",
    }


@router.post("/keys/create")
def create_customer_dashboard_key(payload: CreateKeyRequest):
    response = create_dashboard_key(payload)
    response["source"] = "customer-mock-store"
    return response


@router.post("/keys/{key_id}/rotate")
def rotate_customer_dashboard_key(key_id: str):
    response = rotate_dashboard_key(key_id)
    response["source"] = "customer-mock-store"
    return response


@router.post("/keys/{key_id}/revoke")
def revoke_customer_dashboard_key(key_id: str):
    response = revoke_dashboard_key(key_id)
    response["source"] = "customer-mock-store"
    return response


@router.post("/keys/{key_id}/activate")
def activate_customer_dashboard_key(key_id: str):
    response = activate_dashboard_key(key_id)
    response["source"] = "customer-mock-store"
    return response
