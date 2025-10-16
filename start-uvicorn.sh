#!/bin/sh
set -e

UVICORN_ARGS="--host ${APP_HOST:-0.0.0.0} --port ${APP_PORT:-8888} --workers ${APP_WORKERS:-1} --no-access-log --loop uvloop --lifespan on"

if [ "$APP_RELOAD" = "True" ]; then
    UVICORN_ARGS="$UVICORN_ARGS --reload"
fi

# shellcheck disable=SC2086
exec uvicorn main:app $UVICORN_ARGS
