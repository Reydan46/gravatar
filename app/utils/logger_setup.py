import logging
import sys
from logging.handlers import RotatingFileHandler

from colorama import Back, Fore, Style, init

from config.constants import LEVEL_TO_SHORT, LOG_CONFIG
from utils.session_context import SessionIdFilter

# Инициализация colorama
init(autoreset=True)


class CustomFormatter(logging.Formatter):
    """Кастомный форматтер для сокращенных уровней логирования и цветного вывода."""

    # Инициализация переменной для использования цвета
    def __init__(self, *args, use_color=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color

    LOG_COLORS = {
        logging.DEBUG: Fore.WHITE,  # Серый
        logging.INFO: Fore.BLUE,  # Синий
        logging.WARNING: Fore.YELLOW,  # Желтый
        logging.ERROR: Fore.RED,  # Красный
        logging.CRITICAL: Fore.LIGHTWHITE_EX
        + Back.RED
        + Style.BRIGHT,  # Белый жирный текст с красным фоном
    }
    NO_COLOR = Style.RESET_ALL

    def format(self, record: logging.LogRecord) -> str:
        # Изменяем уровень логирования на сокращенную форму
        record.levelname = LEVEL_TO_SHORT.get(record.levelno, record.levelname)
        log_color = (
            self.LOG_COLORS.get(record.levelno, self.NO_COLOR) if self.use_color else ""
        )
        reset_color = self.NO_COLOR if self.use_color else ""
        message = super().format(record)
        return f"{log_color}{message}{reset_color}"


def setup_logging(
    name_logger: str = __name__, log_filename: str = None
) -> logging.Logger:
    """Инициализация и настройка логгера."""
    if log_filename is None:
        log_filename = f"{name_logger}.log"

    # Инициализация логгера
    logger = logging.getLogger(name_logger)

    # Если логгер уже был настроен - очищаем настройки
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()

    # Установка уровня логирования
    logger.setLevel(LOG_CONFIG["level"])

    # Создаем и добавляем фильтр сессии
    session_filter = SessionIdFilter()

    if LOG_CONFIG["in_console_enabled"]:
        # Настройка обработчика вывода в консоль
        c_handler = logging.StreamHandler(sys.stdout)
        c_format = CustomFormatter(
            LOG_CONFIG["in_console_format"],
            datefmt=LOG_CONFIG["in_console_format_datetime"],
            use_color=True,
        )
        c_handler.setFormatter(c_format)
        c_handler.addFilter(session_filter)
        logger.addHandler(c_handler)

    if LOG_CONFIG["in_file_enabled"]:
        # Настройка обработчика записи в файл
        f_handler = RotatingFileHandler(
            log_filename,
            maxBytes=LOG_CONFIG["max_size_file_bytes"],
            backupCount=LOG_CONFIG["backup_file_count"],
            encoding="utf-8",
        )
        f_format = CustomFormatter(
            LOG_CONFIG["in_file_format"],
            datefmt=LOG_CONFIG["in_file_format_datetime"],
            use_color=False,
        )
        f_handler.setFormatter(f_format)
        f_handler.addFilter(session_filter)
        logger.addHandler(f_handler)

    return logger
