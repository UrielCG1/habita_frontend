from math import ceil

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import habita_login_required
from accounts.utils import get_habita_user, is_habita_authenticated
from .services import (
    add_favorite,
    build_query_string,
    get_favorite_status,
    get_properties_list,
    get_property_detail,
    get_user_favorite_ids,
    remove_favorite,
)


def properties_list_view(request):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "city": request.GET.get("city", "").strip(),
        "state": request.GET.get("state", "").strip(),
        "property_type": request.GET.get("property_type", "").strip(),
        "status": request.GET.get("status", "available").strip(),
        "min_price": request.GET.get("min_price", "").strip(),
        "max_price": request.GET.get("max_price", "").strip(),
        "bedrooms": request.GET.get("bedrooms", "").strip(),
        "bathrooms": request.GET.get("bathrooms", "").strip(),
        "is_published": "true",
    }

    page = request.GET.get("page", "1")
    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1

    items, pagination, error = get_properties_list(filters=filters, page=page, limit=9)

    favorite_ids = set()
    if is_habita_authenticated(request):
        habita_user = get_habita_user(request)
        favorite_ids = get_user_favorite_ids(request, habita_user["id"])

    for item in items:
        item["is_favorite"] = item["id"] in favorite_ids

    total = pagination.get("total", 0)
    limit = pagination.get("limit", 9)
    total_pages = ceil(total / limit) if limit else 1

    query_filters = dict(filters)
    query_filters.pop("is_published", None)
    query_string = build_query_string(query_filters)

    return render(
        request,
        "properties/list.html",
        {
            "properties": items,
            "properties_error": error,
            "filters": filters,
            "pagination": pagination,
            "current_page": page,
            "total_pages": total_pages,
            "query_string": query_string,
        },
    )


def property_detail_view(request, property_id: int):
    property_data, error = get_property_detail(property_id)

    if error:
        messages.error(request, error)
        return redirect("properties:list")

    is_favorite = False
    if is_habita_authenticated(request):
        habita_user = get_habita_user(request)
        is_favorite = get_favorite_status(request, habita_user["id"], property_id)

    return render(
        request,
        "properties/detail.html",
        {
            "property": property_data,
            "is_favorite": is_favorite,
        },
    )


@require_POST
@habita_login_required
def toggle_favorite_view(request, property_id: int):
    habita_user = get_habita_user(request)
    action = request.POST.get("action")
    next_url = request.POST.get("next") or reverse("properties:detail", args=[property_id])

    if action == "add":
        success, message = add_favorite(request, habita_user["id"], property_id)
    else:
        success, message = remove_favorite(request, habita_user["id"], property_id)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect(next_url)