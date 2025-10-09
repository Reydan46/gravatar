import logging

from config.constants import LOG_CONFIG
from config.settings import settings
from utils.logger_setup import setup_logging

logger = setup_logging(LOG_CONFIG["main_logger_name"])

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from api.auth.auth_router import auth_router
from api.avatar.avatar_router import avatar_router
from api.conf.conf_router import conf_router
from api.crypto.crypto_router import crypto_router
from api.gallery.gallery_router import gallery_router
from api.health.health_router import health_router
from api.ldap.ldap_router import ldap_router
from api.logs.logs_router import logs_router
from api.saml.saml_router import saml_router
from middleware.cors_logging_middleware import LoggingCORSMiddleware
from middleware.logger_middleware import RequestLoggingMiddleware
from middleware.protect_middleware import HostAllowMiddleware
from middleware.proxy_middleware import ProxyMiddleware
from utils.lifespan_utils import lifespan
from utils.session_context import SessionIdFilter

session_filter = SessionIdFilter()

for uvicorn_logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
    uvicorn_logger = logging.getLogger(uvicorn_logger_name)
    uvicorn_logger.filters.clear()
    for handler in uvicorn_logger.handlers:
        handler.setFormatter(logger.handlers[0].formatter)
        handler.addFilter(session_filter)

app = FastAPI(
    title="Gravatar API",
    description="Прокси-сервис для работы с различными LLM API",
    version="2.0.0",
    lifespan=lifespan,
)



app.add_middleware(
    LoggingCORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# noinspection PyTypeChecker
app.add_middleware(HostAllowMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ProxyMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(avatar_router)
app.include_router(conf_router)
app.include_router(crypto_router)
app.include_router(gallery_router)
app.include_router(health_router)
app.include_router(ldap_router)
app.include_router(logs_router)
app.include_router(saml_router)
