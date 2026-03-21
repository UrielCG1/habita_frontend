from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin
from typing import Optional

from django.conf import settings
from properties.services import _property_image_proxy_url

from .services import (
    AuthServiceError,
    BackendUnavailableError,
    UnauthorizedRefreshError,
    authenticated_request,
)


def _format_price(value) -> str:
    if value in (None, ""):
        return "No disponible"

    try:
        amount = Decimal(str(value))
        return f"${amount:,.0f}"
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def _normalize_property(item: dict) -> dict:
    cover_image = item.get("cover_image") or {}
    owner = item.get("owner") or {}

    neighborhood = item.get("neighborhood")
    city = item.get("city")
    state = item.get("state")
    parts = [part for part in [neighborhood, city, state] if part]
    location = ", ".join(parts) if parts else "Ubicación no disponible"

    return {
        "id": item.get("id"),
        "title": item.get("title", "Propiedad sin título"),
        "location": location,
        "owner_name": owner.get("full_name", "Sin propietario"),
        "price": _format_price(item.get("price")),
        "status": (item.get("status") or "").capitalize(),
        "image_url": _property_image_proxy_url(cover_image.get("id")),
    }


def _normalize_recent_request(item: dict) -> dict:
    user = item.get("user") or {}
    property_data = item.get("property") or {}

    return {
        "id": item.get("id"),
        "user_name": user.get("full_name", "Usuario"),
        "property_title": property_data.get("title", "Propiedad"),
        "status": (item.get("status") or "").capitalize(),
        "message": item.get("message") or "",
        "created_at": item.get("created_at"),
    }


def get_admin_dashboard(request) -> tuple[Optional[dict], Optional[str]]:
    try:
        response = authenticated_request(
            request,
            "GET",
            "/admin/dashboard",
        )

        if response.status_code == 403:
            return None, "No tienes permisos para acceder al panel admin."

        if response.status_code != 200:
            return None, "No fue posible cargar el panel admin."

        payload = response.json()
        data = payload.get("data") or {}

        summary = data.get("summary") or {}
        recent_properties = data.get("recent_properties") or []
        recent_requests = data.get("recent_requests") or []

        return {
            "summary": {
                "total_properties": summary.get("total_properties", 0),
                "active_requests": summary.get("active_requests", 0),
                "total_users": summary.get("total_users", 0),
                "projected_income": _format_price(summary.get("projected_income")),
            },
            "recent_properties": [_normalize_property(item) for item in recent_properties],
            "recent_requests": [_normalize_recent_request(item) for item in recent_requests],
        }, None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return None, "No fue posible cargar el panel admin."