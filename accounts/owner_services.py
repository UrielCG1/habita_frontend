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
    safe_limit = max(1, min(int(limit or 100), 100))

    try:
        response = authenticated_request(
            request,
            "GET",
            "/properties/",
            params={
                "owner_id": owner_id,
                "limit": safe_limit,
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
                    "sort_order": image.get("sort_order", 0),
                }
            )

        normalized_images.sort(
            key=lambda image: (
                not image.get("is_cover", False),
                image.get("sort_order", 0),
                image.get("id", 0),
            )
        )

        latitude = data.get("latitude")
        longitude = data.get("longitude")

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
            "postal_code": data.get("postal_code") or "",
            "bedrooms": data.get("bedrooms", 0),
            "bathrooms": data.get("bathrooms", 0),
            "parking_spaces": data.get("parking_spaces"),
            "area_m2": data.get("area_m2"),
            "latitude": latitude,
            "longitude": longitude,
            "has_coordinates": latitude is not None and longitude is not None,
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

        if response.status_code != 200:
            return False, "No fue posible actualizar la imagen principal."

        return True, "Imagen principal actualizada correctamente."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible actualizar la imagen principal."


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
    properties, properties_error = get_owner_properties(request, owner_id=owner_id, limit=100)

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




def reorder_property_images(request, ordered_image_ids: list[int]) -> tuple[bool, str]:
    """
    Reordena las imágenes de una propiedad actualizando sort_order
    en el backend vía PATCH /property-images/{image_id}.

    ordered_image_ids:
        Lista ordenada de IDs de imágenes, por ejemplo:
        [14, 9, 6, 3]
    """

    if not ordered_image_ids:
        return True, "Sin cambios en el orden de imágenes."

    try:
        for sort_order, image_id in enumerate(ordered_image_ids):
            response = authenticated_request(
                request,
                "PATCH",
                f"/property-images/{image_id}",
                json={"sort_order": sort_order},
            )

            if response.status_code != 200:
                return False, "No fue posible guardar el orden de las imágenes."

        return True, "Orden de imágenes actualizado correctamente."

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError):
        return False, "No fue posible guardar el orden de las imágenes."
    
    
def get_owner_dashboard_reputation(request, owner_id: int) -> tuple[dict, Optional[str]]:
    try:
        response = authenticated_request(
            request,
            "GET",
            f"/owners/{owner_id}/dashboard/reputation",
        )

        if response.status_code != 200:
            return {}, "No fue posible cargar la reputación del owner."

        payload = response.json()
        data = payload.get("data") or {}

        return {
            "favorites_count": data.get("favorites_count", 0),
            "reviews_count": data.get("reviews_count", 0),
            "average_rating": data.get("average_rating", 0),
            "rating_breakdown": data.get(
                "rating_breakdown",
                {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0},
            ),
            "latest_reviews": data.get("latest_reviews", []),
            "property_review_summary": data.get("property_review_summary", []),
        }, None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return {}, "No fue posible cargar la reputación del owner."
    

REPORT_TYPE_LABELS = {
    "summary": "Resumen general",
    "properties": "Propiedades",
    "requests": "Solicitudes",
    "reputation": "Reputación",
}

from django.conf import settings


def get_owner_reports_summary(
    request,
    owner_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[dict, Optional[str]]:
    params = {}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    try:
        response = authenticated_request(
            request,
            "GET",
            f"/owners/{owner_id}/dashboard/reports-summary",
            params=params,
        )

        if response.status_code != 200:
            return {}, "No fue posible cargar el resumen de reportes."

        payload = response.json()
        data = payload.get("data") or {}

        summary_cards = data.get("summary_cards") or {}
        report_types = data.get("report_types") or []
        available_properties = data.get("available_properties") or []
        recent_reports = data.get("recent_reports") or []

        normalized_report_types = []
        for item in report_types:
            code = (item.get("code") or "").strip()
            normalized_report_types.append(
                {
                    "code": code,
                    "label": item.get("label") or REPORT_TYPE_LABELS.get(code, code.title()),
                    "description": item.get("description") or "",
                }
            )

        normalized_recent_reports = []
        for item in recent_reports:
            raw_download_url = item.get("download_url") or ""
            absolute_download_url = (
                f"{settings.BACKEND_API_BASE_URL.rstrip('/')}{raw_download_url}"
                if raw_download_url
                else ""
            )

            normalized_recent_reports.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name") or "Reporte",
                    "report_type": item.get("report_type"),
                    "report_type_label": item.get("report_type_label")
                    or REPORT_TYPE_LABELS.get(item.get("report_type"), "Reporte"),
                    "created_at_display": item.get("created_at_display") or "",
                    "download_url": absolute_download_url,
                }
            )

        return {
            "summary_cards": {
                "properties_count": summary_cards.get("properties_count", 0),
                "requests_count": summary_cards.get("requests_count", 0),
                "reviews_count": summary_cards.get("reviews_count", 0),
                "average_rating": summary_cards.get("average_rating", 0),
            },
            "report_types": normalized_report_types,
            "available_properties": available_properties,
            "recent_reports": normalized_recent_reports,
        }, None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return {}, "No fue posible cargar el resumen de reportes."


def export_owner_report_pdf(
    request,
    owner_id: int,
    payload: dict,
) -> tuple[dict, Optional[str]]:
    try:
        response = authenticated_request(
            request,
            "POST",
            f"/owners/{owner_id}/reports/export",
            json=payload,
        )

        if response.status_code not in (200, 201):
            return {}, "No fue posible generar el reporte PDF."

        body = response.json()
        data = body.get("data") or {}

        return {
            "report_id": data.get("report_id"),
            "report_name": data.get("report_name") or "Reporte",
            "report_type": data.get("report_type"),
            "format": data.get("format") or "pdf",
            "generated_at_display": data.get("generated_at_display") or "",
            "download_url": data.get("download_url") or "",
        }, None

    except (AuthServiceError, BackendUnavailableError, UnauthorizedRefreshError, ValueError):
        return {}, "No fue posible generar el reporte PDF."