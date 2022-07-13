#! /usr/bin/env bash
set -e

/uwsgi-nginx-entrypoint.sh

# Get the listen port for Nginx, default to 80
USE_LISTEN_PORT=${LISTEN_PORT:-8080}

if [ -f /app/app.conf ]; then
    cp /app/app.conf /etc/nginx/conf.d/nginx.conf
else
    printf "" > /etc/nginx/conf.d/nginx.conf
fi

exec "$@"
