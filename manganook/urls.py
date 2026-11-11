from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from catalog import views as catalog_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "cuenta/login/",
        auth_views.LoginView.as_view(template_name="cuenta/login.html"),
        name="login",
    ),
    path("cuenta/registrarse/", catalog_views.register, name="registrarse"),
    path("cuenta/perfil/", catalog_views.profile, name="perfil"),
    path("cuenta/", include("django.contrib.auth.urls")),
    path("carrito/", include("catalog.cart_urls")),
    path("backoffice/", include("catalog.backoffice_urls")),
    path("", include("catalog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
