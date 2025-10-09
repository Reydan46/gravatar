import asyncio
import inspect
import json
import logging
import os
import time
from asyncio import CancelledError
from collections import deque
from datetime import datetime
from typing import AsyncGenerator, Dict, List
from uuid import uuid4

from config.constants import (
    LOGS_ACTIVITY_TIMEOUT,
    LOGS_FAST_CHECK_INTERVAL,
    LOGS_KEEPALIVE_INTERVAL,
    LOGS_SLOW_CHECK_INTERVAL,
    LOG_CONFIG,
    SHARED_MEMORY_CONFIG,
)
from config.settings import settings
from modules.auth.auth_permissions import has_permission
from modules.logs.logs_formatter import create_log_entry
from shared_memory.shm_logs import get_logs_from_shm
from shared_memory.shm_logs_counter import get_logs_counter, initialize_logs_counter_shm
from shared_memory.shm_shutdown import get_shutdown_flag, initialize_shutdown_shm

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])

client_data: Dict[str, Dict] = {}


def debug_log(session_id: str, message: str) -> None:
    """
    Логирование отладочной информации для сервиса логов.

    :param session_id: Идентификатор сессии стрима логов.
    :param message: Сообщение для логирования.
    """
    if settings.show_debug_logs:
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S.%f")[:-3]
        print(f"DEBUG: [{timestamp}][{os.getpid()}][{session_id}]: {message}")


def create_client_data(session_id: str) -> None:
    """
    Создает структуру данных для нового клиента

    :param session_id: Идентификатор сессии
    """
    max_buffer_size = SHARED_MEMORY_CONFIG["logs"]["MAX_BUFFER_SIZE"]
    client_data[session_id] = {"buffer": deque(maxlen=max_buffer_size), "counter": 0}


def add_logs_to_client_buffer(session_id: str, logs: List[Dict]) -> None:
    """
    Добавляет логи в буфер клиента

    :param session_id: Идентификатор сессии
    :param logs: Список логов для добавления
    """
    for log_entry in logs:
        client_data[session_id]["buffer"].append(
            json.dumps({k: v for k, v in log_entry.items() if k != "levelname"})
        )
    if logs:
        debug_log(session_id, f"Added {len(logs)} logs to buffer")


def get_new_logs(session_id: str, current_logs: List[Dict]) -> List[Dict]:
    """
    Получает новые логи, которых еще нет в буфере клиента

    :param session_id: Идентификатор сессии
    :param current_logs: Текущие логи из shared memory
    :return: Список новых логов
    """
    new_logs = []
    buffer = client_data[session_id]["buffer"]
    for log in current_logs:
        log_json = json.dumps({k: v for k, v in log.items() if k != "levelname"})
        if log_json not in buffer:
            new_logs.append(log)
    if new_logs:
        debug_log(session_id, f"Found {len(new_logs)} new logs")
        add_logs_to_client_buffer(session_id, new_logs)
    return new_logs


async def send_logs(session_id: str, logs: List[Dict]) -> AsyncGenerator[bytes, None]:
    """
    Отправляет логи клиенту

    :param session_id: Идентификатор сессии
    :param logs: Список логов для отправки
    :return: Генератор с закодированными логами
    """
    for log_entry in logs:
        yield f"data: {json.dumps(log_entry)}\n\n".encode("utf-8")
    debug_log(session_id, f"Sended {len(logs)} logs")


async def send_message(session_id: str, message: str) -> AsyncGenerator[bytes, None]:
    """
    Отправляет сообщение клиенту

    :param session_id: Идентификатор сессии
    :param message: Сообщение для отправки
    :return: Генератор с закодированным сообщением
    """
    log_message = create_log_entry(
        message, inspect.currentframe().f_code.co_name, add_to_memory=False
    )
    if log_message:
        yield f"data: {json.dumps(log_message)}\n\n".encode("utf-8")
    debug_log(session_id, f"Sended message: {message}")


async def send_keepalive(session_id: str) -> AsyncGenerator[bytes, None]:
    """
    Отправляет keepalive сообщение клиенту

    :param session_id: Идентификатор сессии
    :return: Генератор с закодированным keepalive сообщением
    """
    dt = datetime.now()
    asctime = dt.strftime(LOG_CONFIG["in_console_format_datetime"])
    yield b": keepalive - " + asctime.encode("utf-8") + b"\n\n"
    debug_log(session_id, "Sended keepalive message")


async def get_log_stream(
    username: str, limit: int = 1000
) -> AsyncGenerator[bytes, None]:
    """
    Генератор для потоковой передачи логов с отслеживанием счетчика в shared memory

    :param username: Имя пользователя, для проверки прав доступа
    :param limit: Количество предыдущих записей для загрузки
    :return: Поток событий с логами
    """
    session_id = str(uuid4())[:4]
    debug_log(session_id, "Started log stream")

    create_client_data(session_id)

    try:
        async for message in send_message(session_id, "--- Stream connected ---"):
            yield message

        previous_logs = get_logs_from_shm(
            SHARED_MEMORY_CONFIG["logs"]["MAX_BUFFER_SIZE"]
        )
        debug_log(session_id, f"Total previous logs available: {len(previous_logs)}")
        add_logs_to_client_buffer(session_id, previous_logs)

        debug_log(session_id, f"Sending last {limit} logs to client")
        async for log in send_logs(session_id, previous_logs[-limit:]):
            yield log

        async for message in send_message(session_id, "--- Previous logs loaded ---"):
            yield message

        last_ping_time = last_log_time = time.time()

        shm_shutdown, _ = initialize_shutdown_shm(False)
        shm_logs_counter, _ = initialize_logs_counter_shm(False)
        client_data[session_id]["counter"] = get_logs_counter(shm_logs_counter)
        while True:
            if get_shutdown_flag(shm_shutdown):
                logger.info("Received shutdown signal, stopping log stream")
                async for message in send_message(
                    session_id, "--- Stream stopped by server shutdown ---"
                ):
                    yield message
                break
            if not has_permission(username, "logs"):
                logger.warning(
                    f"Access rights revoked for user '{username}', stopping log stream"
                )
                async for message in send_message(
                    session_id, "--- Stream stopped by access rights revoked ---"
                ):
                    yield message
                break

            current_time = time.time()

            current_counter = get_logs_counter(shm_logs_counter)
            if current_counter != client_data[session_id]["counter"]:
                current_logs = get_logs_from_shm(
                    SHARED_MEMORY_CONFIG["logs"]["MAX_BUFFER_SIZE"]
                )
                new_logs = get_new_logs(session_id, current_logs)

                if new_logs:
                    async for log in send_logs(session_id, new_logs):
                        yield log
                    last_log_time = current_time
                    last_ping_time = current_time

                client_data[session_id]["counter"] = current_counter

            if current_time - last_ping_time >= LOGS_KEEPALIVE_INTERVAL:
                async for keepalive in send_keepalive(session_id):
                    yield keepalive
                last_ping_time = current_time

            passed_time = current_time - last_log_time
            if passed_time > LOGS_ACTIVITY_TIMEOUT:
                debug_log(
                    session_id,
                    f"No logs for {passed_time:.2f} sec, "
                    f"waiting for {LOGS_SLOW_CHECK_INTERVAL} sec",
                )
                await asyncio.sleep(LOGS_SLOW_CHECK_INTERVAL)
            else:
                debug_log(
                    session_id,
                    f"No logs for {passed_time:.2f} sec, "
                    f"waiting for {LOGS_FAST_CHECK_INTERVAL} sec",
                )
                await asyncio.sleep(LOGS_FAST_CHECK_INTERVAL)
    except (ConnectionResetError, BrokenPipeError, CancelledError):
        pass
    except Exception as e:
        logger.error(f"[{username}] Stream error: {type(e).__name__}: {str(e)}")
    finally:
        if session_id in client_data:
            del client_data[session_id]
        debug_log(session_id, "Ended log stream")
