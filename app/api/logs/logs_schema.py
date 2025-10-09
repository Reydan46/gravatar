from typing import Optional, List

from pydantic import BaseModel, Field


class AuthData(BaseModel):
    """
    Данные для аутентификации

    :param username: Имя пользователя
    :param password: Пароль
    """

    username: str = Field(..., description="Имя пользователя")
    password: str = Field(..., description="Пароль")


class LogEntry(BaseModel):
    """
    Запись лога системы

    :param asctime: Дата и время записи лога
    :param msecs: Миллисекунды времени записи
    :param message: Текст сообщения лога
    :param module: Название модуля
    :param funcName: Название функции
    :param process: ID процесса
    :param levelname: Название уровня логирования
    """

    asctime: str = Field(..., description="Дата и время записи лога")
    msecs: str = Field(..., description="Миллисекунды времени записи")
    message: str = Field(..., description="Текст сообщения лога")
    module: Optional[str] = Field(None, description="Название модуля")
    funcName: Optional[str] = Field(None, description="Название функции")
    process: Optional[str] = Field(None, description="ID процесса")
    levelname: Optional[str] = Field(None, description="Название уровня логирования")


class LogStreamResponse(BaseModel):
    """
    Ответ с потоком логов

    :param logs: Список записей логов
    """

    logs: List[LogEntry] = Field(..., description="Список записей логов")


class LogFilterParams(BaseModel):
    """
    Параметры фильтрации логов

    :param limit: Ограничение количества возвращаемых логов
    """

    limit: int = Field(1000, description="Максимальное количество записей")


class AuthResponse(BaseModel):
    """
    Ответ на запрос аутентификации

    :param status: Статус операции
    :param message: Сообщение
    """

    status: str = Field(..., description="Статус операции")
    message: str = Field(..., description="Сообщение")


class TokenResponse(BaseModel):
    """
    Ответ с данными о токене

    :param status: Статус операции
    :param message: Сообщение
    """

    status: str = Field(..., description="Статус операции")
    message: str = Field(..., description="Сообщение")
