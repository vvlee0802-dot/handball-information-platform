COMPOSE := docker compose

.PHONY: dev-up dev-down logs health seed-demo monitoring-up monitoring-down test release-check backup restore-check

dev-up:
	$(COMPOSE) up -d --build

dev-down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

health:
	./scripts/smoke-test.sh

seed-demo:
	$(COMPOSE) exec backend python -m app.scripts.seed_demo

monitoring-up:
	$(COMPOSE) --profile monitoring up -d prometheus alertmanager blackbox

monitoring-down:
	$(COMPOSE) --profile monitoring stop prometheus alertmanager blackbox

test:
	cd frontend && npm run lint:check && npm run type-check && npm run test:unit -- --run && npm run build
	cd backend && .venv/bin/ruff format --check app tests alembic && .venv/bin/ruff check app tests alembic && .venv/bin/python -m pytest -q

release-check:
	./scripts/release-check.sh

backup:
	./scripts/backup.sh

restore-check:
	@test -n "$(BACKUP)" || (echo "Usage: make restore-check BACKUP=backups/<timestamp>/database.dump" && exit 2)
	./scripts/restore-check.sh "$(BACKUP)"
