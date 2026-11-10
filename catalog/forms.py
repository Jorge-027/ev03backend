from django import forms

from .models import Genre, Manga


class MangaForm(forms.ModelForm):
    slug = forms.SlugField(required=False)

    class Meta:
        model = Manga
        fields = (
            "genre",
            "title",
            "slug",
            "author",
            "code",
            "description",
            "price",
            "stock",
            "status",
            "cover",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class GenreForm(forms.ModelForm):
    class Meta:
        model = Genre
        fields = ("name", "slug", "description", "is_active")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
