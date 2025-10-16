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

# ==============================================================================
# Проверяем, передан ли аргумент и существует ли для него скрипт в /scripts/commands
# ==============================================================================
if [ -n "$1" ] && [ -x "/scripts/commands/$1.sh" ]; then
    echo "Executing command: $1"
    # Используем exec, чтобы передать управление и код завершения
    exec "/scripts/commands/$1.sh"
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
# Выполнение подготовительных скриптов
# ==============================================================================
PRE_START_DIR="/scripts/pre-start"
if [ -d "$PRE_START_DIR" ]; then
    echo "Running pre-start scripts from $PRE_START_DIR..."
    for f in $(find "$PRE_START_DIR" -type f -executable | sort); do
        echo "Sourcing pre-start script: $f"
        . "$f"
    done
    echo "Pre-start scripts finished."
fi

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

echo "Starting supervisord..."
export PYTHONWARNINGS="ignore:pkg_resources is deprecated,ignore:resource_tracker"
exec "$@"
