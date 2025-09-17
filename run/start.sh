#!/usr/bin/env sh
set -eu
: "${HTTP_HOST:?ERROR: HTTP_HOST is required}"
: "${HTTP_PORT:?ERROR: HTTP_PORT is required}"

exec uvicorn app.main:app --host "$HTTP_HOST" --port "$HTTP_PORT" --no-access-log