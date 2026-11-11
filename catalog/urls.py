from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.catalog, name="catalogo"),
    path("detalle_manga/<str:slug>/", views.manga_detail, name="detalle_manga"),
]
