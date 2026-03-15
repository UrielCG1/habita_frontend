from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from .decorators import habita_login_required
from .forms import LoginForm
from .services import (
    AuthServiceError,
    BackendUnavailableError,
    InactiveUserError,
    InvalidCredentialsError,
    clear_auth_session,
    login_with_backend,
    save_auth_session,
)
from .utils import get_habita_user


def login_view(request):
    if request.session.get("habita_logged_in"):
        return redirect("home:home")

    next_url = request.GET.get("next") or request.POST.get("next") or reverse("home:home")
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]

        try:
            auth_data = login_with_backend(email=email, password=password)
            save_auth_session(request, auth_data)

            user_name = auth_data["user"]["full_name"]
            messages.success(request, f"Bienvenido, {user_name}.")
            return redirect(next_url)

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
            "next_url": next_url,
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