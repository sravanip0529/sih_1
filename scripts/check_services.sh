#!/usr/bin/env sh
set -eu

printf '%s\n' "Checking FastAPI basic health..."
curl --fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 1 http://localhost:8000/health
printf '\n%s\n' "Checking FastAPI detailed health..."
curl --fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 1 http://localhost:8000/health/detailed
printf '\n%s\n' "Checking Qdrant..."
curl --fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 1 http://localhost:6333/healthz
printf '\n%s\n' "Checking PostgreSQL..."
docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-satellite}" -d "${POSTGRES_DB:-satellite}"
printf '%s\n' "Checking frontend..."
curl --fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 1 http://localhost:5173/ >/dev/null
printf '%s\n' "Service checks complete."