# Cómo contribuir con este proyecto

## Ejecutar con Docker

```bash
docker compose up --build
```

El sitio quedará disponible en http://localhost:8000.

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

## Tecnología (Tech Stack)

- **Backend:** Django

## TODO

### Antes de producción

- [ ] Mover `SECRET_KEY` a una variable de entorno (actualmente hardcodeada en [config/settings.py](config/settings.py)).
- [ ] Establecer `DEBUG = False` mediante variable de entorno (actualmente `True` en [config/settings.py](config/settings.py)).
