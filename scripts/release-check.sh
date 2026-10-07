#!/usr/bin/env bash
set -euo pipefail

docker compose config --quiet
docker compose build backend worker frontend
docker compose up -d postgres redis backend worker frontend
./scripts/smoke-test.sh

echo "Release check passed: images built, services are healthy, and the worker is reachable."
