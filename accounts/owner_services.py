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
    property_type = (item.get("property_type") or "").capitalize()
    status_value = (item.get("status") or "").capitalize()

    return {
        "id": item.get("id"),
        "title": item.get("title", "Propiedad sin título"),
        "location": _build_location(item),
        "price": _format_price(item.get("price")),
        "property_type": property_type,
        "property_type_label": property_type or "Propiedad",
        "status": status_value,
        "status_label": status_value or "Disponible",
        "bedrooms": item.get("bedrooms", 0),
        "bathrooms": item.get("bathrooms", 0),
        "cover_image_url": _property_image_proxy_url(cover_image.get("id")),
        "is_published": item.get("is_published", False),
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



def get_owner_requests_overview(
    request,
    owner_id: int,
    status: Optional[str] = None,
    property_id: Optional[int] = None,
) -> tuple[list[dict], Optional[str]]:
    properties, properties_error = get_owner_properties(request, owner_id=owner_id, limit=200)

    if properties_error:
        return [], properties_error

    if property_id is not None:
        properties = [item for item in properties if item.get("id") == property_id]

    all_requests = []

    for property_item in properties:
        property_requests, property_requests_error = get_property_rental_requests(
            request,
            property_id=property_item["id"],
            status=None,
        )

        if property_requests_error:
            continue

        for req in property_requests:
            req["property_status"] = property_item.get("status")
            req["property_status_label"] = property_item.get("status_label")
            req["property_price"] = property_item.get("price")
            req["property_location"] = property_item.get("location")
            req["property_cover_image_url"] = property_item.get("cover_image_url") or req.get("property_cover_image_url")
            all_requests.append(req)

    if status:
        normalized_status = str(status).strip().lower()
        all_requests = [item for item in all_requests if item.get("status_code") == normalized_status]

    all_requests.sort(key=lambda req: (req.get("created_at_sort") is None, req.get("created_at_sort") or datetime.min), reverse=True)
    return all_requests, None






### views requests patch ###

@habita_role_required("owner", "admin")
def owner_property_requests_view(request, property_id: int):
    habita_user = get_habita_user(request)
    status_filter = request.GET.get("status", "").strip() or ""

    properties, _ = get_owner_properties(request, owner_id=habita_user["id"])
    owned_property = next((item for item in properties if item["id"] == property_id), None)

    if not owned_property:
        messages.error(request, "No tienes acceso a esa propiedad.")
        return redirect("accounts:owner-properties")

    all_requests, rental_requests_error = get_property_rental_requests(
        request,
        property_id=property_id,
        status=None,
    )

    request_summary = build_owner_requests_summary(all_requests)
    rental_requests = all_requests
    if status_filter:
        rental_requests = [item for item in all_requests if item.get("status_code") == status_filter]

    return render(
        request,
        "accounts/owner_property_requests.html",
        {
            "habita_user": habita_user,
            "owned_property": owned_property,
            "rental_requests": rental_requests,
            "rental_requests_error": rental_requests_error,
            "status_filter": status_filter,
            "request_summary": request_summary,
            "current_url": request.get_full_path(),
        },
    )


@require_POST
@habita_role_required("owner", "admin")
def owner_update_request_status_view(request, property_id: int, request_id: int):
    form = OwnerRequestStatusForm(request.POST)
    next_url = request.POST.get("next_url") or reverse("accounts:owner-property-requests", args=[property_id])

    if not form.is_valid():
        messages.error(request, "Revisa los datos del cambio de estado.")
        return redirect(next_url)

    success, message = patch_rental_request_status(
        request=request,
        request_id=request_id,
        status=form.cleaned_data["status"],
        owner_notes=form.cleaned_data.get("owner_notes", ""),
    )

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect(next_url)


@habita_role_required("owner", "admin")
def owner_requests_view(request):
    habita_user = get_habita_user(request)
    status_filter = request.GET.get("status", "").strip() or ""
    property_filter = request.GET.get("property_id", "").strip() or ""

    selected_property_id = None
    if property_filter.isdigit():
        selected_property_id = int(property_filter)

    owner_properties, properties_error = get_owner_properties(request, owner_id=habita_user["id"], limit=200)

    all_requests, rental_requests_error = get_owner_requests_overview(
        request,
        owner_id=habita_user["id"],
        property_id=selected_property_id,
        status=None,
    )

    request_summary = build_owner_requests_summary(all_requests)
    rental_requests = all_requests
    if status_filter:
        rental_requests = [item for item in all_requests if item.get("status_code") == status_filter]

    return render(
        request,
        "accounts/owner_requests.html",
        {
            "habita_user": habita_user,
            "owner_properties": owner_properties,
            "owner_properties_error": properties_error,
            "rental_requests": rental_requests,
            "rental_requests_error": rental_requests_error,
            "status_filter": status_filter,
            "property_filter": property_filter,
            "request_summary": request_summary,
            "current_url": request.get_full_path(),
        },
    )
