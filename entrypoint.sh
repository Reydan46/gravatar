#!/bin/sh
set -e

if [ -f /defaults.env ]; then
    echo "Loading default settings from /defaults.env"
    while IFS='=' read -r key value; do
        key=$(echo "$key" | sed 's/#.*//' | xargs)
        if [ -n "$key" ]; then
            if ! (set | grep -q "^$key="); then
                export "$key=$value"
            fi
        fi
    done < /defaults.env
fi

# Если первый аргумент - "hash_password", то запускаем утилиту для хеширования
if [ "$1" = "hash_password" ]; then
    exec python /app/utils/password_utils.py
fi

# ==============================================================================
# Динамическое определение IP-адреса шлюза Docker
# ==============================================================================
case "${TRUST_DOCKER_GATEWAY}" in
    [Tt][Rr][Uu][Ee])
        if [ "$TRUSTED_PROXY_IPS" != "*" ]; then
            DOCKER_GATEWAY_IP=$(ip route | awk '/default/ {print $3}')

            if [ -n "$DOCKER_GATEWAY_IP" ]; then
                echo "Docker gateway IP detected: ${DOCKER_GATEWAY_IP}"
                if ! echo ",${TRUSTED_PROXY_IPS}," | grep -q ",${DOCKER_GATEWAY_IP},"; then
                    if [ -z "$TRUSTED_PROXY_IPS" ]; then
                        export TRUSTED_PROXY_IPS="${DOCKER_GATEWAY_IP}"
                    else
                        export TRUSTED_PROXY_IPS="${TRUSTED_PROXY_IPS},${DOCKER_GATEWAY_IP}"
                    fi
                else
                    echo "Docker gateway IP is already in TRUSTED_PROXY_IPS."
                fi
            else
                echo "Warning: Could not detect Docker gateway IP. TRUSTED_PROXY_IPS remains unchanged."
            fi
        fi
        ;;
esac


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

# ==============================================================================
# Вывод итоговой конфигурации
# ==============================================================================
ACTUAL_PYTHON_VERSION=$(python3 -V 2>&1 | cut -d " " -f 2)

echo "----------------------------------------------------"
echo "Starting container with the following settings:"
echo "----------------------------------------------------"
echo "PYTHON_VERSION:                ${PYTHON_VERSION:-<not set>} (${ACTUAL_PYTHON_VERSION})"
echo "TZ:                            ${TZ:-<not set>}"
echo "SHOW_DEBUG_LOGS:               ${SHOW_DEBUG_LOGS:-<not set>}"
echo ""
echo "APP_HOST:                      ${APP_HOST:-<not set>}"
echo "APP_PORT:                      ${APP_PORT:-<not set>}"
echo "NGINX_PORT:                    ${NGINX_PORT:-<not set>} (${PROTOCOL})"
echo ""
echo "APP_WORKERS:                   ${APP_WORKERS:-<not set>}"
echo "APP_RELOAD:                    ${APP_RELOAD:-<not set>}"
echo ""
echo "CORS_ALLOW_ORIGINS:            ${CORS_ALLOW_ORIGINS:-<empty>}"
echo "ALLOWED_HOSTS:                 ${ALLOWED_HOSTS:-<empty>}"
echo "TRUSTED_PROXY_IPS:             ${TRUSTED_PROXY_IPS:-<empty>}"
echo "PROXY_MIDDLEWARE_IGNORE_IPS:   ${PROXY_MIDDLEWARE_IGNORE_IPS:-<empty>}"
echo "TRUST_DOCKER_GATEWAY:          ${TRUST_DOCKER_GATEWAY:-<empty>}"
echo "----------------------------------------------------"
echo "Starting supervisor..."

exec env PYTHONWARNINGS="ignore:pkg_resources is deprecated,ignore:resource_tracker" \
    /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
