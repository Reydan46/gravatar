import logging
import os
from datetime import datetime

from config.constants import LEVEL_TO_SHORT, LOG_CONFIG
from shared_memory.shm_logs import add_log_to_shm
from utils.session_context import get_session_id


class LogHandler(logging.Handler):
    """
    Обработчик логов для перехвата сообщений из стандартного логгера

    :param record: Запись лога для обработки
    """

    def emit(self, record: logging.LogRecord):
        try:
            # Получаем время в нужном формате
            dt = datetime.fromtimestamp(record.created)
            asctime = dt.strftime(LOG_CONFIG["in_console_format_datetime"])
            msecs = f"{int(record.msecs):03d}"
            levelname = LEVEL_TO_SHORT.get(record.levelno, record.levelname)

            # Получаем session_id из атрибута записи (установленного фильтром),
            # или напрямую из контекста как запасной вариант.
            session_id = getattr(record, "session_id", get_session_id())

            # Создаем запись с отдельными компонентами
            log_entry = {
                "asctime": asctime,
                "msecs": msecs,
                "message": record.getMessage(),
                "module": record.module,
                "funcName": record.funcName,
                "process": str(record.process),
                "session_id": session_id,
                "levelname": levelname,
            }

            # Добавляем лог в shared memory
            add_log_to_shm(log_entry)
        except Exception:
            self.handleError(record)


def initialize_log_handler():
    """
    Инициализирует обработчик логов и добавляет его в логгеры
    """
    # Remove any existing LogHandler instances to avoid duplicates
    root_logger = logging.getLogger()  # Get the root logger
    for handler in root_logger.handlers[:]:
        if isinstance(handler, LogHandler):
            root_logger.removeHandler(handler)

    # Создаем новый обработчик и добавляем его в корневой логгер
    log_handler = LogHandler()
    log_handler.setLevel(
        logging.DEBUG
    )  # Устанавливаем самый низкий уровень, чтобы ловить все сообщения
    root_logger.addHandler(log_handler)

    # Generate a test log to ensure the handler is working
    logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
    logger.info(f"Log handler initialized [{os.getpid()}]")


def stop_log_handler():
    """
    Останавливает обработчик логов и удаляет его из логгеров
    """
    root_logger = logging.getLogger()  # Get the root logger
    for handler in root_logger.handlers[:]:
        if isinstance(handler, LogHandler):
            root_logger.removeHandler(handler)

    logger = logging.getLogger(LOG_CONFIG["main_logger_name"])
    logger.info(f"Log handler stopped [{os.getpid()}]")
