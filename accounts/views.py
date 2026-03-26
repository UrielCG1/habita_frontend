from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .admin_services import get_admin_dashboard
from .dashboard_services import (
    get_dashboard_summary,
    get_user_activity_profile,
    get_user_favorites,
    get_user_rental_requests,
)
from .decorators import habita_login_required, habita_role_required
from .forms import LoginForm, OwnerPropertyForm, OwnerRequestStatusForm, RegisterForm
from .owner_services import (
    build_owner_requests_summary,
    create_owner_property,
    delete_property_by_id,
    delete_property_image_by_id,
    get_owner_properties,
    get_owner_property_detail,
    get_owner_requests_overview,
    get_property_rental_requests,
    patch_owner_property,
    patch_rental_request_status,
    reorder_property_images,
    set_property_image_as_cover,
    upload_owner_property_images,
)
from .services import (
    AuthServiceError,
    BackendUnavailableError,
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    clear_auth_session,
    get_property_geocode_preview,
    login_with_backend,
    register_with_backend,
    save_auth_session,
)
from .utils import get_habita_user


def _default_redirect_for_role(user: dict) -> str:
    role = user.get("role")

    if role == "admin":
        return reverse("accounts:admin-area")
    if role == "owner":
        return reverse("accounts:owner-dashboard")
    return reverse("accounts:dashboard")


def login_view(request):
    if request.session.get("habita_logged_in"):
        return redirect("home:home")

    next_url = request.GET.get("next") or request.POST.get("next")
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]

        try:
            auth_data = login_with_backend(email=email, password=password)
            save_auth_session(request, auth_data)

            user_name = auth_data["user"]["full_name"]
            messages.success(request, f"Bienvenido, {user_name}.")
            return redirect(next_url or _default_redirect_for_role(auth_data["user"]))

        except InvalidCredentialsError as exc:
            form.add_error(None, str(exc))
        except InactiveUserError as exc:
            form.add_error(None, str(exc))
        except BackendUnavailableError as exc:
            form.add_error(None, str(exc))
        except AuthServiceError as exc:
            form.add_error(None, str(exc))

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
            "next_url": next_url or reverse("home:home"),
        },
    )


def register_view(request):
    if request.session.get("habita_logged_in"):
        return redirect("home:home")

    form = RegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        payload = {
            "full_name": form.cleaned_data["full_name"],
            "email": form.cleaned_data["email"],
            "phone": form.cleaned_data["phone"],
            "role": form.cleaned_data["role"],
            "password": form.cleaned_data["password"],
        }

        try:
            auth_data = register_with_backend(payload)
            save_auth_session(request, auth_data)

            messages.success(request, "Tu cuenta fue creada correctamente.")
            return redirect(_default_redirect_for_role(auth_data["user"]))

        except EmailAlreadyExistsError as exc:
            form.add_error("email", str(exc))
        except BackendUnavailableError as exc:
            form.add_error(None, str(exc))
        except AuthServiceError as exc:
            form.add_error(None, str(exc))

    return render(
        request,
        "accounts/register.html",
        {
            "form": form,
        },
    )


def logout_view(request):
    if request.session.get("habita_logged_in"):
        clear_auth_session(request)
        messages.info(request, "Tu sesión ha sido cerrada correctamente.")

    return redirect("home:home")


@habita_login_required
def dashboard_view(request):
    habita_user = get_habita_user(request)
    summary = get_dashboard_summary(request, user_id=habita_user["id"])

    return render(
        request,
        "accounts/dashboard.html",
        {
            "habita_user": habita_user,
            **summary,
        },
    )



@habita_role_required("admin")
def admin_area_view(request):
    habita_user = get_habita_user(request)
    dashboard_data, dashboard_error = get_admin_dashboard(request)

    return render(
        request,
        "accounts/admin_area.html",
        {
            "habita_user": habita_user,
            "dashboard_data": dashboard_data,
            "dashboard_error": dashboard_error,
        },
    )
    
### my_activity view
@habita_login_required
def activity_view(request):
    habita_user = get_habita_user(request)

    favorites, favorites_error = get_user_favorites(
        request,
        user_id=habita_user["id"],
        limit=50,
    )

    rental_requests, rental_requests_error = get_user_rental_requests(
        request,
        user_id=habita_user["id"],
        limit=50,
    )

    activity_profile = get_user_activity_profile(
        request=request,
        user_id=habita_user["id"],
        favorites_count=len(favorites),
        requests_count=len(rental_requests),
    )

    return render(
        request,
        "accounts/activity.html",
        {
            "habita_user": habita_user,
            "activity_profile": activity_profile,
            "favorites": favorites,
            "favorites_error": favorites_error,
            "rental_requests": rental_requests,
            "rental_requests_error": rental_requests_error,
        },
    )
    
    
def _safe_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


@habita_role_required("owner", "admin")
def owner_properties_view(request):
    habita_user = get_habita_user(request)
    properties, properties_error = get_owner_properties(request, owner_id=habita_user["id"])

    pending_requests, _pending_error = get_owner_requests_overview(
        request,
        owner_id=habita_user["id"],
        status="pending",
    )

    pending_map = {}
    for rental_request in pending_requests:
        property_id = rental_request.get("property_id")
        if not property_id:
            continue
        pending_map[property_id] = pending_map.get(property_id, 0) + 1

    rented_statuses = {"rented", "occupied", "leased"}

    for property_item in properties:
        property_item["pending_requests_count"] = pending_map.get(property_item["id"], 0)
        property_item["pending_requests_label"] = (
            "1 solicitud pendiente"
            if property_item["pending_requests_count"] == 1
            else f'{property_item["pending_requests_count"]} solicitudes pendientes'
        )

    stats = {
        "total": len(properties),
        "published": sum(1 for property_item in properties if property_item.get("is_published")),
        "available": sum(1 for property_item in properties if property_item.get("status_code") == "available"),
        "pending_requests": len(pending_requests),
        "monthly_income_display": "${:,.0f}/mes".format(
            float(sum(
                _safe_decimal(property_item.get("price_amount"))
                for property_item in properties
                if property_item.get("status_code") in rented_statuses
            ))
        ),
    }

    return render(
        request,
        "accounts/owner_properties.html",
        {
            "habita_user": habita_user,
            "properties": properties,
            "properties_error": properties_error,
            "stats": stats,
        },
    )


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


### ============================
# Formularios para la sección de propietario
### ============================

def _parse_gallery_tokens(raw_value: str) -> list[str]:
    return [token.strip() for token in (raw_value or "").split(",") if token.strip()]


def _token_is_existing(token: str) -> bool:
    return token.startswith("e:") and token[2:].isdigit()


def _token_is_new(token: str) -> bool:
    return token.startswith("n:") and len(token) > 2


def _image_id_from_existing_token(token: str) -> int | None:
    if _token_is_existing(token):
        return int(token.split(":", 1)[1])
    return None


def _apply_property_gallery_changes(
    request,
    property_id: int,
    title: str,
    initial_existing_ids: list[int],
    uploaded_files: list,
) -> list[str]:
    warnings: list[str] = []

    gallery_tokens = _parse_gallery_tokens(request.POST.get("gallery_order", ""))
    cover_token = (request.POST.get("cover_token") or "").strip()

    # Si la portada elegida es una imagen nueva, al subirlas marcamos la primera nueva como cover
    set_new_cover = _token_is_new(cover_token) and bool(uploaded_files)

    if uploaded_files:
        upload_ok, upload_message = upload_owner_property_images(
            request,
            property_id=property_id,
            files=uploaded_files,
            alt_text=title or "",
            set_first_as_cover=set_new_cover,
        )
        if not upload_ok:
            warnings.append(upload_message)

    # Si la portada elegida es una imagen existente, la marcamos explícitamente
    if _token_is_existing(cover_token):
        image_id = _image_id_from_existing_token(cover_token)
        if image_id:
            cover_ok, cover_message = set_property_image_as_cover(
                request,
                image_id=image_id,
            )
            if not cover_ok:
                warnings.append(cover_message)

    # Si no hay orden explícito, terminamos aquí
    if not gallery_tokens:
        return warnings

    current_ids = list(initial_existing_ids)

    # Si se subieron nuevas imágenes, recargamos detalle para obtener sus IDs reales
    if uploaded_files:
        refreshed_detail, refresh_error = get_owner_property_detail(
            request,
            property_id=property_id,
        )
        if refresh_error or not refreshed_detail:
            warnings.append(
                "La propiedad se actualizó, pero no se pudo refrescar la galería para guardar el orden final."
            )
            return warnings

        current_ids = [
            image.get("id")
            for image in refreshed_detail.get("images", [])
            if image.get("id")
        ]

    new_ids = [image_id for image_id in current_ids if image_id not in initial_existing_ids]
    new_tokens_in_order = [token for token in gallery_tokens if _token_is_new(token)]

    # Mapeamos los tokens n:* a los IDs reales recién creados
    new_token_map = {}
    for index, token in enumerate(new_tokens_in_order):
        if index < len(new_ids):
            new_token_map[token] = new_ids[index]

    ordered_image_ids: list[int] = []

    for token in gallery_tokens:
        if _token_is_existing(token):
            image_id = _image_id_from_existing_token(token)
            if image_id and image_id in current_ids and image_id not in ordered_image_ids:
                ordered_image_ids.append(image_id)
        elif token in new_token_map and new_token_map[token] not in ordered_image_ids:
            ordered_image_ids.append(new_token_map[token])

    # Asegura que no se pierda ninguna imagen
    for image_id in current_ids:
        if image_id not in ordered_image_ids:
            ordered_image_ids.append(image_id)

    if len(ordered_image_ids) > 1:
        reorder_ok, reorder_message = reorder_property_images(
            request,
            ordered_image_ids,
        )
        if not reorder_ok:
            warnings.append(reorder_message)

    return warnings

def _build_property_payload(form, is_published_value: bool) -> dict:
    return {
        "title": form.cleaned_data["title"],
        "description": form.cleaned_data["description"],
        "price": str(form.cleaned_data["price"]),
        "property_type": form.cleaned_data["property_type"],
        "status": form.cleaned_data["status"],
        "address_line": form.cleaned_data["address_line"],
        "neighborhood": form.cleaned_data["neighborhood"],
        "city": form.cleaned_data["city"],
        "state": form.cleaned_data["state"],
        "postal_code": form.cleaned_data.get("postal_code") or None,
        "bedrooms": form.cleaned_data["bedrooms"],
        "bathrooms": form.cleaned_data["bathrooms"],
        "parking_spaces": form.cleaned_data["parking_spaces"],
        "area_m2": str(form.cleaned_data["area_m2"]) if form.cleaned_data["area_m2"] is not None else None,
        "is_published": is_published_value,
    }


### helpers para vistas de creación/edición de propiedad del propietario

def _safe_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _get_first_query_value(request, *names: str, default: str = "") -> str:
    for name in names:
        value = (request.GET.get(name) or "").strip()
        if value:
            return value
    return default.strip() if isinstance(default, str) else default


def _normalize_location_preview_params(request) -> dict:
    return {
        "street": _get_first_query_value(request, "street", "address_line"),
        "county": _get_first_query_value(request, "county", "neighborhood"),
        "city": _get_first_query_value(request, "city"),
        "state": _get_first_query_value(request, "state"),
        "postalcode": _get_first_query_value(request, "postalcode", "postal_code"),
        "country": _get_first_query_value(request, "country", default="Mexico") or "Mexico",
    }


def _build_property_form_initial(property_detail: dict) -> dict:
    return {
        "title": property_detail["title"],
        "description": property_detail["description"],
        "price": property_detail["price"],
        "property_type": property_detail["property_type"],
        "status": property_detail["status"],
        "address_line": property_detail["address_line"],
        "neighborhood": property_detail["neighborhood"],
        "city": property_detail["city"],
        "state": property_detail["state"],
        "postal_code": property_detail.get("postal_code"),
        "bedrooms": property_detail["bedrooms"],
        "bathrooms": property_detail["bathrooms"],
        "parking_spaces": property_detail["parking_spaces"],
        "area_m2": property_detail["area_m2"],
        "latitude": property_detail.get("latitude"),
        "longitude": property_detail.get("longitude"),
        "is_published": property_detail["is_published"],
    }


def _build_property_payload(form, is_published_value: bool) -> dict:
    latitude = form.cleaned_data.get("latitude")
    longitude = form.cleaned_data.get("longitude")

    return {
        "title": form.cleaned_data["title"],
        "description": form.cleaned_data["description"],
        "price": str(form.cleaned_data["price"]),
        "property_type": form.cleaned_data["property_type"],
        "status": form.cleaned_data["status"],
        "address_line": form.cleaned_data["address_line"],
        "neighborhood": form.cleaned_data["neighborhood"],
        "city": form.cleaned_data["city"],
        "state": form.cleaned_data["state"],
        "postal_code": form.cleaned_data.get("postal_code") or None,
        "bedrooms": form.cleaned_data["bedrooms"],
        "bathrooms": form.cleaned_data["bathrooms"],
        "parking_spaces": form.cleaned_data["parking_spaces"],
        "area_m2": str(form.cleaned_data["area_m2"]) if form.cleaned_data["area_m2"] is not None else None,
        "latitude": str(latitude) if latitude is not None else None,
        "longitude": str(longitude) if longitude is not None else None,
        "is_published": is_published_value,
    }

@habita_role_required("owner", "admin")
def owner_property_create_view(request):
    habita_user = get_habita_user(request)
    form = OwnerPropertyForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        submit_mode = request.POST.get("submit_mode", "save")
        is_published_value = form.cleaned_data["is_published"]

        if submit_mode == "publish":
            is_published_value = True
        elif submit_mode == "draft":
            is_published_value = False

        payload = _build_property_payload(form, is_published_value)

        created_property, error = create_owner_property(
            request,
            owner_id=habita_user["id"],
            payload=payload,
        )

        if error or not created_property:
            messages.error(request, error or "No fue posible crear la propiedad.")
            return render(
                request,
                "accounts/owner_property_form.html",
                {
                    "form": form,
                    "mode": "create",
                    "property_obj": None,
                },
            )

        uploaded_files = list(form.cleaned_data.get("images") or [])
        warnings = _apply_property_gallery_changes(
            request=request,
            property_id=created_property["id"],
            title=created_property.get("title", ""),
            initial_existing_ids=[],
            uploaded_files=uploaded_files,
        )

        messages.success(request, "Propiedad creada correctamente.")
        for warning in warnings:
            messages.warning(request, warning)

        return redirect("accounts:owner-properties")

    return render(
        request,
        "accounts/owner_property_form.html",
        {
            "form": form,
            "mode": "create",
            "property_obj": None,
        },
    )

@habita_role_required("owner", "admin")
def owner_property_edit_view(request, property_id: int):
    habita_user = get_habita_user(request)

    properties, _ = get_owner_properties(request, owner_id=habita_user["id"])
    owned_property = next((item for item in properties if item["id"] == property_id), None)
    if not owned_property:
        messages.error(request, "No tienes acceso a esa propiedad.")
        return redirect("accounts:owner-properties")

    property_detail, error = get_owner_property_detail(request, property_id=property_id)
    if error or not property_detail:
        messages.error(request, error or "No fue posible cargar la propiedad.")
        return redirect("accounts:owner-properties")

    initial = _build_property_form_initial(property_detail)
    existing_image_ids = [image.get("id") for image in property_detail.get("images", []) if image.get("id")]

    form = OwnerPropertyForm(request.POST or None, request.FILES or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        submit_mode = request.POST.get("submit_mode", "save")
        is_published_value = form.cleaned_data["is_published"]

        if submit_mode == "publish":
            is_published_value = True
        elif submit_mode == "draft":
            is_published_value = False

        payload = _build_property_payload(form, is_published_value)

        updated_property, patch_error = patch_owner_property(
            request,
            property_id=property_id,
            payload=payload,
        )

        if patch_error or not updated_property:
            messages.error(request, patch_error or "No fue posible actualizar la propiedad.")
            return render(
                request,
                "accounts/owner_property_form.html",
                {
                    "form": form,
                    "mode": "edit",
                    "property_obj": property_detail,
                },
            )

        uploaded_files = list(form.cleaned_data.get("images") or [])
        warnings = _apply_property_gallery_changes(
            request=request,
            property_id=property_id,
            title=updated_property.get("title", property_detail.get("title", "")),
            initial_existing_ids=existing_image_ids,
            uploaded_files=uploaded_files,
        )

        messages.success(request, "Propiedad actualizada correctamente.")
        for warning in warnings:
            messages.warning(request, warning)

        return redirect("accounts:owner-properties")

    return render(
        request,
        "accounts/owner_property_form.html",
        {
            "form": form,
            "mode": "edit",
            "property_obj": property_detail,
        },
    )


@habita_role_required("admin")
def admin_property_edit_view(request, property_id: int):
    property_detail, error = get_owner_property_detail(request, property_id=property_id)
    if error or not property_detail:
        messages.error(request, error or "No fue posible cargar la propiedad.")
        return redirect("accounts:admin-area")

    initial = _build_property_form_initial(property_detail)
    existing_image_ids = [image.get("id") for image in property_detail.get("images", []) if image.get("id")]

    form = OwnerPropertyForm(request.POST or None, request.FILES or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        submit_mode = request.POST.get("submit_mode", "save")
        is_published_value = form.cleaned_data["is_published"]

        if submit_mode == "publish":
            is_published_value = True
        elif submit_mode == "draft":
            is_published_value = False

        payload = _build_property_payload(form, is_published_value)

        updated_property, patch_error = patch_owner_property(
            request,
            property_id=property_id,
            payload=payload,
        )

        if patch_error or not updated_property:
            messages.error(request, patch_error or "No fue posible actualizar la propiedad.")
            return render(
                request,
                "accounts/owner_property_form.html",
                {
                    "form": form,
                    "mode": "edit",
                    "property_obj": property_detail,
                    "admin_mode": True,
                },
            )

        uploaded_files = list(form.cleaned_data.get("images") or [])
        warnings = _apply_property_gallery_changes(
            request=request,
            property_id=property_id,
            title=updated_property.get("title", property_detail.get("title", "")),
            initial_existing_ids=existing_image_ids,
            uploaded_files=uploaded_files,
        )

        messages.success(request, "Propiedad actualizada correctamente.")
        for warning in warnings:
            messages.warning(request, warning)

        return redirect("accounts:admin-area")

    return render(
        request,
        "accounts/owner_property_form.html",
        {
            "form": form,
            "mode": "edit",
            "property_obj": property_detail,
            "admin_mode": True,
        },
    )

@require_POST
@habita_role_required("admin")
def admin_property_delete_view(request, property_id: int):
    success, message = delete_property_by_id(request, property_id=property_id)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("accounts:admin-area")


@require_POST
@habita_role_required("owner", "admin")
def owner_set_cover_image_view(request, property_id: int, image_id: int):
    success, message = set_property_image_as_cover(request, image_id=image_id)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("accounts:owner-property-edit", property_id=property_id)


@require_POST
@habita_role_required("owner", "admin")
def owner_delete_property_image_view(request, property_id: int, image_id: int):
    success, message = delete_property_image_by_id(request, image_id=image_id)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("accounts:owner-property-edit", property_id=property_id)


@require_POST
@habita_role_required("admin")
def admin_set_cover_image_view(request, property_id: int, image_id: int):
    success, message = set_property_image_as_cover(request, image_id=image_id)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("accounts:admin-property-edit", property_id=property_id)


@require_POST
@habita_role_required("admin")
def admin_delete_property_image_view(request, property_id: int, image_id: int):
    success, message = delete_property_image_by_id(request, image_id=image_id)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("accounts:admin-property-edit", property_id=property_id)


@habita_role_required("owner", "admin")
def owner_requests_view(request):
    habita_user = get_habita_user(request)
    status_filter = request.GET.get("status", "").strip() or ""
    property_filter = request.GET.get("property_id", "").strip() or ""

    selected_property_id = None
    if property_filter.isdigit():
        selected_property_id = int(property_filter)

    owner_properties, properties_error = get_owner_properties(
        request,
        owner_id=habita_user["id"],
        limit=100,
    )

    all_requests, rental_requests_error = get_owner_requests_overview(
        request,
        owner_id=habita_user["id"],
        status=None,
    )

    rental_requests = all_requests

    if selected_property_id is not None:
        rental_requests = [
            item for item in rental_requests
            if item.get("property_id") == selected_property_id
        ]

    if status_filter:
        rental_requests = [
            item for item in rental_requests
            if item.get("status_code") == status_filter
        ]

    request_summary = build_owner_requests_summary(rental_requests)

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
    
    
    
from django.conf import settings
from django.http import JsonResponse
import requests

from accounts.decorators import habita_role_required


@require_GET
@habita_role_required("owner", "admin")
def owner_property_location_preview_view(request):
    params = _normalize_location_preview_params(request)

    if not params["city"] or not params["state"]:
        return JsonResponse(
            {
                "success": False,
                "error": "Captura al menos ciudad y estado.",
            },
            status=400,
        )

    if not params["street"] and not params["county"] and not params["postalcode"]:
        return JsonResponse(
            {
                "success": False,
                "error": "Captura al menos calle, colonia o código postal.",
            },
            status=400,
        )

    data, error = get_property_geocode_preview(
        street=params["street"],
        county=params["county"],
        city=params["city"],
        state=params["state"],
        postalcode=params["postalcode"],
        country=params["country"],
    )

    if error:
        return JsonResponse(
            {
                "success": False,
                "error": error,
            },
            status=502,
        )

    if not data:
        return JsonResponse(
            {
                "success": False,
                "error": "No se pudo ubicar la dirección.",
            },
            status=404,
        )

    return JsonResponse(
        {
            "success": True,
            "data": data,
        }
    )
    
    
#######################################
##    OWNER PORTAL - PROPERTY CREATION/EDITING
##
##################################

@habita_role_required("owner", "admin")
def owner_reviews_view(request):
    habita_user = get_habita_user(request)
    return render(
        request,
        "accounts/owner/reviews_placeholder.html",
        {"habita_user": habita_user},
    )


@habita_role_required("owner", "admin")
def owner_reports_view(request):
    habita_user = get_habita_user(request)
    return render(
        request,
        "accounts/owner/reports_placeholder.html",
        {"habita_user": habita_user},
    )


@habita_role_required("owner", "admin")
def owner_dashboard_view(request):
    habita_user = get_habita_user(request)

    properties, _properties_error = get_owner_properties(request, owner_id=habita_user["id"])
    pending_requests, _pending_error = get_owner_requests_overview(
        request,
        owner_id=habita_user["id"],
        status="pending",
    )

    dashboard_stats = {
        "total_properties": len(properties),
        "published_properties": sum(1 for item in properties if item.get("is_published")),
        "pending_requests": len(pending_requests),
    }

    return render(
        request,
        "accounts/owner/dashboard.html",
        {
            "habita_user": habita_user,
            "dashboard_stats": dashboard_stats,
        },
    )