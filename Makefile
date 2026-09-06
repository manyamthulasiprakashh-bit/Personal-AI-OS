PYTHON ?= python
BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: backend-install backend-test backend-lint backend-run frontend-install frontend-run compose-up alembic-upgrade alembic-revision

backend-install:
	cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements.txt

backend-test:
	cd $(BACKEND_DIR) && pytest -q

backend-lint:
	cd $(BACKEND_DIR) && ruff check app tests

backend-run:
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-run:
	cd $(FRONTEND_DIR) && npm run dev

compose-up:
	docker compose up --build

alembic-upgrade:
	cd $(BACKEND_DIR) && alembic upgrade head

alembic-revision:
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$m"
