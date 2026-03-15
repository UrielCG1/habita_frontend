from django.urls import path

from .views import properties_list_view, property_detail_view, toggle_favorite_view

app_name = "properties"

urlpatterns = [
    path("", properties_list_view, name="list"),
    path("<int:property_id>/", property_detail_view, name="detail"),
    path("<int:property_id>/favorite/", toggle_favorite_view, name="toggle-favorite"),
]