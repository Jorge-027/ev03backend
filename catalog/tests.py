from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .admin import GenreAdmin, MangaAdmin
from .forms import MangaForm
from .models import Genre, Manga


class StoreTestCase(TestCase):
    def setUp(self):
        self.genre = Genre.objects.create(name="Shonen", slug="shonen")
        self.manga = Manga.objects.create(
            genre=self.genre,
            title="Manga de prueba",
            code="TEST-001",
            price=Decimal("12.50"),
            stock=3,
        )


class DjangoAdminConfigurationTests(TestCase):
    def test_admin_site_uses_manga_nook_identity(self):
        self.assertEqual(admin.site.site_header, "Manga Nook - Panel de Control")
        self.assertEqual(admin.site.site_title, "Manga Nook Admin")
        self.assertEqual(
            admin.site.index_title,
            "Gestión Operativa de Recursos y Servicios",
        )

    def test_manga_admin_exposes_catalog_fields_and_inline_stock_editing(self):
        self.assertEqual(
            MangaAdmin.list_display,
            ("code", "title", "genre", "price", "stock", "status", "is_active"),
        )
        self.assertEqual(MangaAdmin.list_filter, ("genre", "status", "is_active"))
        self.assertEqual(
            MangaAdmin.search_fields,
            ("title", "code", "author", "description"),
        )
        self.assertIn("stock", MangaAdmin.list_editable)

    def test_genre_admin_uses_decorator_registered_configuration(self):
        self.assertIsInstance(admin.site._registry[Genre], GenreAdmin)
        self.assertEqual(GenreAdmin.list_filter, ("is_active",))
        self.assertEqual(GenreAdmin.search_fields, ("name", "description"))


class PublicCatalogTests(StoreTestCase):
    def test_catalog_supports_search_and_genre_filter(self):
        response = self.client.get(
            reverse("catalog:catalog"),
            {"q": "TEST-001", "genero": "shonen"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manga de prueba")

    def test_catalog_supports_price_ordering_and_pagination(self):
        for index in range(12):
            Manga.objects.create(
                genre=self.genre,
                title=f"Manga adicional {index:02}",
                code=f"ADD-{index:03}",
                price=Decimal(index + 1),
                stock=1,
            )

        response = self.client.get(reverse("catalog:catalog"), {"orden": "price"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 13)
        self.assertEqual(response.context["mangas"][0].price, Decimal("1"))
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertContains(response, "page=2")

    def test_catalog_searches_description_and_detail_accepts_code(self):
        self.manga.description = "Edición especial de colección"
        self.manga.code = "TEST.001"
        self.manga.save(update_fields=("description", "code"))
        response = self.client.get(reverse("catalog:catalog"), {"q": "colección"})
        self.assertContains(response, "Manga de prueba")

        response = self.client.get(
            reverse("catalog:manga_detail", args=(self.manga.code,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manga de prueba")

    def test_inactive_manga_is_not_public(self):
        self.manga.is_active = False
        self.manga.save(update_fields=("is_active",))
        response = self.client.get(reverse("catalog:catalog"))
        self.assertNotContains(response, "Manga de prueba")

    def test_catalog_renders_empty_state_without_seeded_mangas(self):
        Manga.objects.all().delete()
        response = self.client.get(reverse("catalog:catalog"))
        self.assertContains(response, "Aún no hay mangas")


class SessionCartTests(StoreTestCase):
    def test_cart_add_and_update_calculates_total_without_creating_orders(self):
        self.client.post(reverse("cart:add", args=(self.manga.pk,)))
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.context["total"], Decimal("12.50"))

        self.client.post(
            reverse("cart:update", args=(self.manga.pk,)),
            {"quantity": "2"},
        )
        response = self.client.get(reverse("cart:detail"))
        self.assertEqual(response.context["total"], Decimal("25.00"))
        self.assertEqual(Manga.objects.count(), 1)

    def test_cart_cannot_exceed_available_stock(self):
        self.client.post(reverse("cart:add", args=(self.manga.pk,)))
        self.client.post(
            reverse("cart:update", args=(self.manga.pk,)),
            {"quantity": "4"},
        )
        self.assertEqual(self.client.session["cart"][str(self.manga.pk)], 1)

    def test_protected_genre_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.genre.delete()


class BackofficeTests(StoreTestCase):
    def test_backoffice_requires_authorized_staff(self):
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('backoffice:dashboard')}",
        )

        user = get_user_model().objects.create_user(
            username="cliente",
            password="cliente-password",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_access_backoffice(self):
        staff = get_user_model().objects.create_user(
            username="staff",
            password="staff-password",
            is_staff=True,
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_create_and_logically_deactivate_manga(self):
        staff = get_user_model().objects.create_user(
            username="staff-editor",
            password="staff-password",
            is_staff=True,
        )
        self.client.force_login(staff)
        response = self.client.post(
            reverse("backoffice:manga_create"),
            {
                "genre": self.genre.pk,
                "title": "Manga para crear",
                "slug": "",
                "author": "Autor de prueba",
                "code": "NEW-001",
                "description": "Registro de prueba.",
                "price": "9.90",
                "stock": "2",
                "status": Manga.Status.AVAILABLE,
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("backoffice:mangas"))
        manga = Manga.objects.get(code="NEW-001")
        self.assertEqual(manga.slug, "manga-para-crear")

        response = self.client.post(
            reverse("backoffice:manga_deactivate", args=(manga.pk,))
        )
        self.assertRedirects(response, reverse("backoffice:mangas"))
        manga.refresh_from_db()
        self.assertFalse(manga.is_active)

    def test_staff_can_create_manga_with_uploaded_cover(self):
        staff = get_user_model().objects.create_user(
            username="staff-cover",
            password="cover-password",
            is_staff=True,
        )
        self.client.force_login(staff)
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(image_buffer, format="JPEG")
        image = SimpleUploadedFile(
            "cover.jpg",
            image_buffer.getvalue(),
            content_type="image/jpeg",
        )

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("backoffice:manga_create"),
                    {
                        "genre": self.genre.pk,
                        "title": "Manga con portada",
                        "slug": "",
                        "author": "",
                        "code": "COVER-001",
                        "description": "",
                        "price": "9.90",
                        "stock": "1",
                        "status": Manga.Status.AVAILABLE,
                        "is_active": "on",
                        "cover": image,
                    },
                )
                self.assertRedirects(response, reverse("backoffice:mangas"))

        manga = Manga.objects.get(code="COVER-001")
        self.assertTrue(manga.cover.name.endswith("cover.jpg"))


class MangaFormValidationTests(StoreTestCase):
    def form_data(self, **overrides):
        data = {
            "genre": self.genre.pk,
            "title": "Otro manga",
            "slug": "otro-manga",
            "author": "",
            "code": "OTHER-001",
            "description": "",
            "price": "10.00",
            "stock": "2",
            "status": Manga.Status.AVAILABLE,
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def test_form_rejects_duplicate_code_and_slug(self):
        duplicate_code_form = MangaForm(
            data=self.form_data(code=self.manga.code)
        )
        self.assertFalse(duplicate_code_form.is_valid())
        self.assertIn("code", duplicate_code_form.errors)

        duplicate_slug_form = MangaForm(
            data=self.form_data(slug=self.manga.slug)
        )
        self.assertFalse(duplicate_slug_form.is_valid())
        self.assertIn("slug", duplicate_slug_form.errors)

    def test_form_rejects_negative_quantitative_values(self):
        negative_price_form = MangaForm(data=self.form_data(price="-1.00"))
        self.assertFalse(negative_price_form.is_valid())
        self.assertIn("price", negative_price_form.errors)

        negative_stock_form = MangaForm(data=self.form_data(stock="-1"))
        self.assertFalse(negative_stock_form.is_valid())
        self.assertIn("stock", negative_stock_form.errors)


class PopulateDataCommandTests(TestCase):
    def test_command_creates_genres_and_users_but_no_manga_examples(self):
        call_command("poblar_datos", stdout=None)
        self.assertEqual(Genre.objects.count(), 4)
        self.assertEqual(Manga.objects.count(), 0)
        users = get_user_model().objects
        self.assertTrue(users.get(username="admin").is_superuser)
        self.assertFalse(users.get(username="usuario").is_staff)
