from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import requests
from django.conf import settings


def _backend_base_url() -> str:
    return settings.BACKEND_API_BASE_URL.removesuffix("/api")


def _absolute_media_url(file_url: str | None) -> str | None:
    if not file_url:
        return None

    if file_url.startswith("http://") or file_url.startswith("https://"):
        return file_url

    return urljoin(f"{_backend_base_url()}/", file_url.lstrip("/"))


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


def get_featured_properties(limit: int = 3) -> tuple[list[dict], str | None]:
    url = f"{settings.BACKEND_API_BASE_URL}/properties/"
    params = {
        "limit": limit,
        "skip": 0,
        "status": "available",
        "is_published": "true",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=settings.BACKEND_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        items = payload.get("data", {}).get("items", [])
        results = []

        for item in items:
            cover_image = item.get("cover_image") or {}
            image_url = _absolute_media_url(cover_image.get("file_url"))

            results.append(
                {
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
            )

        return results, None

    except requests.RequestException:
        return [], "No fue posible obtener las propiedades destacadas en este momento."
    except ValueError:
        return [], "La API respondió con un formato no válido."