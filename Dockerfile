# =====================================================================
# STAGE 0: Build arguments
# =====================================================================
ARG PYTHON_VERSION=3.13
ARG NODE_VERSION=24-alpine
ARG NGINX_PORT=9999
ARG PUID=1000
ARG PGID=1000
ARG APP_USER=appuser
ARG APP_GROUP=appgroup

# =====================================================================
# STAGE 1: Build Python dependencies
# =====================================================================
FROM python:${PYTHON_VERSION}-alpine AS python-dependencies
ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev libffi-dev openssl-dev

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt \
    && rm -rf /install/bin/pip*

# =====================================================================
# STAGE 2: Build and minify frontend assets
# =====================================================================
FROM node:${NODE_VERSION} AS frontend-assets
WORKDIR /build

COPY package.json gulpfile.js ./
RUN npm install

COPY app/static/css ./app/static/css
RUN npx gulp minCss

COPY app/static/js ./app/static/js
RUN npx gulp minJs

RUN echo "Frontend assets are ready."

# =====================================================================
# STAGE 3: Final production image
# =====================================================================
FROM python:${PYTHON_VERSION}-alpine AS production-image

ARG PUID
ARG PGID
ARG APP_USER
ARG APP_GROUP
ARG NGINX_PORT

ENV PYTHONUNBUFFERED=1
ENV APP_USER=${APP_USER}
ENV APP_GROUP=${APP_GROUP}

RUN addgroup -g ${PGID} -S ${APP_GROUP} \
    && adduser -u ${PUID} -S -G ${APP_GROUP} -s /sbin/nologin ${APP_USER} \
    && apk add --no-cache nginx supervisor

COPY --from=python-dependencies /install /usr/local

COPY --chown=${APP_USER}:${APP_GROUP} app /app
COPY --from=frontend-assets --chown=${APP_USER}:${APP_GROUP} /build/app/static /app/static

COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /entrypoint.sh
COPY start-uvicorn.sh /start-uvicorn.sh
COPY defaults.env /defaults.env
COPY scripts /scripts

RUN rm -rf /var/cache/apk/* \
    && mkdir -p /var/log/supervisor /run/nginx \
    && chmod 755 /entrypoint.sh /start-uvicorn.sh /scripts/commands/*.sh /scripts/pre-start/*.sh \
    && chown -R ${APP_USER}:${APP_GROUP} /app \
    && find /app/static -type d -exec chmod 755 {} + \
    && find /app/static -type f -exec chmod 644 {} + \
    && chown nginx:nginx /run/nginx && chmod 770 /run/nginx

WORKDIR /app

EXPOSE ${NGINX_PORT}

ENTRYPOINT ["/entrypoint.sh"]

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
