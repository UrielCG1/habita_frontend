from math import ceil

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import habita_login_required
from accounts.dashboard_services import create_rental_request
from accounts.utils import get_habita_user, is_habita_authenticated
from .forms import RentalRequestForm, ReviewForm
from .services import (
    add_favorite,
    build_query_string,
    delete_review,
    get_favorite_status,
    get_properties_list,
    get_property_detail,
    get_property_reviews,
    get_user_favorite_ids,
    get_user_review_for_property,
    remove_favorite,
    save_review,
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


from datetime import datetime

SPANISH_MONTHS = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def property_detail_view(request, property_id: int):
    property_data, error = get_property_detail(property_id)

    if error:
        messages.error(request, error)
        return redirect("properties:list")

    is_favorite = False
    user_review = None
    review_form = ReviewForm()
    reviews, reviews_summary, reviews_error = get_property_reviews(property_id)

    reviews_summary = reviews_summary or {"count": 0, "average": 0}
    average = float(reviews_summary.get("average") or 0)
    reviews_summary["average"] = round(average, 1)
    reviews_summary["average_percent"] = round((average / 5) * 100, 2)

    normalized_reviews = []
    for review in reviews or []:
        item = dict(review)
        user_name = (item.get("user_name") or "Usuario").strip()
        parts = [part for part in user_name.split() if part]
        item["user_initials"] = "".join(part[0].upper() for part in parts[:2]) or "U"

        created_at = item.get("created_at")
        item["display_date"] = "Fecha no disponible"

        if created_at:
            try:
                dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                item["display_date"] = f"{SPANISH_MONTHS[dt.month]} {dt.year}"
            except ValueError:
                item["display_date"] = str(created_at)[:10]

        normalized_reviews.append(item)

    reviews = normalized_reviews

    if is_habita_authenticated(request):
        habita_user = get_habita_user(request)
        is_favorite = get_favorite_status(request, habita_user["id"], property_id)
        user_review = get_user_review_for_property(request, habita_user["id"], property_id)

        if user_review:
            review_form = ReviewForm(
                initial={
                    "rating": str(user_review["rating"]),
                    "comment": user_review["comment"],
                }
            )

    return render(
        request,
        "properties/detail.html",
        {
            "property": property_data,
            "is_favorite": is_favorite,
            "rental_request_form": RentalRequestForm(),
            "reviews": reviews,
            "reviews_summary": reviews_summary,
            "reviews_error": reviews_error,
            "review_form": review_form,
            "user_review": user_review,
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


@require_POST
@habita_login_required
def submit_rental_request_view(request, property_id: int):
    habita_user = get_habita_user(request)
    form = RentalRequestForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Revisa los datos de la solicitud.")
        return redirect("properties:detail", property_id=property_id)

    success, message = create_rental_request(
        request=request,
        user_id=habita_user["id"],
        property_id=property_id,
        message=form.cleaned_data.get("message"),
        move_in_date=form.cleaned_data.get("move_in_date").isoformat() if form.cleaned_data.get("move_in_date") else None,
        monthly_budget=str(form.cleaned_data.get("monthly_budget")) if form.cleaned_data.get("monthly_budget") else None,
    )

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("properties:detail", property_id=property_id)


@require_POST
@habita_login_required
def submit_review_view(request, property_id: int):
    habita_user = get_habita_user(request)
    form = ReviewForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Revisa los datos de tu reseña.")
        return redirect("properties:detail", property_id=property_id)

    user_review = get_user_review_for_property(request, habita_user["id"], property_id)

    success, message = save_review(
        request=request,
        user_id=habita_user["id"],
        property_id=property_id,
        rating=int(form.cleaned_data["rating"]),
        comment=form.cleaned_data.get("comment") or "",
        review_id=user_review["id"] if user_review else None,
    )

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("properties:detail", property_id=property_id)


@require_POST
@habita_login_required
def delete_review_view(request, property_id: int):
    habita_user = get_habita_user(request)
    user_review = get_user_review_for_property(request, habita_user["id"], property_id)

    if not user_review:
        messages.error(request, "No se encontró una reseña tuya para esta propiedad.")
        return redirect("properties:detail", property_id=property_id)

    success, message = delete_review(request, review_id=user_review["id"])

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("properties:detail", property_id=property_id)