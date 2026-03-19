from decimal import Decimal, InvalidOperation
from typing import Optional
from urllib.parse import urljoin

import requests
from django.conf import settings


PROPERTY_TYPE_LABELS = {
    "house": "Casa",
    "apartment": "Departamento",
    "office": "Oficina",
    "studio": "Estudio",
    "room": "Habitación",
    "land": "Terreno",
}

STATUS_LABELS = {
    "available": "Disponible",
    "reserved": "Reservada",
    "rented": "Rentada",
    "inactive": "Inactiva",
}



def _backend_base_url() -> str:
    return settings.BACKEND_API_BASE_URL.removesuffix("/api")



def _absolute_media_url(file_url: Optional[str]) -> Optional[str]:
    if not file_url:
        return None

    if file_url.startswith(("http://", "https://")):
        return file_url

    return urljoin(f"{_backend_base_url()}/", file_url.lstrip("/"))



def _to_decimal(value) -> Optional[Decimal]:
    if value in (None, ""):
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None



def _format_price(value) -> str:
    amount = _to_decimal(value)
    if amount is None:
        return "Precio no disponible"
    return f"${amount:,.0f}/mes"



def _format_area(value) -> str:
    amount = _to_decimal(value)
    if amount is None:
        return "N/D"
    return f"{amount.normalize()} m²" if amount % 1 else f"{int(amount)} m²"



def _build_location(item: dict) -> str:
    neighborhood = item.get("neighborhood")
    city = item.get("city")
    state = item.get("state")

    parts = [part for part in [neighborhood, city, state] if part]
    return ", ".join(parts) if parts else "Ubicación no disponible"



def _property_type_label(value: Optional[str]) -> str:
    if not value:
        return "Propiedad"
    return PROPERTY_TYPE_LABELS.get(value, value.replace("_", " ").title())



def _status_label(value: Optional[str]) -> str:
    if not value:
        return "Sin estatus"
    return STATUS_LABELS.get(value, value.replace("_", " ").title())



def _short_description(value: Optional[str], limit: int = 120) -> str:
    if not value:
        return "Explora esta propiedad y conoce más detalles desde su ficha completa."

    clean_value = " ".join(str(value).split())
    if len(clean_value) <= limit:
        return clean_value
    return f"{clean_value[:limit].rstrip()}..."



def _placeholder_image() -> str:
    return "https://placehold.co/900x620?text=HABITA"



def _map_property_card(item: dict) -> dict:
    cover_image = item.get("cover_image") or {}
    owner = item.get("owner") or {}
    image_url = _absolute_media_url(cover_image.get("file_url")) or _placeholder_image()

    bedrooms = item.get("bedrooms") or 0
    bathrooms = item.get("bathrooms") or 0
    parking_spaces = item.get("parking_spaces") or 0

    return {
        "id": item.get("id"),
        "title": item.get("title") or "Propiedad sin título",
        "description": item.get("description") or "",
        "short_description": _short_description(item.get("description")),
        "location": _build_location(item),
        "price": item.get("price"),
        "price_display": _format_price(item.get("price")),
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "parking_spaces": parking_spaces,
        "bedrooms_display": f"{bedrooms} rec.",
        "bathrooms_display": f"{bathrooms} baños",
        "parking_spaces_display": f"{parking_spaces} est.",
        "area_m2": item.get("area_m2"),
        "area_display": _format_area(item.get("area_m2")),
        "cover_image_url": image_url,
        "cover_image_alt": cover_image.get("alt_text") or item.get("title") or "Propiedad",
        "property_type": item.get("property_type") or "",
        "property_type_label": _property_type_label(item.get("property_type")),
        "status": item.get("status") or "",
        "status_label": _status_label(item.get("status")),
        "owner_name": owner.get("full_name") or "HABITA",
        "owner_email": owner.get("email") or "",
        "is_published": bool(item.get("is_published")),
        "address_line": item.get("address_line") or "",
        "city": item.get("city") or "",
        "state": item.get("state") or "",
        "neighborhood": item.get("neighborhood") or "",
    }



def get_featured_properties(limit: int = 6) -> tuple[list[dict], Optional[str]]:
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
        results = [_map_property_card(item) for item in items]
        return results, None

    except requests.RequestException:
        return [], "No fue posible obtener las propiedades destacadas en este momento."
    except ValueError:
        return [], "La API respondió con un formato no válido."
