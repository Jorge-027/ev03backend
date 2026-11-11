from django import forms

from .models import Genre, Manga


class MangaForm(forms.ModelForm):
    slug = forms.SlugField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = (
                "form-check-input"
                if isinstance(field.widget, forms.CheckboxInput)
                else "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class

    def clean_code(self):
        code = self.cleaned_data["code"]
        if Manga.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un manga con este código.")
        return code

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        if slug and Manga.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un manga con este identificador.")
        return slug

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data["stock"]
        if stock < 0:
            raise forms.ValidationError("Las unidades disponibles no pueden ser negativas.")
        return stock

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = (
                "form-check-input"
                if isinstance(field.widget, forms.CheckboxInput)
                else "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs["class"] = css_class

    class Meta:
        model = Genre
        fields = ("name", "slug", "description", "is_active")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
