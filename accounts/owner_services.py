from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin
from typing import Optional

from django.conf import settings

from .services import (
    AuthServiceError,
    BackendUnavailableError,
    UnauthorizedRefreshError,
    authenticated_request,
)


def _backend_root() -> str:
    return settings.BACKEND_API_BASE_URL.removesuffix("/api")


def _absolute_media_url(file_url: Optional[str]) -> Optional[str]:
    if not file_url:
        return None

    if file_url.startswith("http://") or file_url.startswith("https://"):
        return file_url

    return urljoin(f"{_backend_root()}/", file_url.lstrip("/"))


def _format_price(value) -> str:
    if value in (None, ""):
        return "Precio no disponible"

    try:
        amount = Decimal(str(value))
        return f"${amount:,.0f}/mes"
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def _build_location(item: dict) -> str:
    neighborhood = item.get("neighborhood")
    city = item.get("city")
    state = item.get("state")
    parts = [part for part in [neighborhood, city, state] if part]
    return ", ".join(parts) if parts else "Ubicación no disponible"


def _normalize_owner_property(item: dict) -> dict:
    cover_image = item.get("cover_image") or {}

    return {
        "id": item.get("id"),
        "title": item.get("title", "Propiedad sin título"),
        "location": _build_location(item),
        "price": _format_price(item.get("price")),
        "property_type": (item.get("property_type") or "").capitalize(),
        "status": (item.get("status") or "").capitalize(),
        "bedrooms": item.get("bedrooms", 0),
        "bathrooms": item.get("bathrooms", 0),
        "cover_image_url": _absolute_media_url(cover_image.get("file_url")),
        "is_published": item.get("is_published", False),
    }


def _normalize_rental_request(item: dict) -> dict:
    user = item.get("user") or {}
    property_data = item.get("property") or {}
    cover_image = property_data.get("cover_image") or {}

    return {
        "id": item.get("id"),
        "status": (item.get("status") or "").capitalize(),
        "message": item.get("message") or "",
        "owner_notes": item.get("owner_notes") or "",
        "move_in_date": item.get("move_in_date"),
        "monthly_budget": _format_price(item.get("monthly_budget")) if item.get("monthly_budget") else "No especificado",
        "user_name": user.get("full_name", "Usuario"),
        "user_email": user.get("email", ""),
        "user_phone": user.get("phone", ""),
        "property_title": property_data.get("title", "Propiedad"),
        "property_id": property_data.get("id"),
        "property_image_url": _absolute_media_url(cover_image.get("file_url")),
    }


def get_owner_properties(request, owner_id: int, limit: int = 100) -> tuple[list[dict], Optional[str]]:
    try:
        response = authenticated_request(
            request,
            "GET",
            "/properties/",
            params={
                "owner_id": owner_id,
                "limit": limit,
                "skip": 0,
            },
        )

        if response.status_code != 200:
            return [], "No fue posible cargar tus propiedades."

        payload = response.json()
        items = payload.get("data", {}).get("items", [])
        return [_normalize_owner_property(item) for item in items], None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return [], "No fue posible cargar tus propiedades."


def get_property_rental_requests(request, property_id: int, status: Optional[str] = None) -> tuple[list[dict], Optional[str]]:
    params = {
        "limit": 100,
        "skip": 0,
    }
    if status:
        params["status"] = status

    try:
        response = authenticated_request(
            request,
            "GET",
            f"/properties/{property_id}/rental-requests",
            params=params,
        )

        if response.status_code != 200:
            return [], "No fue posible cargar las solicitudes de esta propiedad."

        payload = response.json()
        items = payload if isinstance(payload, list) else []
        return [_normalize_rental_request(item) for item in items], None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return [], "No fue posible cargar las solicitudes de esta propiedad."


def patch_rental_request_status(request, request_id: int, status: str, owner_notes: str = "") -> tuple[bool, str]:
    try:
        response = authenticated_request(
            request,
            "PATCH",
            f"/rental-requests/{request_id}",
            json={
                "status": status,
                "owner_notes": owner_notes or None,
            },
        )

        if response.status_code == 200:
            return True, "Solicitud actualizada correctamente."

        return False, "No fue posible actualizar la solicitud."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible actualizar la solicitud."