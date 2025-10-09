import logging
import sys

import uvicorn

from config.constants import LOG_CONFIG
from config.settings import settings

logger = logging.getLogger(LOG_CONFIG['main_logger_name'] + ".dev")


def run_fastapi_server() -> None:
    """
    Запускает основной FastAPI сервер через uvicorn

    :return: None
    """
    try:
        # noinspection PyPackageRequirements
        import uvloop
        logger.info("Event loop: uvloop enabled (high performance mode)")
        has_uvloop = True
    except ImportError:
        if sys.platform == "win32":
            logger.info("Event loop: standard asyncio (uvloop not available on Windows)")
        else:
            logger.info("Event loop: standard asyncio (uvloop not installed)")
        has_uvloop = False

    uvicorn.run(
        app="app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        workers=settings.app_workers,
        proxy_headers=True,
        forwarded_allow_ips="*",
        access_log=False,
        loop="uvloop" if has_uvloop else "asyncio",
        lifespan="on",
        reload=settings.app_reload,
    )