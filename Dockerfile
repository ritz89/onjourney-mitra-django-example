FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SQLITE_NAME=/app/data/db.sqlite3 \
    HOME=/tmp \
    UV_CACHE_DIR=/tmp/uv-cache

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.14
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev \
    && useradd --system --uid 10001 demo \
    && mkdir -p /app/data /tmp/uv-cache \
    && chown -R demo:demo /app/data /tmp/uv-cache
USER demo

EXPOSE 8000
CMD ["sh", "-c", "uv run --no-sync python manage.py migrate && uv run --no-sync python manage.py runserver 0.0.0.0:8000"]
