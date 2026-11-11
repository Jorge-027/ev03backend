from django.urls import path

from . import views

app_name = "carrito"

urlpatterns = [
    path("", views.cart_detail, name="detalle"),
    path("agregar/<int:manga_id>/", views.cart_add, name="agregar"),
    path("actualizar/<int:manga_id>/", views.cart_update, name="actualizar"),
    path("quitar/<int:manga_id>/", views.cart_remove, name="quitar"),
    path("vaciar/", views.cart_clear, name="vaciar"),
    path("solicitar/", views.cart_checkout, name="solicitar"),
    path("boleta/", views.cart_receipt, name="boleta"),
]
