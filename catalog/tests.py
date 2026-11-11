from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .admin import GenreAdmin, MangaAdmin
from .formatting import format_clp
from .forms import MangaForm
from .models import Genre, Manga, UserProfile


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


class SpanishRouteNameTests(TestCase):
    def test_translated_routes_and_unchanged_login_route(self):
        self.assertEqual(reverse("catalogo:catalogo"), "/")
        self.assertEqual(
            reverse("catalogo:detalle_manga", args=("mi-manga",)),
            "/detalle_manga/mi-manga/",
        )
        self.assertEqual(reverse("carrito:detalle"), "/carrito/")
        self.assertEqual(reverse("carrito:boleta"), "/carrito/boleta/")
        self.assertEqual(reverse("perfil"), "/cuenta/perfil/")
        self.assertEqual(reverse("registrarse"), "/cuenta/registrarse/")
        self.assertEqual(reverse("login"), "/cuenta/login/")

    def test_login_uses_unchanged_filename_in_spanish_templates_folder(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cuenta/login.html")


class DjangoAdminConfigurationTests(TestCase):
    def test_admin_site_uses_store_identity(self):
        self.assertEqual(
            admin.site.site_header,
            "Manga's Bizarre Buying - Panel de Control",
        )
        self.assertEqual(admin.site.site_title, "Manga's Bizarre Buying Admin")
        self.assertEqual(
            admin.site.index_title,
            "Gestión Operativa de Recursos y Servicios",
        )

    def test_manga_admin_exposes_catalog_fields_and_inline_stock_editing(self):
        self.assertEqual(
            MangaAdmin.list_display,
            (
                "code",
                "title",
                "genre",
                "formatted_price",
                "stock",
                "status",
                "is_active",
            ),
        )
        self.assertEqual(MangaAdmin.list_filter, ("genre", "status", "is_active"))
        self.assertEqual(
            MangaAdmin.search_fields,
            ("title", "code", "author", "description"),
        )
        self.assertIn("stock", MangaAdmin.list_editable)

    def test_price_format_uses_period_thousands_and_no_decimals(self):
        self.assertEqual(format_clp(Decimal("1234567.89")), "1.234.568")

    def test_genre_admin_uses_decorator_registered_configuration(self):
        self.assertIsInstance(admin.site._registry[Genre], GenreAdmin)
        self.assertEqual(GenreAdmin.list_filter, ("is_active",))
        self.assertEqual(GenreAdmin.search_fields, ("name", "description"))


class PublicCatalogTests(StoreTestCase):
    def test_catalog_supports_search_and_genre_filter(self):
        response = self.client.get(
            reverse("catalogo:catalogo"),
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

        response = self.client.get(reverse("catalogo:catalogo"), {"orden": "price"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 13)
        self.assertEqual(response.context["mangas"][0].price, Decimal("1"))
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertContains(response, "page=2")

    def test_catalog_searches_description_and_detail_accepts_code(self):
        self.manga.description = "Edición especial de colección"
        self.manga.code = "TEST.001"
        self.manga.save(update_fields=("description", "code"))
        response = self.client.get(reverse("catalogo:catalogo"), {"q": "colección"})
        self.assertContains(response, "Manga de prueba")

        response = self.client.get(
            reverse("catalogo:detalle_manga", args=(self.manga.code,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manga de prueba")

    def test_inactive_manga_is_not_public(self):
        self.manga.is_active = False
        self.manga.save(update_fields=("is_active",))
        response = self.client.get(reverse("catalogo:catalogo"))
        self.assertNotContains(response, "Manga de prueba")

    def test_catalog_renders_empty_state_without_seeded_mangas(self):
        Manga.objects.all().delete()
        response = self.client.get(reverse("catalogo:catalogo"))
        self.assertContains(response, "Aún no hay mangas")


class SessionCartTests(StoreTestCase):
    def test_cart_add_and_update_calculates_total_without_creating_orders(self):
        self.client.post(reverse("carrito:agregar", args=(self.manga.pk,)))
        response = self.client.get(reverse("carrito:detalle"))
        self.assertEqual(response.context["total"], Decimal("12.50"))

        self.client.post(
            reverse("carrito:actualizar", args=(self.manga.pk,)),
            {"quantity": "2"},
        )
        response = self.client.get(reverse("carrito:detalle"))
        self.assertEqual(response.context["total"], Decimal("25.00"))
        self.assertEqual(Manga.objects.count(), 1)

    def test_cart_cannot_exceed_available_stock(self):
        self.client.post(reverse("carrito:agregar", args=(self.manga.pk,)))
        self.client.post(
            reverse("carrito:actualizar", args=(self.manga.pk,)),
            {"quantity": "4"},
        )
        self.assertEqual(self.client.session["cart"][str(self.manga.pk)], 1)

    def test_cart_rejects_non_numeric_quantity_without_removing_item(self):
        self.client.post(reverse("carrito:agregar", args=(self.manga.pk,)))

        response = self.client.post(
            reverse("carrito:actualizar", args=(self.manga.pk,)),
            {"quantity": "abc"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["cart"][str(self.manga.pk)], 1)
        self.assertContains(response, "Ingresa una cantidad entera válida.")

    def test_protected_genre_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.genre.delete()

    def test_navbar_counts_cart_units_from_session(self):
        session = self.client.session
        session["cart"] = {str(self.manga.pk): 2}
        session.save()

        response = self.client.get(reverse("catalogo:catalogo"))

        self.assertContains(response, "Carrito (2)")

    def test_checkout_generates_session_receipt_and_clears_cart(self):
        self.client.post(reverse("carrito:agregar", args=(self.manga.pk,)))
        self.client.post(
            reverse("carrito:actualizar", args=(self.manga.pk,)),
            {"quantity": "2"},
        )

        response = self.client.post(reverse("carrito:solicitar"))

        self.assertRedirects(response, reverse("carrito:boleta"))
        self.assertEqual(self.client.session["cart"], {})
        receipt = self.client.session["cart_receipt"]
        self.assertEqual(receipt["subtotal"], "25.00")
        self.assertEqual(receipt["tax"], "0.00")
        self.assertEqual(receipt["total"], "25.00")
        self.assertEqual(receipt["items"][0]["quantity"], 2)
        self.manga.refresh_from_db()
        self.assertEqual(self.manga.stock, 3)

        response = self.client.get(reverse("carrito:boleta"))
        self.assertContains(response, "Solicitud simulada generada")
        self.assertContains(response, receipt["number"])

    def test_checkout_rejects_empty_cart(self):
        response = self.client.post(reverse("carrito:solicitar"))
        self.assertRedirects(response, reverse("carrito:detalle"))
        self.assertNotIn("cart_receipt", self.client.session)

    def test_checkout_revalidates_stock_and_preserves_cart_when_unavailable(self):
        self.client.post(reverse("carrito:agregar", args=(self.manga.pk,)))
        self.manga.stock = 0
        self.manga.save(update_fields=("stock",))

        response = self.client.post(reverse("carrito:solicitar"))

        self.assertRedirects(response, reverse("carrito:detalle"))
        self.assertEqual(self.client.session["cart"], {str(self.manga.pk): 1})
        self.assertNotIn("cart_receipt", self.client.session)


class AccountTests(TestCase):
    def test_registration_creates_standard_user_and_profile(self):
        response = self.client.post(
            reverse("registrarse"),
            {
                "username": "lector",
                "email": "lector@example.com",
                "password1": "S3curePass!word99",
                "password2": "S3curePass!word99",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = get_user_model().objects.get(username="lector")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_requires_login_and_can_be_updated(self):
        response = self.client.get(reverse("perfil"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('perfil')}",
        )

        user = get_user_model().objects.create_user(
            username="perfil",
            password="S3curePass!word99",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("perfil"),
            {
                "rut": "21.986.602-K",
                "phone": "+56912345678",
                "institutional_role": UserProfile.InstitutionalRole.STUDENT,
            },
        )
        self.assertRedirects(response, reverse("perfil"))
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.rut, "21.986.602-K")
        self.assertEqual(profile.phone, "+56912345678")
        self.assertEqual(
            profile.institutional_role,
            UserProfile.InstitutionalRole.STUDENT,
        )

    def test_login_logout_and_csrf_protection(self):
        user = get_user_model().objects.create_user(
            username="sesiones",
            password="S3curePass!word99",
        )
        self.assertTrue(
            self.client.login(username=user.username, password="S3curePass!word99")
        )
        self.assertEqual(self.client.get(reverse("perfil")).status_code, 200)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("catalogo:catalogo"))

        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("registrarse"),
            {
                "username": "sin-csrf",
                "email": "sin-csrf@example.com",
                "password1": "S3curePass!word99",
                "password2": "S3curePass!word99",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user_model().objects.filter(username="sin-csrf").exists())


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
