.PHONY: check backend-check frontend-check integration up down smoke

check: backend-check frontend-check

backend-check:
	cd backend && uv sync --frozen
	cd backend && uv run ruff check . ../scripts
	cd backend && uv run ruff format --check . ../scripts
	cd backend && uv run pytest -m 'not integration'

frontend-check:
	cd frontend && bun install --frozen-lockfile
	cd frontend && bun run check
	cd frontend && bun run lint
	cd frontend && bun run format:check
	cd frontend && bun run build

integration:
	cd backend && uv run pytest -m integration -v

up:
	docker compose up --build -d

down:
	docker compose down

smoke:
	uv run --python 3.12 --with playwright python scripts/browser_smoke.py
