from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .dashboard_services import get_dashboard_summary, get_user_favorites, get_user_rental_requests, get_user_rental_requests, get_user_activity_profile
from .decorators import habita_login_required, habita_role_required
from .forms import LoginForm, RegisterForm, OwnerRequestStatusForm, OwnerPropertyForm
from .admin_services import get_admin_dashboard
from .owner_services import (
    create_owner_property,
    get_owner_properties,
    get_owner_property_detail,
    get_property_rental_requests,
    patch_owner_property,
    patch_rental_request_status,
    upload_owner_property_images,
    delete_property_by_id,
)
from .services import (
    AuthServiceError,
    BackendUnavailableError,
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    clear_auth_session,
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
        return reverse("accounts:owner-area")
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


@habita_role_required("owner", "admin")
def owner_area_view(request):
    return render(
        request,
        "accounts/owner_area.html",
        {
            "habita_user": get_habita_user(request),
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
    
    
@habita_role_required("owner", "admin")
def owner_properties_view(request):
    habita_user = get_habita_user(request)
    properties, properties_error = get_owner_properties(request, owner_id=habita_user["id"])

    return render(
        request,
        "accounts/owner_properties.html",
        {
            "habita_user": habita_user,
            "properties": properties,
            "properties_error": properties_error,
        },
    )


@habita_role_required("owner", "admin")
def owner_property_requests_view(request, property_id: int):
    habita_user = get_habita_user(request)
    status_filter = request.GET.get("status", "").strip() or None

    properties, _ = get_owner_properties(request, owner_id=habita_user["id"])
    owned_property = next((item for item in properties if item["id"] == property_id), None)

    if not owned_property:
        messages.error(request, "No tienes acceso a esa propiedad.")
        return redirect("accounts:owner-properties")

    rental_requests, rental_requests_error = get_property_rental_requests(
        request,
        property_id=property_id,
        status=status_filter,
    )

    return render(
        request,
        "accounts/owner_property_requests.html",
        {
            "habita_user": habita_user,
            "owned_property": owned_property,
            "rental_requests": rental_requests,
            "rental_requests_error": rental_requests_error,
            "status_filter": status_filter or "",
            "status_form": OwnerRequestStatusForm(),
        },
    )


@require_POST
@habita_role_required("owner", "admin")
def owner_update_request_status_view(request, property_id: int, request_id: int):
    form = OwnerRequestStatusForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Revisa los datos del cambio de estado.")
        return redirect("accounts:owner-property-requests", property_id=property_id)

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

    return redirect("accounts:owner-property-requests", property_id=property_id)




### ============================
# Formularios para la sección de propietario
### ============================


@habita_role_required("owner", "admin")
def owner_property_create_view(request):
    habita_user = get_habita_user(request)
    form = OwnerPropertyForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        payload = {
            "title": form.cleaned_data["title"],
            "description": form.cleaned_data["description"],
            "price": str(form.cleaned_data["price"]),
            "property_type": form.cleaned_data["property_type"],
            "status": form.cleaned_data["status"],
            "address_line": form.cleaned_data["address_line"],
            "neighborhood": form.cleaned_data["neighborhood"],
            "city": form.cleaned_data["city"],
            "state": form.cleaned_data["state"],
            "bedrooms": form.cleaned_data["bedrooms"],
            "bathrooms": form.cleaned_data["bathrooms"],
            "parking_spaces": form.cleaned_data["parking_spaces"],
            "area_m2": str(form.cleaned_data["area_m2"]) if form.cleaned_data["area_m2"] is not None else None,
            "latitude": str(form.cleaned_data["latitude"]) if form.cleaned_data["latitude"] is not None else None,
            "longitude": str(form.cleaned_data["longitude"]) if form.cleaned_data["longitude"] is not None else None,
            "is_published": form.cleaned_data["is_published"],
        }

        created_property, error = create_owner_property(request, owner_id=habita_user["id"], payload=payload)

        if error or not created_property:
            messages.error(request, error or "No fue posible crear la propiedad.")
            return render(
                request,
                "accounts/owner_property_form.html",
                {
                    "form": form,
                    "mode": "create",
                },
            )

        uploaded_files = form.cleaned_data.get("images") or []
        upload_ok, upload_message = upload_owner_property_images(
            request,
            property_id=created_property["id"],
            files=uploaded_files,
            alt_text=created_property.get("title", ""),
            set_first_as_cover=True,
        )

        if upload_ok:
            messages.success(request, "Propiedad creada correctamente.")
        else:
            messages.warning(request, upload_message)

        return redirect("accounts:owner-properties")

    return render(
        request,
        "accounts/owner_property_form.html",
        {
            "form": form,
            "mode": "create",
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

    initial = {
        "title": property_detail["title"],
        "description": property_detail["description"],
        "price": property_detail["price"],
        "property_type": property_detail["property_type"],
        "status": property_detail["status"],
        "address_line": property_detail["address_line"],
        "neighborhood": property_detail["neighborhood"],
        "city": property_detail["city"],
        "state": property_detail["state"],
        "bedrooms": property_detail["bedrooms"],
        "bathrooms": property_detail["bathrooms"],
        "parking_spaces": property_detail["parking_spaces"],
        "area_m2": property_detail["area_m2"],
        "latitude": property_detail["latitude"],
        "longitude": property_detail["longitude"],
        "is_published": property_detail["is_published"],
    }

    form = OwnerPropertyForm(request.POST or None, request.FILES or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        payload = {
            "title": form.cleaned_data["title"],
            "description": form.cleaned_data["description"],
            "price": str(form.cleaned_data["price"]),
            "property_type": form.cleaned_data["property_type"],
            "status": form.cleaned_data["status"],
            "address_line": form.cleaned_data["address_line"],
            "neighborhood": form.cleaned_data["neighborhood"],
            "city": form.cleaned_data["city"],
            "state": form.cleaned_data["state"],
            "bedrooms": form.cleaned_data["bedrooms"],
            "bathrooms": form.cleaned_data["bathrooms"],
            "parking_spaces": form.cleaned_data["parking_spaces"],
            "area_m2": str(form.cleaned_data["area_m2"]) if form.cleaned_data["area_m2"] is not None else None,
            "latitude": str(form.cleaned_data["latitude"]) if form.cleaned_data["latitude"] is not None else None,
            "longitude": str(form.cleaned_data["longitude"]) if form.cleaned_data["longitude"] is not None else None,
            "is_published": form.cleaned_data["is_published"],
        }

        updated_property, patch_error = patch_owner_property(request, property_id=property_id, payload=payload)

        if patch_error or not updated_property:
            messages.error(request, patch_error or "No fue posible actualizar la propiedad.")
        else:
            uploaded_files = form.cleaned_data.get("images") or []
            if uploaded_files:
                upload_ok, upload_message = upload_owner_property_images(
                    request,
                    property_id=property_id,
                    files=uploaded_files,
                    alt_text=updated_property.get("title", ""),
                    set_first_as_cover=False,
                )
                if not upload_ok:
                    messages.warning(request, upload_message)

            messages.success(request, "Propiedad actualizada correctamente.")
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
    
    
#### PANEL DE ADMINISTRACIÓN

@habita_role_required("admin")
def admin_property_edit_view(request, property_id: int):
    property_detail, error = get_owner_property_detail(request, property_id=property_id)

    if error or not property_detail:
        messages.error(request, error or "No fue posible cargar la propiedad.")
        return redirect("accounts:admin-area")

    initial = {
        "title": property_detail["title"],
        "description": property_detail["description"],
        "price": property_detail["price"],
        "property_type": property_detail["property_type"],
        "status": property_detail["status"],
        "address_line": property_detail["address_line"],
        "neighborhood": property_detail["neighborhood"],
        "city": property_detail["city"],
        "state": property_detail["state"],
        "bedrooms": property_detail["bedrooms"],
        "bathrooms": property_detail["bathrooms"],
        "parking_spaces": property_detail["parking_spaces"],
        "area_m2": property_detail["area_m2"],
        "latitude": property_detail["latitude"],
        "longitude": property_detail["longitude"],
        "is_published": property_detail["is_published"],
    }

    form = OwnerPropertyForm(request.POST or None, request.FILES or None, initial=initial)

    if request.method == "POST" and form.is_valid():
        payload = {
            "title": form.cleaned_data["title"],
            "description": form.cleaned_data["description"],
            "price": str(form.cleaned_data["price"]),
            "property_type": form.cleaned_data["property_type"],
            "status": form.cleaned_data["status"],
            "address_line": form.cleaned_data["address_line"],
            "neighborhood": form.cleaned_data["neighborhood"],
            "city": form.cleaned_data["city"],
            "state": form.cleaned_data["state"],
            "bedrooms": form.cleaned_data["bedrooms"],
            "bathrooms": form.cleaned_data["bathrooms"],
            "parking_spaces": form.cleaned_data["parking_spaces"],
            "area_m2": str(form.cleaned_data["area_m2"]) if form.cleaned_data["area_m2"] is not None else None,
            "latitude": str(form.cleaned_data["latitude"]) if form.cleaned_data["latitude"] is not None else None,
            "longitude": str(form.cleaned_data["longitude"]) if form.cleaned_data["longitude"] is not None else None,
            "is_published": form.cleaned_data["is_published"],
        }

        updated_property, patch_error = patch_owner_property(request, property_id=property_id, payload=payload)

        if patch_error or not updated_property:
            messages.error(request, patch_error or "No fue posible actualizar la propiedad.")
        else:
            uploaded_files = form.cleaned_data.get("images") or []
            if uploaded_files:
                upload_ok, upload_message = upload_owner_property_images(
                    request,
                    property_id=property_id,
                    files=uploaded_files,
                    alt_text=updated_property.get("title", ""),
                    set_first_as_cover=False,
                )
                if not upload_ok:
                    messages.warning(request, upload_message)

            messages.success(request, "Propiedad actualizada correctamente.")
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