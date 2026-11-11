from django.contrib import admin

from .models import Genre, Manga, UserProfile

admin.site.site_header = "Manga Nook - Panel de Control"
admin.site.site_title = "Manga Nook Admin"
admin.site.index_title = "Gestión Operativa de Recursos y Servicios"


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Manga)
class MangaAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "genre", "price", "stock", "status", "is_active")
    list_editable = ("stock",)
    list_filter = ("genre", "status", "is_active")
    search_fields = ("title", "code", "author", "description")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ("genre",)
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "rut", "phone", "institutional_role")
    list_filter = ("institutional_role",)
    search_fields = ("user__username", "user__email", "rut", "phone")
