# Cómo contribuir con este proyecto

## Ejecutar con Docker

```bash
docker compose up --build
```

El sitio quedará disponible en http://localhost:8000.

## Migraciones

- `docker compose up` ejecuta `migrate` automáticamente al iniciar el contenedor, así que las migraciones existentes se aplican solas.
- Si corres el proyecto directo en el host (`uv run manage.py runserver`, sin Docker), `migrate` no es automático: hay que correrlo a mano después de traer cambios que incluyan migraciones nuevas.
- `makemigrations` nunca es automático. Cada vez que se modifique un modelo hay que generar el archivo de migración a mano y commitearlo:

```bash
uv run manage.py makemigrations
uv run manage.py migrate
```

## Autenticación

Las cuentas de vecinos se registran en `/accounts/signup/` pero quedan inactivas (`is_active=False`) hasta que un administrador las aprueba desde `/admin/` (acción "Aprobar cuentas seleccionadas" sobre el modelo Usuario).

Para crear un administrador local:

```bash
uv run manage.py createsuperuser
```

... o dentro de Docker:

```
docker compose exec web uv run manage.py createsuperuser
```

## Formato de código

- **Python:** [Ruff](https://docs.astral.sh/ruff/) (instalado como dependencia de desarrollo). Corre:

  ```bash
  uv run ruff format .
  uv run ruff check .
  ```

- **HTML/CSS/JS:** [Prettier](https://prettier.io/). El repo trae `.prettierrc` con la configuración compartida; basta con tener la extensión de Prettier del editor activada (o correr `npx prettier --write .` si prefieres la CLI). Por ahora esto no está forzado automáticamente (sin pre-commit hook ni CI) — depende de que cada quien lo corra o tenga formato-al-guardar activado.
  - **Los templates de Django (`templates/**/_.html`, `accounts/templates/\*\*/_.html`) están excluidos vía `.prettierignore`.** El parser HTML de Prettier no entiende las etiquetas `{% %}` de Django y puede partirlas en dos líneas cuando son largas y eso rompe el parser de templates de Django. Si en algún momento se quiere formatear estos archivos, hace falta un plugin de Prettier que entienda templates de Django/Jinja, no el parser HTML plano.

## Tecnología (Tech Stack)

- **Backend:** Django

## TODO

### Antes de producción

- [ ] Migrar de SQLite a Postgres (u otra base de datos apta para producción) configurable por variable de entorno (actualmente hardcodeada a SQLite en [config/settings.py](config/settings.py)).
