import os
from datetime import datetime

from shared_memory.shm_logs import add_log_to_shm
from utils.session_context import get_session_id


def create_log_entry(
    message: str,
    func_name: str,
    module: str = __name__.split(".")[-1],
    levelname: str = "INF",
    add_to_memory: bool = True,
) -> dict:
    """
    Создает запись лога с указанными параметрами

    :param message: Сообщение для записи
    :param module: Название модуля
    :param func_name: Имя функции
    :param levelname: Уровень логгирования
    :param add_to_memory: Добавлять ли лог в общую память
    :return: Словарь записи лога
    """
    dt = datetime.now()
    asctime = dt.strftime("%d.%m.%Y %H:%M:%S")  # Формат из конфигурации
    msecs = f"{int(dt.microsecond / 1000):03d}"

    log_entry = {
        "asctime": asctime,
        "msecs": msecs,
        "message": message,
        "module": module,
        "funcName": func_name,
        "process": str(os.getpid()),
        "session_id": get_session_id(),
        "levelname": levelname,
    }

    # Добавляем в shared memory только если это требуется
    if add_to_memory:
        add_log_to_shm(log_entry)

    return log_entry
