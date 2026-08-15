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

El arranque real para producción (`collectstatic` → `migrate` → Gunicorn) se encuentra especificado en [scripts/start-prod.sh](scripts/start-prod.sh), y es el `CMD` por defecto del [Dockerfile](Dockerfile). Así, `docker-compose.prod.yml` no lo especifica por aparte.

La app escucha en el puerto definido por la variable de entorno `PORT` (por defecto `8000`). Esto es para compatibilidad con plataformas como Render que asignan su propio puerto dinámicamente.

## Despliegue automático (GitHub Actions + VM de Azure)

[.github/workflows/deploy.yml](.github/workflows/deploy.yml) despliega automáticamente a una VM de Azure en cada push a `main`. El job `deploy` corre en un **runner autohospedado (self-hosted) instalado directamente en la VM**, no en un runner de GitHub. Con un runner autohospedado, el job corre localmente en la VM: no hace falta abrir el puerto 22 a GitHub ni manejar llaves SSH en absoluto.

### Configuración única en la VM

1. Crear un usuario dedicado para este runner, solo en el grupo `docker`:

   ```bash
   sudo adduser --disabled-password --gecos "" gha-website
   sudo passwd -l gha-website
   sudo usermod -aG docker gha-website
   ```

2. Registrar el runner para este repositorio: en GitHub, ir a Settings → Actions → Runners → New self-hosted runner → Linux, X64. Copiar los comandos que GitHub genera ahí (incluyen un token de registro temporal) y correrlos en la VM como `gha-website`:

   ```bash
   sudo -iu gha-website
   mkdir -p ~/actions-runner && cd ~/actions-runner

   # Correr los comandos que la página de GitHub muestra para Linux x64
   ```

3. Instalar el runner como servicio, para que sobreviva reinicios de la VM:

   ```bash
   sudo ./svc.sh install gha-website
   sudo ./svc.sh start
   ```

4. Confirmar en GitHub (Settings → Actions → Runners) que el runner aparece en línea antes de disparar un deploy.

### Cómo funciona el deploy

El job `deploy` hace checkout del código directamente en la VM, escribe un `.env` a partir de los secretos requeridos, construye la imagen con `docker build`, y reinicia el contenedor con `docker compose -f docker-compose.prod.yml up -d`. `docker image prune -f` al final evita que las imágenes viejas se acumulen en disco.

## Desplegar en Render

Render construye la imagen directamente desde el [Dockerfile](Dockerfile) i.e. no lee `docker-compose.prod.yml`. Al crear el Web Service:

- **Language**: Docker
- **Docker Command** (en Advanced): `sh scripts/start-prod.sh`
- **Variables de entorno**: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`, y `ALLOWED_HOSTS` (este último hay que agregarlo _después_ de crear el servicio, una vez que Render asigna el dominio `*.onrender.com` — de lo contrario todas las peticiones se rechazan con `DisallowedHost`).
