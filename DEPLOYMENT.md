# Ambiente de Producción

## Configurar variables de entorno

[config/settings.py](config/settings.py) lee `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS` de variables de entorno. Ninguna es necesaria para desarrollo local (todas tienen valores por defecto seguros para ese caso: `SECRET_KEY` cae a una llave insegura de desarrollo, `DEBUG` a `True`, `ALLOWED_HOSTS` a vacío — Django permite `localhost`/`127.0.0.1` automáticamente cuando `DEBUG=True`, sin importar `ALLOWED_HOSTS`).

En producción hay que establecer las tres:

```bash
SECRET_KEY="<clave larga y aleatoria>"
DEBUG="False"
ALLOWED_HOSTS="ejemplo.com,www.ejemplo.com"
```
