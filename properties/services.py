from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urljoin

import requests
from django.conf import settings

from accounts.services import (
    AuthServiceError,
    BackendUnavailableError,
    UnauthorizedRefreshError,
    authenticated_request,
)
from accounts.utils import is_habita_authenticated


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
        "description": item.get("description") or "",
        "location": _build_location(item),
        "price": _format_price(item.get("price")),
        "raw_price": item.get("price"),
        "bedrooms": item.get("bedrooms", 0),
        "bathrooms": item.get("bathrooms", 0),
        "parking_spaces": item.get("parking_spaces"),
        "area": _format_area(item.get("area_m2")),
        "image_url": image_url,
        "property_type": (item.get("property_type") or "").capitalize(),
        "status": (item.get("status") or "").capitalize(),
        "is_published": item.get("is_published", False),
    }


def _normalize_property_detail(item: dict) -> dict:
    images = item.get("images") or []
    normalized_images = []

    for image in images:
        normalized_images.append(
            {
                "id": image.get("id"),
                "image_url": _absolute_media_url(image.get("file_url")),
                "alt_text": image.get("alt_text") or item.get("title", "Imagen de propiedad"),
                "is_cover": image.get("is_cover", False),
            }
        )

    return {
        "id": item.get("id"),
        "title": item.get("title", "Propiedad sin título"),
        "description": item.get("description") or "Sin descripción disponible.",
        "price": _format_price(item.get("price")),
        "raw_price": item.get("price"),
        "property_type": (item.get("property_type") or "").capitalize(),
        "status": (item.get("status") or "").capitalize(),
        "address_line": item.get("address_line") or "",
        "neighborhood": item.get("neighborhood") or "",
        "city": item.get("city") or "",
        "state": item.get("state") or "",
        "location": _build_location(item),
        "bedrooms": item.get("bedrooms", 0),
        "bathrooms": item.get("bathrooms", 0),
        "parking_spaces": item.get("parking_spaces"),
        "area": _format_area(item.get("area_m2")),
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
        "is_published": item.get("is_published", False),
        "images": normalized_images,
    }


def get_properties_list(filters: dict, page: int = 1, limit: int = 9) -> tuple[list[dict], dict, str | None]:
    skip = max(page - 1, 0) * limit

    params = {
        "limit": limit,
        "skip": skip,
    }

    allowed_filters = [
        "q",
        "city",
        "state",
        "property_type",
        "status",
        "min_price",
        "max_price",
        "bedrooms",
        "bathrooms",
        "is_published",
    ]

    for key in allowed_filters:
        value = filters.get(key)
        if value not in (None, "", []):
            params[key] = value

    url = f"{settings.BACKEND_API_BASE_URL}/properties/"

    try:
        response = requests.get(
            url,
            params=params,
            timeout=settings.BACKEND_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return [], {"total": 0, "skip": skip, "limit": limit, "returned": 0}, "No fue posible cargar las propiedades."
    except ValueError:
        return [], {"total": 0, "skip": skip, "limit": limit, "returned": 0}, "La API devolvió un formato inválido."

    data = payload.get("data", {})
    items = data.get("items", [])
    pagination = data.get("pagination", {"total": 0, "skip": skip, "limit": limit, "returned": 0})

    return [_normalize_property_card(item) for item in items], pagination, None


def get_property_detail(property_id: int) -> tuple[dict | None, str | None]:
    url = f"{settings.BACKEND_API_BASE_URL}/properties/{property_id}"

    try:
        response = requests.get(
            url,
            timeout=settings.BACKEND_REQUEST_TIMEOUT,
        )

        if response.status_code == 404:
            return None, "Propiedad no encontrada."

        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return None, "No fue posible cargar el detalle de la propiedad."
    except ValueError:
        return None, "La API devolvió un formato inválido."

    data = payload.get("data")
    if not data:
        return None, "La propiedad no tiene datos válidos."

    return _normalize_property_detail(data), None


def get_user_favorite_ids(request, user_id: int, limit: int = 200) -> set[int]:
    if not is_habita_authenticated(request):
        return set()

    try:
        response = authenticated_request(
            request,
            "GET",
            f"/users/{user_id}/favorites",
            params={"limit": limit, "skip": 0},
        )

        if response.status_code != 200:
            return set()

        payload = response.json()
        if not isinstance(payload, list):
            return set()

        return {item.get("id") for item in payload if item.get("id") is not None}

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return set()


def get_favorite_status(request, user_id: int, property_id: int) -> bool:
    if not is_habita_authenticated(request):
        return False

    try:
        response = authenticated_request(
            request,
            "GET",
            f"/users/{user_id}/favorites/{property_id}/exists",
        )

        if response.status_code != 200:
            return False

        payload = response.json()
        return bool(payload.get("is_favorite"))

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return False


def add_favorite(request, user_id: int, property_id: int) -> tuple[bool, str]:
    try:
        response = authenticated_request(
            request,
            "POST",
            f"/users/{user_id}/favorites/{property_id}",
        )

        if response.status_code in (200, 201):
            return True, "Propiedad agregada a favoritos."

        return False, "No fue posible agregar la propiedad a favoritos."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible agregar la propiedad a favoritos."


def remove_favorite(request, user_id: int, property_id: int) -> tuple[bool, str]:
    try:
        response = authenticated_request(
            request,
            "DELETE",
            f"/users/{user_id}/favorites/{property_id}",
        )

        if response.status_code == 200:
            return True, "Propiedad eliminada de favoritos."

        return False, "No fue posible eliminar la propiedad de favoritos."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible eliminar la propiedad de favoritos."


def build_query_string(filters: dict) -> str:
    clean_filters = {}
    for key, value in filters.items():
        if value not in (None, "", []):
            clean_filters[key] = value
    return urlencode(clean_filters)