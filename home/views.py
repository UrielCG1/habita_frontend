from django.shortcuts import render

from .services import get_featured_properties


def home_view(request):
    featured_properties, featured_properties_error = get_featured_properties(limit=6)

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
            "El Refugio",
            "Centro",
        ],
        "home_metrics": [
            {"value": "+120", "label": "propiedades activas"},
            {"value": "24 h", "label": "respuesta promedio"},
            {"value": "100%", "label": "publicaciones revisadas"},
        ],
    }
    return render(request, "home/home.html", context)
