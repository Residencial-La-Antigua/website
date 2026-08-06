#!/bin/sh
set -e

uv run manage.py collectstatic --noinput
uv run manage.py migrate
exec uv run gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 3
