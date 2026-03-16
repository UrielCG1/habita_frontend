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
                    "image_url": _absolute_media_url(image.get("file_url")),
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