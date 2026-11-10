from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="detail"),
    path("agregar/<int:manga_id>/", views.cart_add, name="add"),
    path("actualizar/<int:manga_id>/", views.cart_update, name="update"),
    path("quitar/<int:manga_id>/", views.cart_remove, name="remove"),
    path("vaciar/", views.cart_clear, name="clear"),
]
