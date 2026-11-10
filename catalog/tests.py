from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

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


class PublicCatalogTests(StoreTestCase):
    def test_catalog_supports_search_and_genre_filter(self):
        response = self.client.get(
            reverse("catalog:catalog"),
            {"q": "TEST-001", "genero": "shonen"},
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


class PopulateDataCommandTests(TestCase):
    def test_command_creates_genres_and_users_but_no_manga_examples(self):
        call_command("poblar_datos", stdout=None)
        self.assertEqual(Genre.objects.count(), 4)
        self.assertEqual(Manga.objects.count(), 0)
        users = get_user_model().objects
        self.assertTrue(users.get(username="admin").is_superuser)
        self.assertFalse(users.get(username="usuario").is_staff)
