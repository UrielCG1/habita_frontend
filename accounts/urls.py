from django.urls import path

from .views import (
    admin_area_view,
    dashboard_view,
    favorites_view,
    login_view,
    logout_view,
    owner_area_view,
    register_view,
)

app_name = "accounts"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("favorites/", favorites_view, name="favorites"),
    path("owner-area/", owner_area_view, name="owner-area"),
    path("admin-area/", admin_area_view, name="admin-area"),
]