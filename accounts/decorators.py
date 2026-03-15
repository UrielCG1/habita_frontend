from functools import wraps
from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse

from .utils import is_habita_authenticated


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