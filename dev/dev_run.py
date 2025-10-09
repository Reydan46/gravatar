import multiprocessing

from config.constants import LOG_CONFIG
from dev.fastapi_service import run_fastapi_server
from dev.proxy_service import run_proxy_server
from utils.logger_setup import setup_logging

logger = setup_logging(LOG_CONFIG['main_logger_name'] + ".dev")


def main() -> None:
    """
    Запуск в режиме разработки: стартует FastAPI и прокси с SSL

    :return: None
    """
    proxy_proc = multiprocessing.Process(target=run_proxy_server)
    proxy_proc.start()
    logger.info("Proxy server started as process")
    try:
        run_fastapi_server()
    finally:
        logger.info("Shutting down proxy process...")
        if proxy_proc.is_alive():
            proxy_proc.terminate()
        proxy_proc.join()


if __name__ == "__main__":
    main()
