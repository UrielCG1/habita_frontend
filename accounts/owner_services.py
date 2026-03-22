from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from properties.services import _property_image_proxy_url

from .services import (
    AuthServiceError,
    BackendUnavailableError,
    UnauthorizedRefreshError,
    authenticated_request,
)

STATUS_META = {
    "pending": {
        "label": "Pendiente",
        "tone": "pending",
    },
    "accepted": {
        "label": "Aceptada",
        "tone": "accepted",
    },
    "rejected": {
        "label": "Rechazada",
        "tone": "rejected",
    },
    "cancelled": {
        "label": "Cancelada",
        "tone": "cancelled",
    },
}


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

def _parse_amount(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _format_area(value) -> str:
    if value in (None, ""):
        return "Área no disponible"

    try:
        area = Decimal(str(value))
        return f"{area.normalize()} m²" if area != area.to_integral() else f"{area.quantize(Decimal('1'))} m²"
    except (InvalidOperation, ValueError, TypeError):
        return f"{value} m²"


def _property_type_label(value: str) -> str:
    mapping = {
        "house": "Casa",
        "apartment": "Departamento",
        "studio": "Estudio",
        "room": "Habitación",
        "land": "Terreno",
        "office": "Oficina",
        "commercial": "Local comercial",
    }
    return mapping.get((value or "").lower(), (value or "Propiedad").replace("_", " ").capitalize())


def _property_status_meta(status: str, is_published: bool) -> tuple[str, str]:
    code = (status or "").lower().strip()

    mapping = {
        "available": ("available", "Disponible"),
        "occupied": ("occupied", "Ocupada"),
        "rented": ("rented", "Rentada"),
        "leased": ("rented", "Rentada"),
        "draft": ("draft", "Borrador"),
        "inactive": ("inactive", "Inactiva"),
        "paused": ("inactive", "Pausada"),
    }

    status_code, status_label = mapping.get(
        code,
        ("unpublished", "No publicada") if not is_published else ("unknown", (status or "Sin estado").capitalize()),
    )

    if not is_published and status_code in {"available", "occupied", "rented", "unknown"}:
        return "unpublished", "No publicada"

    return status_code, status_label


def _get_initials(value: str, fallback: str = "U") -> str:
    parts = [part for part in (value or "").strip().split() if part]
    return "".join(part[0].upper() for part in parts[:2]) or fallback


def _parse_datetime(value):
    if not value:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(f"{raw}T00:00:00")
        except ValueError:
            return None


def _format_date(value, include_time: bool = False) -> str:
    dt = _parse_datetime(value)
    if not dt:
        return "No especificada"

    if include_time:
        return dt.strftime("%d/%m/%Y • %H:%M")
    return dt.strftime("%d/%m/%Y")


def _normalize_status(status: Optional[str]) -> tuple[str, str, str]:
    code = (status or "pending").strip().lower() or "pending"
    meta = STATUS_META.get(code, {"label": code.capitalize(), "tone": "pending"})
    return code, meta["label"], meta["tone"]


def _normalize_owner_property(item: dict) -> dict:
    cover_image = item.get("cover_image") or {}
    is_published = item.get("is_published", False)
    status_code, status_label = _property_status_meta(item.get("status"), is_published)
    price_amount = _parse_amount(item.get("price"))

    return {
        "id": item.get("id"),
        "title": item.get("title", "Propiedad sin título"),
        "location": _build_location(item),
        "price": _format_price(item.get("price")),
        "price_amount": price_amount,
        "property_type": (item.get("property_type") or "").capitalize(),
        "property_type_label": _property_type_label(item.get("property_type")),
        "status": (item.get("status") or "").capitalize(),
        "status_code": status_code,
        "status_label": status_label,
        "bedrooms": item.get("bedrooms", 0),
        "bathrooms": item.get("bathrooms", 0),
        "parking_spaces": item.get("parking_spaces", 0),
        "area_m2": item.get("area_m2"),
        "area_display": _format_area(item.get("area_m2")),
        "cover_image_url": _property_image_proxy_url(cover_image.get("id")),
        "is_published": is_published,
    }



def _normalize_rental_request(item: dict) -> dict:
    user = item.get("user") or {}
    property_data = item.get("property") or {}
    cover_image = property_data.get("cover_image") or {}

    status_code, status_label, status_tone = _normalize_status(item.get("status"))
    user_name = user.get("full_name") or "Usuario"
    created_at = item.get("created_at")

    return {
        "id": item.get("id"),
        "status": status_label,
        "status_code": status_code,
        "status_label": status_label,
        "status_tone": status_tone,
        "message": item.get("message") or "",
        "owner_notes": item.get("owner_notes") or "",
        "move_in_date": item.get("move_in_date"),
        "move_in_date_display": _format_date(item.get("move_in_date")),
        "monthly_budget": _format_price(item.get("monthly_budget")) if item.get("monthly_budget") else "No especificado",
        "monthly_budget_raw": item.get("monthly_budget"),
        "user_name": user_name,
        "user_email": user.get("email", ""),
        "user_phone": user.get("phone", ""),
        "user_initials": _get_initials(user_name),
        "property_title": property_data.get("title", "Propiedad"),
        "property_id": property_data.get("id"),
        "property_cover_image_url": _property_image_proxy_url(cover_image.get("id")),
        "created_at": created_at,
        "created_at_display": _format_date(created_at, include_time=True),
        "created_at_sort": _parse_datetime(created_at),
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
        normalized = [_normalize_rental_request(item) for item in items]
        normalized.sort(key=lambda req: (req.get("created_at_sort") is None, req.get("created_at_sort") or datetime.min), reverse=True)
        return normalized, None

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


#### ============================
# Servicios para la sección de propietario
#### ============================

def get_owner_property_detail(request, property_id: int) -> tuple[Optional[dict], Optional[str]]:
    try:
        response = authenticated_request(
            request,
            "GET",
            f"/properties/{property_id}",
        )

        if response.status_code == 404:
            return None, "Propiedad no encontrada."

        if response.status_code != 200:
            return None, "No fue posible cargar la propiedad."

        payload = response.json()
        data = payload.get("data") or {}

        images = data.get("images") or []
        normalized_images = []
        for image in images:
            normalized_images.append(
                {
                    "id": image.get("id"),
                    "image_url": _property_image_proxy_url(image.get("id")),
                    "alt_text": image.get("alt_text") or data.get("title", "Imagen"),
                    "is_cover": image.get("is_cover", False),
                }
            )

        result = {
            "id": data.get("id"),
            "owner_id": data.get("owner_id"),
            "title": data.get("title", ""),
            "description": data.get("description") or "",
            "price": data.get("price"),
            "property_type": data.get("property_type", ""),
            "status": data.get("status", ""),
            "address_line": data.get("address_line", ""),
            "neighborhood": data.get("neighborhood") or "",
            "city": data.get("city", ""),
            "state": data.get("state", ""),
            "bedrooms": data.get("bedrooms", 0),
            "bathrooms": data.get("bathrooms", 0),
            "parking_spaces": data.get("parking_spaces"),
            "area_m2": data.get("area_m2"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "is_published": data.get("is_published", False),
            "images": normalized_images,
        }
        return result, None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return None, "No fue posible cargar la propiedad."



def create_owner_property(request, owner_id: int, payload: dict) -> tuple[Optional[dict], Optional[str]]:
    body = {
        **payload,
        "owner_id": owner_id,
    }

    try:
        response = authenticated_request(
            request,
            "POST",
            "/properties/",
            json=body,
        )

        if response.status_code != 201:
            return None, "No fue posible crear la propiedad."

        payload = response.json()
        return payload.get("data"), None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return None, "No fue posible crear la propiedad."



def patch_owner_property(request, property_id: int, payload: dict) -> tuple[Optional[dict], Optional[str]]:
    try:
        response = authenticated_request(
            request,
            "PATCH",
            f"/properties/{property_id}",
            json=payload,
        )

        if response.status_code != 200:
            return None, "No fue posible actualizar la propiedad."

        payload = response.json()
        return payload.get("data"), None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return None, "No fue posible actualizar la propiedad."



def upload_owner_property_images(
    request,
    property_id: int,
    files: list,
    alt_text: str = "",
    set_first_as_cover: bool = False,
) -> tuple[bool, str]:
    if not files:
        return True, "Sin imágenes nuevas."

    multipart_files = []
    for file_obj in files:
        multipart_files.append(
            (
                "files",
                (
                    file_obj.name,
                    file_obj.read(),
                    getattr(file_obj, "content_type", "application/octet-stream"),
                ),
            )
        )

    try:
        response = authenticated_request(
            request,
            "POST",
            f"/properties/{property_id}/images",
            files=multipart_files,
            data={
                "alt_text": alt_text or "",
                "set_first_as_cover": str(set_first_as_cover).lower(),
            },
        )

        if response.status_code == 201:
            return True, "Imágenes cargadas correctamente."

        return False, "La propiedad se guardó, pero no fue posible subir las imágenes."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "La propiedad se guardó, pero no fue posible subir las imágenes."


### panel admin ###

def delete_property_by_id(request, property_id: int) -> tuple[bool, str]:
    try:
        response = authenticated_request(
            request,
            "DELETE",
            f"/properties/{property_id}",
        )

        if response.status_code == 204:
            return True, "Propiedad eliminada correctamente."

        return False, "No fue posible eliminar la propiedad."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible eliminar la propiedad."



def set_property_image_as_cover(request, image_id: int) -> tuple[bool, str]:
    try:
        response = authenticated_request(
            request,
            "PATCH",
            f"/property-images/{image_id}",
            json={"is_cover": True},
        )

        if response.status_code == 200:
            return True, "Imagen principal actualizada correctamente."

        return False, "No fue posible marcar la imagen como principal."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible marcar la imagen como principal."



def delete_property_image_by_id(request, image_id: int) -> tuple[bool, str]:
    try:
        response = authenticated_request(
            request,
            "DELETE",
            f"/property-images/{image_id}",
        )

        if response.status_code == 200:
            return True, "Imagen eliminada correctamente."

        return False, "No fue posible eliminar la imagen."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible eliminar la imagen."



def build_owner_requests_summary(requests: list[dict]) -> dict:
    summary = {
        "total": len(requests),
        "pending": 0,
        "accepted": 0,
        "rejected": 0,
        "cancelled": 0,
    }

    for item in requests:
        code = item.get("status_code") or "pending"
        if code not in summary:
            continue
        summary[code] += 1

    summary["resolved"] = summary["accepted"] + summary["rejected"] + summary["cancelled"]
    return summary



def get_owner_requests_overview(request, owner_id: int, status: Optional[str] = None) -> tuple[list[dict], Optional[str]]:
    properties, properties_error = get_owner_properties(request, owner_id=owner_id, limit=200)

    if properties_error:
        return [], properties_error

    all_requests = []

    for property_item in properties:
        property_requests, property_requests_error = get_property_rental_requests(
            request,
            property_id=property_item["id"],
            status=status,
        )

        if property_requests_error:
            continue

        for req in property_requests:
            req["property_status"] = property_item.get("status")
            req["property_price"] = property_item.get("price")
            req["property_location"] = property_item.get("location")
            req["property_cover_image_url"] = property_item.get("cover_image_url")
            all_requests.append(req)

    return all_requests, None