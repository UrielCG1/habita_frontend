from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

from django.conf import settings

from .services import (
    AuthServiceError,
    BackendUnavailableError,
    UnauthorizedRefreshError,
    authenticated_request,
)


def _backend_root() -> str:
    return settings.BACKEND_API_BASE_URL.removesuffix("/api")


def _absolute_media_url(file_url: str | None) -> str | None:
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


def _format_area(value) -> str:
    if value in (None, ""):
        return "N/D"
    return f"{value} m²"


def _build_location(item: dict) -> str:
    neighborhood = item.get("neighborhood")
    city = item.get("city")
    state = item.get("state")
    parts = [part for part in [neighborhood, city, state] if part]
    return ", ".join(parts) if parts else "Ubicación no disponible"


def _normalize_property_card(item: dict) -> dict:
    cover_image = item.get("cover_image") or {}
    image_url = _absolute_media_url(cover_image.get("file_url"))

    return {
        "id": item.get("id"),
        "title": item.get("title", "Propiedad sin título"),
        "location": _build_location(item),
        "price": _format_price(item.get("price")),
        "bedrooms": f"{item.get('bedrooms', 0)} Rec.",
        "bathrooms": f"{item.get('bathrooms', 0)} Baños",
        "area": _format_area(item.get("area_m2")),
        "image_url": image_url,
        "property_type": item.get("property_type", "").capitalize(),
        "status": item.get("status", "").capitalize(),
    }


def _normalize_rental_request(item: dict) -> dict:
    property_data = item.get("property") or {}
    cover_image = property_data.get("cover_image") or {}
    image_url = _absolute_media_url(cover_image.get("file_url"))

    return {
        "id": item.get("id"),
        "status": (item.get("status") or "").capitalize(),
        "message": item.get("message") or "",
        "owner_notes": item.get("owner_notes") or "",
        "move_in_date": item.get("move_in_date"),
        "monthly_budget": _format_price(item.get("monthly_budget")) if item.get("monthly_budget") else "No especificado",
        "created_at": item.get("created_at"),
        "property_title": property_data.get("title", "Propiedad"),
        "property_id": property_data.get("id"),
        "property_location": _build_location(property_data),
        "property_price": _format_price(property_data.get("price")),
        "property_image_url": image_url,
    }


def get_user_favorites(request, user_id: int, limit: int = 6) -> tuple[list[dict], str | None]:
    try:
        response = authenticated_request(
            request,
            "GET",
            f"/users/{user_id}/favorites",
            params={"limit": limit, "skip": 0},
        )

        if response.status_code >= 500:
            return [], "No fue posible cargar favoritos."

        if response.status_code != 200:
            return [], "No fue posible obtener favoritos."

        payload = response.json()
        items = payload if isinstance(payload, list) else []

        return [_normalize_property_card(item) for item in items], None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return [], "No fue posible cargar favoritos."


def get_user_rental_requests(request, user_id: int, limit: int = 5) -> tuple[list[dict], str | None]:
    try:
        response = authenticated_request(
            request,
            "GET",
            f"/users/{user_id}/rental-requests",
            params={"limit": limit, "skip": 0},
        )

        if response.status_code >= 500:
            return [], "No fue posible cargar solicitudes."

        if response.status_code != 200:
            return [], "No fue posible obtener solicitudes."

        payload = response.json()
        items = payload if isinstance(payload, list) else []

        return [_normalize_rental_request(item) for item in items], None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return [], "No fue posible cargar solicitudes."


def create_rental_request(
    request,
    user_id: int,
    property_id: int,
    message: str | None = None,
    move_in_date: str | None = None,
    monthly_budget: str | None = None,
) -> tuple[bool, str]:
    payload = {
        "user_id": user_id,
        "property_id": property_id,
        "message": message or None,
        "move_in_date": move_in_date or None,
        "monthly_budget": monthly_budget or None,
    }

    try:
        response = authenticated_request(
            request,
            "POST",
            "/rental-requests",
            json=payload,
        )

        if response.status_code in (200, 201):
            data = response.json()
            message_text = (
                data.get("message")
                if isinstance(data, dict)
                else None
            )
            if not message_text and isinstance(data, dict):
                message_text = data.get("data", {}).get("message")

            return True, message_text or "Solicitud enviada correctamente."

        return False, "No fue posible enviar la solicitud."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible enviar la solicitud."


def get_dashboard_summary(request, user_id: int) -> dict:
    favorites, favorites_error = get_user_favorites(request, user_id=user_id, limit=4)
    rental_requests, requests_error = get_user_rental_requests(request, user_id=user_id, limit=4)

    return {
        "favorites": favorites,
        "favorites_count": len(favorites),
        "favorites_error": favorites_error,
        "rental_requests": rental_requests,
        "rental_requests_count": len(rental_requests),
        "rental_requests_error": requests_error,
    }