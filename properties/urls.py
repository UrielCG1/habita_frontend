from django.urls import path

from .views import (
    delete_review_view,
    properties_list_view,
    property_detail_view,
    submit_rental_request_view,
    submit_review_view,
    toggle_favorite_view,
    property_image_proxy
)

app_name = "properties"

urlpatterns = [
    path("", properties_list_view, name="list"),
    path("<int:property_id>/", property_detail_view, name="detail"),
    path("<int:property_id>/favorite/", toggle_favorite_view, name="toggle-favorite"),
    path("<int:property_id>/request/", submit_rental_request_view, name="submit-request"),
    path("<int:property_id>/review/", submit_review_view, name="submit-review"),
    path("<int:property_id>/review/delete/", delete_review_view, name="delete-review"),
    
    path("images/<int:image_id>/", property_image_proxy, name="property_image_proxy"),
]