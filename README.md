# Manga Nook

Tienda de manga de ejemplo construida con Django. Usa SQLite local, un catálogo público y un carrito temporal guardado en `request.session`. El carrito calcula cantidades y subtotal, pero no crea pedidos ni escribe sus productos en la base de datos.

## Requisitos

- Python 3.12 o superior.
- Windows PowerShell (los comandos equivalentes pueden adaptarse a otros sistemas).

## Instalación local

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py poblar_datos
python manage.py runserver
```

La aplicación queda en <http://127.0.0.1:8000/>. La base de datos se crea en `db.sqlite3` en la raíz del proyecto. `MEDIA_ROOT` guarda las portadas cargadas en `media/`.

El comando `poblar_datos` crea cuatro géneros y los usuarios locales de prueba `admin` y `usuario`; **no crea mangas**. Las contraseñas de desarrollo están indicadas en `.env.example`. Cámbialas para cualquier uso distinto de pruebas locales. `admin` puede acceder a `/admin/` y `/backoffice/`; `usuario` es una cuenta estándar.

## Funcionalidades

- Catálogo público con búsqueda por título, autor, código o descripción y filtro por género.
- Ficha pública para cada manga activo.
- Carrito temporal por sesión con ajuste de cantidades, cálculo de subtotal y vaciado.
- Backoffice restringido a usuarios `staff` para crear, editar y dar de baja lógica mangas, y administrar géneros.
- Django Admin con filtros, búsqueda y columnas adaptadas a los modelos.
- Los mangas y géneros no se eliminan físicamente desde el backoffice; la baja de mangas desactiva el registro.

## Configuración

`.env.example` contiene las variables locales de referencia. `.env`, la base SQLite y archivos multimedia están excluidos de Git. `SECRET_KEY` y contraseñas de ejemplo son solo para desarrollo.

Para validar cambios:

```powershell
python manage.py check
python manage.py test
```
