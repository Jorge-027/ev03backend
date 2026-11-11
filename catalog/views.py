from decimal import Decimal
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import urlencode, url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import GenreForm, MangaForm, RegistrationForm, UserProfileForm
from .models import Genre, Manga, UserProfile


def catalog(request):
    mangas = Manga.objects.filter(
        is_active=True,
        genre__is_active=True,
    ).select_related("genre")
    genres = Genre.objects.filter(is_active=True)
    query = request.GET.get("q", "").strip()
    genre_slug = request.GET.get("genero", "").strip()
    ordering_options = {
        "title": "title",
        "-title": "-title",
        "price": "price",
        "-price": "-price",
        "newest": "-created_at",
    }
    ordering = request.GET.get("orden", "title")
    if ordering not in ordering_options:
        ordering = "title"

    if query:
        mangas = mangas.filter(
            Q(title__icontains=query)
            | Q(code__icontains=query)
            | Q(description__icontains=query)
            | Q(author__icontains=query)
        )
    if genre_slug:
        mangas = mangas.filter(genre__slug=genre_slug, genre__is_active=True)

    mangas = mangas.order_by(ordering_options[ordering])
    paginator = Paginator(mangas, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "catalogo/catalogo.html",
        {
            "mangas": page_obj.object_list,
            "page_obj": page_obj,
            "genres": genres,
            "query": query,
            "selected_genre": genre_slug,
            "selected_ordering": ordering,
            "querystring": urlencode(query_params),
        },
    )


def manga_detail(request, slug):
    manga = get_object_or_404(
        Manga.objects.select_related("genre"),
        Q(slug=slug) | Q(code=slug),
        is_active=True,
        genre__is_active=True,
    )
    return render(request, "catalogo/detalle_manga.html", {"manga": manga})


def cart_detail(request):
    cart = request.session.get("cart", {})
    mangas = Manga.objects.filter(
        pk__in=cart.keys(),
        is_active=True,
        genre__is_active=True,
    ).select_related("genre")
    items = [
        {
            "manga": manga,
            "quantity": cart.get(str(manga.pk), 0),
            "subtotal": manga.price * cart.get(str(manga.pk), 0),
        }
        for manga in mangas
    ]
    total = sum((item["subtotal"] for item in items), Decimal("0.00"))
    return render(
        request,
        "catalogo/carrito.html",
        {"items": items, "subtotal": total, "tax": Decimal("0.00"), "total": total},
    )


@require_POST
def cart_add(request, manga_id):
    manga = get_object_or_404(
        Manga,
        pk=manga_id,
        is_active=True,
        genre__is_active=True,
        status__in=(Manga.Status.AVAILABLE, Manga.Status.PREORDER),
    )
    cart = request.session.get("cart", {})
    key = str(manga.pk)
    quantity = cart.get(key, 0) + 1
    if manga.stock and quantity > manga.stock:
        messages.error(request, "No hay unidades suficientes disponibles.")
    elif manga.stock == 0 and manga.status != Manga.Status.PREORDER:
        messages.error(request, "Este manga no tiene unidades disponibles.")
    else:
        cart[key] = quantity
        request.session["cart"] = cart
        messages.success(request, "Manga agregado al carrito.")
    referrer = request.META.get("HTTP_REFERER", "")
    if referrer and url_has_allowed_host_and_scheme(
        referrer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referrer)
    return redirect("catalogo:catalogo")


@require_POST
def cart_update(request, manga_id):
    cart = request.session.get("cart", {})
    key = str(manga_id)
    if key in cart:
        try:
            quantity = int(request.POST.get("quantity", ""))
        except ValueError:
            messages.error(request, "Ingresa una cantidad entera válida.")
            return redirect("carrito:detalle")
        if quantity < 0:
            messages.error(request, "La cantidad no puede ser negativa.")
            return redirect("carrito:detalle")
        if quantity == 0:
            cart.pop(key)
        else:
            manga = Manga.objects.filter(
                pk=manga_id,
                is_active=True,
                genre__is_active=True,
                status__in=(Manga.Status.AVAILABLE, Manga.Status.PREORDER),
            ).first()
            if manga is None:
                cart.pop(key)
                messages.error(request, "Este manga ya no está disponible.")
            elif manga.stock and quantity > manga.stock:
                messages.error(request, "La cantidad supera las unidades disponibles.")
            elif manga.stock == 0 and manga.status != Manga.Status.PREORDER:
                cart.pop(key)
                messages.error(request, "Este manga ya no tiene unidades disponibles.")
            else:
                cart[key] = quantity
        request.session["cart"] = cart
    return redirect("carrito:detalle")


@require_POST
def cart_remove(request, manga_id):
    cart = request.session.get("cart", {})
    cart.pop(str(manga_id), None)
    request.session["cart"] = cart
    return redirect("carrito:detalle")


@require_POST
def cart_clear(request):
    request.session["cart"] = {}
    return redirect("carrito:detalle")


@require_POST
def cart_checkout(request):
    cart = request.session.get("cart", {})
    if not cart:
        messages.error(request, "Agrega mangas antes de generar una solicitud.")
        return redirect("carrito:detalle")

    mangas = Manga.objects.filter(
        pk__in=cart.keys(),
        is_active=True,
        genre__is_active=True,
        status__in=(Manga.Status.AVAILABLE, Manga.Status.PREORDER),
    ).select_related("genre")
    receipt_items = []
    for manga in mangas:
        quantity = cart.get(str(manga.pk))
        if not isinstance(quantity, int) or quantity < 1:
            messages.error(request, "El carrito contiene una cantidad no válida.")
            return redirect("carrito:detalle")
        if manga.stock and quantity > manga.stock:
            messages.error(
                request,
                f"El stock de «{manga.title}» cambió. Ajusta la cantidad antes de continuar.",
            )
            return redirect("carrito:detalle")
        if manga.stock == 0 and manga.status != Manga.Status.PREORDER:
            messages.error(request, f"«{manga.title}» ya no está disponible.")
            return redirect("carrito:detalle")
        line_total = manga.price * quantity
        receipt_items.append(
            {
                "title": manga.title,
                "code": manga.code,
                "quantity": quantity,
                "unit_price": str(manga.price),
                "subtotal": str(line_total),
            }
        )

    if len(receipt_items) != len(cart):
        messages.error(
            request,
            "Uno o más mangas ya no están disponibles. Revisa el carrito.",
        )
        return redirect("carrito:detalle")

    subtotal = sum(
        (Decimal(item["subtotal"]) for item in receipt_items),
        Decimal("0.00"),
    )
    request.session["cart_receipt"] = {
        "number": uuid4().hex[:12].upper(),
        "created_at": timezone.localtime().strftime("%d-%m-%Y %H:%M"),
        "items": receipt_items,
        "subtotal": str(subtotal),
        "tax": "0.00",
        "total": str(subtotal),
    }
    request.session["cart"] = {}
    return redirect("carrito:boleta")


def cart_receipt(request):
    receipt = request.session.get("cart_receipt")
    if not receipt:
        messages.info(request, "No hay una solicitud reciente en esta sesión.")
        return redirect("carrito:detalle")
    return render(request, "catalogo/boleta.html", {"receipt": receipt})


def _is_staff(user):
    return user.is_authenticated and user.is_staff


def staff_required(view_func):
    protected_view = user_passes_test(_is_staff, login_url="login")(view_func)
    return login_required(protected_view, login_url="login")


def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            UserProfile.objects.create(user=user)
        messages.success(request, "Cuenta creada. Ya puedes iniciar sesión.")
        return redirect("login")
    return render(request, "cuenta/registrarse.html", {"form": form})


@login_required
def profile(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = UserProfileForm(request.POST or None, instance=user_profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado.")
        return redirect("perfil")
    return render(request, "cuenta/perfil.html", {"form": form})


@staff_required
def backoffice_dashboard(request):
    return render(
        request,
        "catalogo/administracion/panel.html",
        {
            "manga_count": Manga.objects.count(),
            "genre_count": Genre.objects.count(),
        },
    )


@staff_required
def backoffice_mangas(request):
    mangas = Manga.objects.select_related("genre").order_by("title")
    return render(request, "catalogo/administracion/mangas.html", {"mangas": mangas})


@staff_required
def manga_create(request):
    form = MangaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Manga creado.")
        return redirect("backoffice:mangas")
    return render(
        request,
        "catalogo/administracion/formulario.html",
        {
            "form": form,
            "title": "Agregar manga",
            "cancel_url": "backoffice:mangas",
        },
    )


@staff_required
def manga_edit(request, pk):
    manga = get_object_or_404(Manga, pk=pk)
    form = MangaForm(request.POST or None, request.FILES or None, instance=manga)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Manga actualizado.")
        return redirect("backoffice:mangas")
    return render(
        request,
        "catalogo/administracion/formulario.html",
        {
            "form": form,
            "title": "Editar manga",
            "cancel_url": "backoffice:mangas",
        },
    )


@staff_required
@require_POST
def manga_deactivate(request, pk):
    manga = get_object_or_404(Manga, pk=pk)
    manga.is_active = False
    manga.save(update_fields=("is_active", "updated_at"))
    messages.success(request, "Manga desactivado; el registro se conservó.")
    return redirect("backoffice:mangas")


@staff_required
def backoffice_genres(request):
    genres = Genre.objects.order_by("name")
    return render(request, "catalogo/administracion/generos.html", {"genres": genres})


@staff_required
def genre_create(request):
    form = GenreForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Género creado.")
        return redirect("backoffice:genres")
    return render(
        request,
        "catalogo/administracion/formulario.html",
        {
            "form": form,
            "title": "Agregar género",
            "cancel_url": "backoffice:genres",
        },
    )


@staff_required
def genre_edit(request, pk):
    genre = get_object_or_404(Genre, pk=pk)
    form = GenreForm(request.POST or None, instance=genre)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Género actualizado.")
        return redirect("backoffice:genres")
    return render(
        request,
        "catalogo/administracion/formulario.html",
        {
            "form": form,
            "title": "Editar género",
            "cancel_url": "backoffice:genres",
        },
    )


@staff_required
@require_POST
def genre_delete(request, pk):
    genre = get_object_or_404(Genre, pk=pk)
    try:
        genre.delete()
    except ProtectedError:
        messages.error(request, "No se puede eliminar un género que tiene mangas asociados.")
    else:
        messages.success(request, "Género eliminado.")
    return redirect("backoffice:genres")
