from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("manga/<slug:slug>/", views.manga_detail, name="manga_detail"),
]
