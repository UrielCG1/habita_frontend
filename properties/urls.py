from django.urls import path
from . import views

app_name = "properties"

urlpatterns = [
    path("", views.property_list_view, name="list"),
    path("<int:property_id>/", views.property_detail_view, name="detail"),
]
