#!/bin/sh
set -e

echo "Aplicando migrações do banco..."
alembic upgrade head

echo "Garantindo a imobiliária de demonstração (seed é idempotente)..."
python -m app.services.seed

echo "Subindo o servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2 --proxy-headers --forwarded-allow-ips="*"
