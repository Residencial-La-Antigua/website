# Cómo contribuir con este proyecto

## Ejecutar con Docker

```bash
docker compose up --build
```

El sitio quedará disponible en http://localhost:8000.

## Tecnología (Tech Stack)

- **Backend:** Django

## TODO

### Antes de producción

- [ ] Mover `SECRET_KEY` a una variable de entorno (actualmente hardcodeada en [config/settings.py](config/settings.py)).
- [ ] Establecer `DEBUG = False` mediante variable de entorno (actualmente `True` en [config/settings.py](config/settings.py)).
