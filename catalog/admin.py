from django.contrib import admin

from .models import Genre, Manga

admin.site.site_header = "Manga Nook | Administración"
admin.site.site_title = "Manga Nook"
admin.site.index_title = "Gestión de la tienda"


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Manga)
class MangaAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "genre", "price", "stock", "status", "is_active")
    list_editable = ("is_active",)
    list_filter = ("genre", "status", "is_active")
    search_fields = ("title", "code", "author", "description")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ("genre",)
    readonly_fields = ("created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False
