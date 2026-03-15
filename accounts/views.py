from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from .decorators import habita_login_required, habita_role_required
from .forms import LoginForm, RegisterForm
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
    return reverse("home:home")


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
    return render(
        request,
        "accounts/dashboard.html",
        {
            "habita_user": get_habita_user(request),
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
    return render(
        request,
        "accounts/admin_area.html",
        {
            "habita_user": get_habita_user(request),
        },
    )