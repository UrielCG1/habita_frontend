from django.urls import path

from .views import (
    admin_area_view,
    dashboard_view,
    favorites_view,
    login_view,
    logout_view,
    my_requests_view,
    owner_area_view,
    owner_properties_view,
    owner_property_requests_view,
    owner_update_request_status_view,
    register_view,
    owner_property_create_view,
    owner_property_edit_view,
    admin_property_delete_view,
    admin_property_edit_view,
)

app_name = "accounts"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("favorites/", favorites_view, name="favorites"),
    path("my-requests/", my_requests_view, name="my-requests"),
    path("owner-area/", owner_area_view, name="owner-area"),
    path("admin-area/", admin_area_view, name="admin-area"),
    
    path("owner-properties/", owner_properties_view, name="owner-properties"),
    path("owner-properties/<int:property_id>/requests/", owner_property_requests_view, name="owner-property-requests"),
    path("owner-properties/<int:property_id>/requests/<int:request_id>/update/", owner_update_request_status_view, name="owner-update-request-status"),
    
    path("owner-properties/create/", owner_property_create_view, name="owner-property-create"),
    path("owner-properties/<int:property_id>/edit/", owner_property_edit_view, name="owner-property-edit"),
    
    path("admin/properties/<int:property_id>/edit/", admin_property_edit_view, name="admin-property-edit"),
    path("admin/properties/<int:property_id>/delete/", admin_property_delete_view, name="admin-property-delete"),
]