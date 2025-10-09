ARG PYTHON_VERSION=3.13
ARG APP_PORT=8888

FROM python:${PYTHON_VERSION}-alpine AS builder

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev libffi-dev openssl-dev

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:${PYTHON_VERSION}-alpine

ENV PYTHONUNBUFFERED=1

RUN addgroup -g 1000 -S nginx \
    && adduser -u 1000 -S -G nginx -s /sbin/nologin nginx \
    && apk add --no-cache nginx libffi openssl


COPY --from=builder /install /usr/local

RUN rm -rf /root/.cache /var/cache/apk /usr/share/doc /usr/share/man /usr/share/locale

COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /
COPY app /app

RUN chmod 644 /etc/nginx/nginx.conf \
    && chmod +x /entrypoint.sh \
    && chown -R nginx:nginx /etc/nginx /app

WORKDIR /app

EXPOSE ${APP_PORT}

USER nginx

ENTRYPOINT ["/entrypoint.sh"]