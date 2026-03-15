from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from .utils import get_habita_user, is_habita_authenticated


def habita_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if is_habita_authenticated(request):
            return view_func(request, *args, **kwargs)

        login_url = reverse("accounts:login")
        next_url = request.get_full_path()
        query_string = urlencode({"next": next_url})
        return redirect(f"{login_url}?{query_string}")

    return _wrapped_view


def habita_role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not is_habita_authenticated(request):
                login_url = reverse("accounts:login")
                next_url = request.get_full_path()
                query_string = urlencode({"next": next_url})
                return redirect(f"{login_url}?{query_string}")

            user = get_habita_user(request)
            role = (user or {}).get("role")

            if role not in allowed_roles:
                messages.error(request, "No tienes permisos para acceder a esta sección.")
                return redirect("home:home")

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator