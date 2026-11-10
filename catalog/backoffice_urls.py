from django.urls import path

from . import views

app_name = "backoffice"

urlpatterns = [
    path("", views.backoffice_dashboard, name="dashboard"),
    path("mangas/", views.backoffice_mangas, name="mangas"),
    path("mangas/nuevo/", views.manga_create, name="manga_create"),
    path("mangas/<int:pk>/editar/", views.manga_edit, name="manga_edit"),
    path("mangas/<int:pk>/desactivar/", views.manga_deactivate, name="manga_deactivate"),
    path("generos/", views.backoffice_genres, name="genres"),
    path("generos/nuevo/", views.genre_create, name="genre_create"),
    path("generos/<int:pk>/editar/", views.genre_edit, name="genre_edit"),
    path("generos/<int:pk>/eliminar/", views.genre_delete, name="genre_delete"),
]
