#!/bin/sh
set -e

echo "Configuring Nginx..."

SSL_CONF_FOUND=""
if ls /etc/nginx/conf.d/*ssl*.conf > /dev/null 2>&1; then
    SSL_CONF_FOUND=" ssl"
    export "PROTOCOL=https"
else
    export "PROTOCOL=http"
fi

sed -i "s/NGINX_PORT/$NGINX_PORT$SSL_CONF_FOUND/g; s/APP_PORT/$APP_PORT/g" /etc/nginx/nginx.conf

echo "Nginx configured."
