Nombre de la Organización o Plataforma: Manga's Bizarre Buying
Modelo de Negocio / Giro: Comercio Minorista
Integrantes del Equipo: Jorge Sepúlveda 21.986.602-K
Entidad de Contexto / Agrupación (ORM): Local Comercial
Entidad Principal Gestionable (ORM): Tienda
Propósito de la Sesión (request.session): Crear una mini comunidad y que la gente lea mas mangas

## Bitácora de prompts de IA

Se usó Copilot como apoyo técnico. Las propuestas se contrastaron con el código,
las reglas del proyecto y las pruebas; la herramienta no reemplazó la revisión.

### Caso 1: arquitectura de perfiles

- **Prompt:** ¿Cómo agregar RUT, teléfono y rol institucional sin reemplazar el modelo de usuario de Django?
- **Respuesta técnica:** Mantener `django.contrib.auth.User` y asociar un perfil mediante una relación `OneToOneField`; crear el perfil al registrar y permitir su edición con un `ModelForm`.
- **Adaptación aplicada:** Se añadió `UserProfile` con esos campos, roles acotados, formulario de edición autenticado y migración. Los campos complementarios son opcionales para no exigir datos personales al registrarse.

### Caso 2: carrito y solicitud simulada

- **Prompt:** ¿Cómo generar un comprobante desde un carrito de sesión sin crear pedidos ni modificar inventario?
- **Respuesta técnica:** Revalidar disponibilidad y cantidades al confirmar, copiar los detalles y totales a la sesión, vaciar el carrito y mostrar el comprobante desde esa misma sesión.
- **Adaptación aplicada:** La ruta de solicitud valida disponibilidad y stock, calcula subtotales y total, conserva el comprobante en `request.session` y deja el inventario intacto. No se aplican impuestos o recargos porque el proyecto no define ninguno.

### Caso 3: seguridad y consultas

- **Prompt:** ¿Qué revisar al proteger operaciones administrativas y al mostrar el contador del carrito?
- **Respuesta técnica:** Usar los decoradores de autenticación y autorización de Django, exigir CSRF en las peticiones POST y centralizar el contador en un context processor que lea la sesión.
- **Adaptación aplicada:** Se mantuvo la protección del backoffice para personal autenticado (`is_staff`), se añadieron registro y perfil con CSRF, y el contador global se calcula desde las unidades válidas de la sesión. Las pruebas verifican acceso, CSRF, registro y comprobante.
