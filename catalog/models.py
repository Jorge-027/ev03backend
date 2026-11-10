from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify


class Genre(models.Model):
    name = models.CharField("nombre", max_length=80, unique=True)
    slug = models.SlugField("identificador", max_length=90, unique=True)
    description = models.TextField("descripción", blank=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "género"
        verbose_name_plural = "géneros"

    def __str__(self):
        return self.name


class Manga(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        OUT_OF_STOCK = "out_of_stock", "Agotado"
        PREORDER = "preorder", "Preventa"
        DISCONTINUED = "discontinued", "Descontinuado"

    genre = models.ForeignKey(
        Genre,
        on_delete=models.PROTECT,
        related_name="mangas",
        verbose_name="género",
    )
    title = models.CharField("título", max_length=180)
    slug = models.SlugField("identificador", max_length=200, unique=True)
    author = models.CharField("autor", max_length=120, blank=True)
    code = models.CharField("código", max_length=40, unique=True)
    description = models.TextField("descripción", blank=True)
    price = models.DecimalField(
        "precio",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    stock = models.PositiveIntegerField("unidades disponibles", default=0)
    status = models.CharField(
        "estado",
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    cover = models.ImageField("portada", upload_to="mangas/covers/", blank=True)
    is_active = models.BooleanField("visible en catálogo", default=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "manga"
        verbose_name_plural = "mangas"

    def __str__(self):
        return f"{self.title} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or slugify(self.code)
            candidate = base_slug
            suffix = 2
            while Manga.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)
