#!/bin/sh
set -e

# Если первый аргумент - "hash_password", то запускаем утилиту для хеширования
if [ "$1" = "hash_password" ]; then
    # Запускаем скрипт хеширования пароля в интерактивном режиме
    python /app/utils/password_utils.py
    exit 0
fi

SSL_CONF_FOUND=
if ls /etc/nginx/conf.d/*ssl*.conf 1>/dev/null 2>&1; then
    SSL_CONF_FOUND=" ssl"
    PROTOCOL="https"
else
    PROTOCOL="http"
fi

sed -i "s/NGINX_PORT/$NGINX_PORT$SSL_CONF_FOUND/g; s/APP_PORT/$APP_PORT/g" /etc/nginx/nginx.conf

echo "----------------------------------------------------"
echo "Nginx is configured to listen on port: ${NGINX_PORT} (${PROTOCOL})"
echo "Uvicorn will be started on port:       ${APP_PORT}"
echo "----------------------------------------------------"
echo "Starting supervisor..."

exec env PYTHONWARNINGS="ignore:pkg_resources is deprecated" \
    /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
