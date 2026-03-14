import requests
from decimal import Decimal, InvalidOperation
from django.conf import settings


def _build_absolute_media_url(file_url: str | None) -> str:
    if not file_url:
        return settings.STATIC_URL + "img/property-placeholder.jpg"

    if file_url.startswith("http://") or file_url.startswith("https://"):
        return file_url

    base = settings.BACKEND_MEDIA_BASE_URL.rstrip("/")
    path = file_url.lstrip("/")

    if path.startswith("media/"):
        path = path[len("media/"):]

    return f"{base}/{path}"


def _format_price(value) -> str:
    try:
        amount = Decimal(str(value))
        return f"${amount:,.0f}"
    except (InvalidOperation, TypeError, ValueError):
        return "$0"


def _format_location(item: dict) -> str:
    city = item.get("city") or ""
    state = item.get("state") or ""
    location = ", ".join(part for part in [city, state] if part)
    return location or "Ubicación no disponible"


def _normalize_property_card(item: dict) -> dict:
    cover_image = item.get("cover_image") or {}
    return {
        "id": item.get("id"),
        "title": item.get("title") or "Propiedad sin título",
        "price": item.get("price"),
        "price_display": _format_price(item.get("price")),
        "location": _format_location(item),
        "city": item.get("city") or "",
        "state": item.get("state") or "",
        "property_type": item.get("property_type") or "Propiedad",
        "status": item.get("status") or "",
        "bedrooms": item.get("bedrooms") or 0,
        "bathrooms": item.get("bathrooms") or 0,
        "area_m2": item.get("area_m2") or item.get("area") or 0,
        "cover_image_url": _build_absolute_media_url(cover_image.get("file_url")),
        "cover_image_alt": item.get("title") or "Imagen de propiedad",
        "is_published": item.get("is_published", False),
    }


def _normalize_property_detail(item: dict) -> dict:
    images = item.get("images") or []
    normalized_images = []

    for image in images:
        normalized_images.append({
            "id": image.get("id"),
            "image_url": _build_absolute_media_url(image.get("file_url")),
            "alt": item.get("title") or "Imagen de propiedad",
        })

    if not normalized_images:
        normalized_images.append({
            "id": None,
            "image_url": settings.STATIC_URL + "img/property-placeholder.jpg",
            "alt": item.get("title") or "Imagen de propiedad",
        })

    return {
        "id": item.get("id"),
        "title": item.get("title") or "Propiedad sin título",
        "description": item.get("description") or "",
        "price": item.get("price"),
        "price_display": _format_price(item.get("price")),
        "location": _format_location(item),
        "city": item.get("city") or "",
        "state": item.get("state") or "",
        "address": item.get("address") or "",
        "property_type": item.get("property_type") or "Propiedad",
        "status": item.get("status") or "",
        "bedrooms": item.get("bedrooms") or 0,
        "bathrooms": item.get("bathrooms") or 0,
        "area_m2": item.get("area_m2") or item.get("area") or 0,
        "images": normalized_images,
        "cover_image_url": normalized_images[0]["image_url"],
        "is_published": item.get("is_published", False),
    }


def get_properties(filters: dict | None = None) -> dict:
    filters = filters or {}

    params = {
        "q": filters.get("q") or None,
        "city": filters.get("city") or None,
        "property_type": filters.get("property_type") or None,
        "min_price": filters.get("min_price") or None,
        "max_price": filters.get("max_price") or None,
        "bedrooms": filters.get("bedrooms") or None,
        "bathrooms": filters.get("bathrooms") or None,
        "status": filters.get("status") or None,
        "is_published": True,
        "skip": filters.get("skip", 0),
        "limit": filters.get("limit", 9),
    }

    params = {k: v for k, v in params.items() if v not in [None, ""]}

    url = f"{settings.BACKEND_API_BASE_URL.rstrip('/')}/properties/"

    try:
        response = requests.get(
            url,
            params=params,
            timeout=settings.BACKEND_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        if not payload.get("success"):
            return {
                "success": False,
                "items": [],
                "pagination": None,
                "error_message": "No fue posible obtener las propiedades.",
            }

        data = payload.get("data") or {}
        items = data.get("items") or []
        pagination = data.get("pagination") or {}

        return {
            "success": True,
            "items": [_normalize_property_card(item) for item in items],
            "pagination": pagination,
            "error_message": None,
        }

    except requests.RequestException:
        return {
            "success": False,
            "items": [],
            "pagination": None,
            "error_message": "No fue posible conectar con el servicio de propiedades.",
        }


def get_property_detail(property_id: int) -> dict:
    url = f"{settings.BACKEND_API_BASE_URL.rstrip('/')}/properties/{property_id}"

    try:
        response = requests.get(
            url,
            timeout=settings.BACKEND_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        if not payload.get("success"):
            return {
                "success": False,
                "item": None,
                "error_message": "No se encontró la propiedad solicitada.",
            }

        item = payload.get("data") or {}

        return {
            "success": True,
            "item": _normalize_property_detail(item),
            "error_message": None,
        }

    except requests.RequestException:
        return {
            "success": False,
            "item": None,
            "error_message": "No fue posible obtener el detalle de la propiedad.",
        }
