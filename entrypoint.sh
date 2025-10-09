#!/bin/sh
set -e

# Если первый аргумент - hash_password
if [ "$1" = "hash_password" ]; then
    # Запускаем скрипт хеширования пароля в интерактивном режиме
    python /app/utils/password_utils.py
    exit 0
fi

# Шаблонизация nginx.conf (подставляем переменные)
SSL_CONF_FOUND=
for f in /etc/nginx/conf.d/*ssl*.conf; do
    [ -e "$f" ] && SSL_CONF_FOUND=" ssl" && break
done

sed -i "s/NGINX_PORT/$NGINX_PORT$SSL_CONF_FOUND/g; s/APP_PORT/$APP_PORT/g" /etc/nginx/nginx.conf

# Запуск обоих процессов: nginx и uvicorn
# (nginx — main process для Docker + Uvicorn в фоне)
nginx -c /etc/nginx/nginx.conf &

set --
if [ "$APP_RELOAD" = "True" ]; then
    set -- "$@" --reload
fi

export PYTHONWARNINGS="ignore:resource_tracker"

exec uvicorn main:app \
    --host "$APP_HOST" \
    --port "$APP_PORT" \
    --workers "$APP_WORKERS" \
    --no-access-log \
    --loop uvloop \
    --lifespan on \
    "$@"
