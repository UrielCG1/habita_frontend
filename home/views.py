from django.shortcuts import render

from .services import get_featured_properties


def home_view(request):
    featured_properties, featured_properties_error = get_featured_properties(limit=3)

    context = {
        "featured_properties": featured_properties,
        "featured_properties_error": featured_properties_error,
        "zones": [
            "Juriquilla",
            "El Campanario",
            "Milénio III",
            "Centro Sur",
            "Zibatá",
            "Corregidora",
            "Refugio",
            "Centro",
        ],
    }
    return render(request, "home/home.html", context)