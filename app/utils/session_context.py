import logging
from contextvars import ContextVar
from typing import Optional

session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
suppress_app_logging_var: ContextVar[bool] = ContextVar(
    "suppress_app_logging", default=False
)


def get_session_id() -> str:
    """
    Возвращает текущий ID сессии из contextvar или '----' если он не установлен.

    :return: Строка с ID сессии или значением по умолчанию.
    """
    return session_id_var.get() or "----"


class SessionIdFilter(logging.Filter):
    """
    Фильтр для добавления ID сессии в каждую запись лога.

    Извлекает ID из контекстной переменной `session_id_var` и добавляет
    его в атрибут `session_id` записи лога. Если ID отсутствует,
    используется заполнитель '----'.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Добавляет атрибут 'session_id' к записи лога.

        :param record: Объект записи лога.
        :return: True, чтобы запись всегда обрабатывалась дальше.
        """
        record.session_id = get_session_id()
        return True
