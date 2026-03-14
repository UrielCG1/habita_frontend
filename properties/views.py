from math import ceil
from django.shortcuts import render
from .services import get_properties, get_property_detail


def property_list_view(request):
    limit = 9

    try:
        page = int(request.GET.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    skip = (page - 1) * limit

    filters = {
        "q": request.GET.get("q", "").strip(),
        "city": request.GET.get("city", "").strip(),
        "property_type": request.GET.get("property_type", "").strip(),
        "min_price": request.GET.get("min_price", "").strip(),
        "max_price": request.GET.get("max_price", "").strip(),
        "bedrooms": request.GET.get("bedrooms", "").strip(),
        "bathrooms": request.GET.get("bathrooms", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "skip": skip,
        "limit": limit,
    }

    result = get_properties(filters=filters)

    pagination = result.get("pagination") or {}
    total = pagination.get("total", 0)
    total_pages = ceil(total / limit) if total and limit else 1

    context = {
        "properties": result.get("items", []),
        "error_message": result.get("error_message"),
        "filters": {
            "q": filters["q"],
            "city": filters["city"],
            "property_type": filters["property_type"],
            "min_price": filters["min_price"],
            "max_price": filters["max_price"],
            "bedrooms": filters["bedrooms"],
            "bathrooms": filters["bathrooms"],
            "status": filters["status"],
        },
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "has_previous": page > 1,
            "has_next": page < total_pages,
            "previous_page": page - 1,
            "next_page": page + 1,
        },
    }

    return render(request, "properties/list.html", context)


def property_detail_view(request, property_id):
    result = get_property_detail(property_id)

    context = {
        "property": result.get("item"),
        "error_message": result.get("error_message"),
    }

    return render(request, "properties/detail.html", context)
