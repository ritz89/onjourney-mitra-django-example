.PHONY: setup dev test check

setup:
	uv sync --frozen
	uv run python manage.py migrate

dev:
	uv run python manage.py runserver 127.0.0.1:8000

test:
	uv run pytest -q

check:
	uv run pytest -q
	uv run ruff check .
	uv run python manage.py check
