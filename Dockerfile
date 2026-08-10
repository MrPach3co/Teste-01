# Build a partir da raiz do repositório (backend/ + frontend/ juntos —
# o backend serve o frontend estático, então os dois precisam estar na
# mesma imagem).

FROM python:3.11-slim

WORKDIR /app

# libpq-dev/gcc são necessários para compilar o driver do Postgres (psycopg2).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

WORKDIR /app/backend
RUN chmod +x entrypoint.sh

# Roda como usuário sem privilégios — nunca como root dentro do container.
RUN useradd --create-home --shell /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["./entrypoint.sh"]
