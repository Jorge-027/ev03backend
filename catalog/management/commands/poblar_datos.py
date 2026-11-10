import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.models import Genre


class Command(BaseCommand):
    help = "Crea géneros y usuarios locales de prueba, sin mangas de ejemplo."

    def handle(self, *args, **options):
        genres = (
            ("Shonen", "Historias orientadas a la aventura y la acción."),
            ("Shojo", "Historias de romance, amistad y crecimiento personal."),
            ("Seinen", "Historias dirigidas a un público adulto."),
            ("Josei", "Historias sobre experiencias y relaciones adultas."),
        )
        for name, description in genres:
            Genre.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "description": description},
            )

        user_model = get_user_model()
        self._create_user(
            user_model,
            username="admin",
            password=os.getenv("SEED_ADMIN_PASSWORD", "AdminLocal123!"),
            email="admin@example.local",
            is_staff=True,
            is_superuser=True,
        )
        self._create_user(
            user_model,
            username="usuario",
            password=os.getenv("SEED_USER_PASSWORD", "UsuarioLocal123!"),
            email="usuario@example.local",
            is_staff=False,
            is_superuser=False,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Datos listos: 4 géneros, usuarios admin/usuario y 0 mangas de ejemplo."
            )
        )

    def _create_user(
        self,
        user_model,
        *,
        username,
        password,
        email,
        is_staff,
        is_superuser,
    ):
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            },
        )
        if created:
            user.set_password(password)
            user.save(update_fields=("password",))
            self.stdout.write(f"Usuario de prueba creado: {username}")
        else:
            self.stdout.write(f"Usuario existente sin cambios: {username}")
