#!/bin/sh
set -e

# Если первый аргумент - "hash_password", то запускаем утилиту для хеширования
if [ "$1" = "hash_password" ]; then
    # Запускаем скрипт хеширования пароля в интерактивном режиме
    python /app/utils/password_utils.py
    exit 0
fi

# ==============================================================================
# Динамическое определение IP-адреса шлюза Docker для автоматического
# добавления в доверенные прокси.
# ==============================================================================
DOCKER_GATEWAY_IP=$(ip route | awk '/default/ {print $3}')

if [ -n "$DOCKER_GATEWAY_IP" ]; then
    echo "Docker gateway IP detected: ${DOCKER_GATEWAY_IP}"

    if [ -n "$TRUSTED_PROXY_IPS" ]; then
        export TRUSTED_PROXY_IPS="${TRUSTED_PROXY_IPS},${DOCKER_GATEWAY_IP}"
    fi
else
    echo "Warning: Could not detect Docker gateway IP."
fi


# ==============================================================================
# Конфигурация Nginx
# ==============================================================================
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
if [ "$APP_RELOAD" = "True" ]; then
    echo "Auto-reload on code change:            Enabled"
fi
if [ -n "$TRUSTED_PROXY_IPS" ]; then
    echo "Trusted proxy IPs set to:              ${TRUSTED_PROXY_IPS}"
fi
echo "----------------------------------------------------"
echo "Starting supervisor..."

exec env PYTHONWARNINGS="ignore:pkg_resources is deprecated,ignore:resource_tracker" \
    /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf