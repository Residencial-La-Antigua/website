# Ambiente de Producción

## Configurar variables de entorno

[config/settings.py](config/settings.py) lee `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL` y `ANALYTICS_SALT` de variables de entorno. Ninguna es necesaria para desarrollo local. `SECRET_KEY` y `ANALYTICS_SALT` tienen valores predefinidos e inseguros de desarrollo, `DEBUG` es igual a `True`, `ALLOWED_HOSTS` a vacío (Django permite `localhost`/`127.0.0.1` automáticamente cuando `DEBUG=True`) y `DATABASE_URL` a una instancia de SQLite local.

Por lo tanto, en producción hay que asignar valores a `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL` y `ANALYTICS_SALT`. En caso contrario, `docker compose` se niega a arrancar.

```bash
SECRET_KEY="<clave larga y aleatoria>"
DEBUG="False"
ALLOWED_HOSTS="ejemplo.com,www.ejemplo.com"
DATABASE_URL="postgres://usuario:contraseña@host:5432/nombre_db"
ANALYTICS_SALT="<clave larga y aleatoria, distinta de SECRET_KEY>"
```

## Zona horaria del calendario

`config/settings.py` usa `TIME_ZONE = "UTC"` para toda la aplicación, pero la comunidad de residentes vive físicamente en una sola zona horaria real. `RESIDENT_TZ` en [calendario/timezones.py](calendario/timezones.py) es esa zona horaria: se usa para convertir la hora que un residente escribe en el formulario del calendario a UTC antes de guardarla, y de vuelta a la hora local al mostrarla en el calendario.

De momento, es intencional mantener este valor específico al módulo `calendario` en vez de una configuración global. Si este proyecto se adapta para una comunidad en otra zona horaria, hay que actualizar `RESIDENT_TZ` y `RESIDENT_LOCAL_UTC_OFFSET_MS` (`static/js/calendario.js`) respectivamente.

## Base de datos

El ambiente de desarrollo (`dev`) usa SQLite por defecto, sin servicios adicionales, sin configuración. El ambiente de producción usa Postgres, configurado vía `DATABASE_URL` (parseado con [dj-database-url](https://pypi.org/project/dj-database-url/); el driver es [psycopg](https://www.psycopg.org/psycopg3/)). Esta decisión es intencional: dado el tamaño actual del proyecto (CRUD simple sobre el ORM de Django, sin funcionalidades específicas de Postgres), el riesgo de divergencia entre dev y producción es bajo, así que mantener SQLite en `dev` evita añadir un servicio extra al flujo de desarrollo local. Si el proyecto crece en complejidad, vale la pena revisar esta decisión.

`docker-compose.prod.yml` no incluye un contenedor de Postgres. Se espera una base de datos administrada externa (RDS, Render, Railway, Supabase, etc.), apuntada vía `DATABASE_URL`.

## Archivos estáticos

Con `DEBUG=False`, Django deja de servir archivos estáticos automáticamente. En producción esto lo maneja [WhiteNoise](https://whitenoise.readthedocs.io/): sirve los archivos directamente desde Gunicorn (sin necesidad de nginx u otro servidor aparte), con compresión gzip y nombres de archivo con hash (e.g. `main.00e0ebb078fb.css`) para poder guardarlos en cache de forma segura por mucho tiempo (`Cache-Control: max-age=315360000, immutable`).

`docker-compose.prod.yml` corre `collectstatic` automáticamente al iniciar el contenedor, antes de `migrate` y de levantar Gunicorn. En `dev` no hace falta `collectstatic` en absoluto pues con `DEBUG=True`, Django sirve los archivos directo desde `STATICFILES_DIRS`, sin hash en el nombre.

## Ejecutar con Docker

`docker-compose.yml` es para desarrollo local. Para producción existe [docker-compose.prod.yml](docker-compose.prod.yml), que corre la app con [Gunicorn](https://gunicorn.org/) en vez del servidor de desarrollo de Django.

```bash
SECRET_KEY="<clave larga y aleatoria>" \
ALLOWED_HOSTS="ejemplo.com,www.ejemplo.com" \
DATABASE_URL="postgres://usuario:contraseña@host:5432/nombre_db" \
ANALYTICS_SALT="<clave larga y aleatoria, distinta de SECRET_KEY>" \
docker compose -f docker-compose.prod.yml up --build
```

El arranque real para producción (`collectstatic` → `migrate` → Gunicorn) se encuentra especificado en [scripts/start-prod.sh](scripts/start-prod.sh), y es el `CMD` por defecto del [Dockerfile](Dockerfile). Así, `docker-compose.prod.yml` no lo especifica por aparte.

La app escucha en el puerto definido por la variable de entorno `PORT` (por defecto `8000`). Esto es para compatibilidad con plataformas como Render que asignan su propio puerto dinámicamente.

### Concurrencia (workers de Gunicorn)

[scripts/start-prod.sh](scripts/start-prod.sh) arranca Gunicorn con `--workers 3` y la clase de worker por defecto (`sync`). Cada worker es un proceso de sistema operativo independiente que atiende **una petición a la vez**. Con 3 workers, la app procesa como máximo 3 peticiones simultáneas; cualquier petición adicional espera en cola a nivel del socket hasta que un worker quede libre. Cada worker maneja su propia petición de forma totalmente independiente.

Gunicorn no impone un máximo de workers; su documentación sugiere `(2 × cores) + 1` como punto de partida. Si la concurrencia real llegara a ser un cuello de botella, las dos palancas estándar serían aumentar `--workers` (limitado por CPU/RAM disponibles, ya que cada worker carga su propia copia completa de la app) o cambiar a una clase de worker con hilos o async (`gthread`, `gevent`), que permite que un mismo worker atienda varias peticiones en vuelo a la vez.

## Despliegue automático (GitHub Actions + VM de Azure)

[.github/workflows/deploy.yml](.github/workflows/deploy.yml) despliega automáticamente a una VM de Azure en cada push a `main`. El job `deploy` corre en un **runner autohospedado (self-hosted) instalado directamente en la VM**, no en un runner de GitHub. Con un runner autohospedado, el job corre localmente en la VM: no hace falta abrir el puerto 22 a GitHub ni manejar llaves SSH en absoluto.

La configuración vigente de Azure, nginx, TLS, Docker sin privilegios y el runner se encuentra en [Infra-doc.md](Infra-doc.md). No agregar `gha-deploy` al grupo `docker` del sistema: el runner usa su propio daemon sin privilegios.

### Cómo funciona el deploy

El job `deploy` hace checkout del código directamente en la VM, escribe un `.env` a partir de los secretos requeridos, construye la imagen con `docker build`, y reinicia el contenedor con `docker compose -f docker-compose.prod.yml up -d`. `docker image prune -f` al final evita que las imágenes viejas se acumulen en disco.

nginx termina HTTPS y reenvía `X-Forwarded-Proto` a Django. La aplicación debe configurar `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` para reconocer el esquema público. Este encabezado solo es confiable mientras nginx lo sobrescriba y Gunicorn permanezca publicado exclusivamente en `127.0.0.1`. Con esto, el chequeo de CSRF de Django ya funciona sin necesitar `CSRF_TRUSTED_ORIGINS`: Django acepta un POST cuyo `Origin` coincide con el host de la propia petición.

## Desplegar en Render

Render construye la imagen directamente desde el [Dockerfile](Dockerfile) i.e. no lee `docker-compose.prod.yml`. Al crear el Web Service:

- **Language**: Docker
- **Docker Command** (en Advanced): `sh scripts/start-prod.sh`
- **Variables de entorno**: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, `ANALYTICS_SALT`, `ALLOWED_HOSTS` — esta última hay que agregarla _después_ de crear el servicio (en caso de utilizar una solución de hosting como Render pues se debe saber cuál es el dominio). Sin `ALLOWED_HOSTS` todas las peticiones se rechazan con `DisallowedHost`.
