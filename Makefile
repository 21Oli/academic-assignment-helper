# Makefile — common dev commands
# Requires: docker-compose, make

.PHONY: up down build logs migrate revision test

## Start all services
up:
	docker-compose up --build

## Stop and remove containers
down:
	docker-compose down

## Build backend image only
build:
	docker-compose build backend

## Follow backend logs
logs:
	docker-compose logs -f backend

## Apply all pending Alembic migrations (run inside the backend container)
migrate:
	docker-compose exec backend alembic upgrade head

## Create a new migration (usage: make revision MSG="add column x")
revision:
	docker-compose exec backend alembic revision --autogenerate -m "$(MSG)"

## Run the test suite inside the backend container
test:
	docker-compose exec backend pytest tests/ -v

## Lint with Ruff
lint:
	ruff check backend/ tests/

## Auto-fix lint issues
lint-fix:
	ruff check --fix backend/ tests/

## Check formatting
fmt-check:
	ruff format --check backend/ tests/

## Apply formatting
fmt:
	ruff format backend/ tests/
