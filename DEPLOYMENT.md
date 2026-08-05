# Ambiente de Producción

## Configurar variables de entorno

[config/settings.py](config/settings.py) lee `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` y `DATABASE_URL` de variables de entorno. Ninguna es necesaria para desarrollo local; todas tienen valores por defecto seguros: `SECRET_KEY` cae a una llave insegura de desarrollo, `DEBUG` a `True`, `ALLOWED_HOSTS` a vacío (Django permite `localhost`/`127.0.0.1` automáticamente cuando `DEBUG=True`) y `DATABASE_URL` a una instancia de SQLite local.

Por lo tanto, en producción hay que asignar valores a `SECRET_KEY`, `ALLOWED_HOSTS` y `DATABASE_URL`. En caso contrario, `docker compose` se niega a arrancar con un mensaje claro, en vez de fallar a medias dentro del contenedor.

```bash
SECRET_KEY="<clave larga y aleatoria>"
DEBUG="False"
ALLOWED_HOSTS="ejemplo.com,www.ejemplo.com"
DATABASE_URL="postgres://usuario:contraseña@host:5432/nombre_db"
```

## Base de datos

El ambiente de desarrollo (`dev`) usa SQLite por defecto, sin servicios adicionales, sin configuración. El ambiente de producción usa Postgres, configurado vía `DATABASE_URL` (parseado con [dj-database-url](https://pypi.org/project/dj-database-url/); el driver es [psycopg](https://www.psycopg.org/psycopg3/)). Esta decisión es intencional: dado el tamaño actual del proyecto (CRUD simple sobre el ORM de Django, sin funcionalidades específicas de Postgres), el riesgo de divergencia entre dev y producción es bajo, así que mantener SQLite en `dev` evita añadir un servicio extra al flujo de desarrollo local. Si el proyecto crece en complejidad, vale la pena revisar esta decisión.

`docker-compose.prod.yml` no incluye un contenedor de Postgres — se espera una base de datos administrada externa (RDS, Render, Railway, Supabase, etc.), apuntada vía `DATABASE_URL`.

## Archivos estáticos

Con `DEBUG=False`, Django deja de servir archivos estáticos automáticamente. En producción esto lo maneja [WhiteNoise](https://whitenoise.readthedocs.io/): sirve los archivos directamente desde Gunicorn (sin necesidad de nginx u otro servidor aparte), con compresión gzip y nombres de archivo con hash (e.g. `main.00e0ebb078fb.css`) para poder guardarlos en cache de forma segura por mucho tiempo (`Cache-Control: max-age=315360000, immutable`).

`docker-compose.prod.yml` corre `collectstatic` automáticamente al iniciar el contenedor, antes de `migrate` y de levantar Gunicorn. En `dev` no hace falta `collectstatic` en absoluto pues con `DEBUG=True`, Django sirve los archivos directo desde `STATICFILES_DIRS`, sin hash en el nombre.

## Ejecutar con Docker

`docker-compose.yml` es para desarrollo local. Para producción existe [docker-compose.prod.yml](docker-compose.prod.yml), que corre la app con [Gunicorn](https://gunicorn.org/) en vez del servidor de desarrollo de Django.

```bash
SECRET_KEY="<clave larga y aleatoria>" \
ALLOWED_HOSTS="ejemplo.com,www.ejemplo.com" \
DATABASE_URL="postgres://usuario:contraseña@host:5432/nombre_db" \
docker compose -f docker-compose.prod.yml up --build
```
