import logging
import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from config.constants import LOG_CONFIG
from modules.logs.logs_handler import initialize_log_handler, stop_log_handler
from shared_memory.shm_auth import initialize_auth_shm, cleanup_auth_shm
from shared_memory.shm_boot_time import (
    initialize_boot_time_shm,
    cleanup_boot_time_shm,
    set_boot_time,
)
from shared_memory.shm_crypto import initialize_crypto_shm, cleanup_crypto_shm
from shared_memory.shm_logs import initialize_logs_shm, cleanup_logs_shm
from shared_memory.shm_logs_counter import (
    initialize_logs_counter_shm,
    cleanup_logs_counter_shm,
)
from shared_memory.shm_pids import log_pids, initialize_pids_shm, cleanup_pids_shm
from shared_memory.shm_settings import initialize_settings_shm, cleanup_settings_shm
from shared_memory.shm_shutdown import (
    initialize_shutdown_shm,
    set_shutdown_flag,
    cleanup_shutdown_shm,
)
from utils.http_client import http_client_wrapper

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Асинхронный менеджер контекста для управления жизненным циклом приложения FastAPI
    Инициализирует и освобождает ресурсы, такие как shared memory и HTTP-клиент

    :param app: Экземпляр приложения FastAPI
    """
    http_client_wrapper.client = httpx.AsyncClient()

    shm_boot_time, is_creator_boot_time = initialize_boot_time_shm()
    shm_shutdown, is_creator_shutdown = initialize_shutdown_shm()
    shm_logs_counter, is_creator_logs_counter = initialize_logs_counter_shm()
    shm_logs, is_creator_logs = initialize_logs_shm()
    shm_settings, is_creator_settings = initialize_settings_shm()
    shm_crypto, is_creator_crypto = initialize_crypto_shm()
    shm_auth_attempts, is_creator_auth_attempts = initialize_auth_shm()
    shm_pids, is_creator_pids = initialize_pids_shm()

    initialize_log_handler()

    if is_creator_boot_time:
        set_boot_time(shm_boot_time, time.time())

    await log_pids(shm_pids)

    yield

    stop_log_handler()

    set_shutdown_flag(shm_shutdown, True)

    if http_client_wrapper.client:
        await http_client_wrapper.client.aclose()

    cleanup_pids_shm(shm_pids, is_creator_pids)
    cleanup_auth_shm(shm_auth_attempts, is_creator_auth_attempts)
    cleanup_crypto_shm(shm_crypto, is_creator_crypto)
    cleanup_settings_shm(shm_settings, is_creator_settings)
    cleanup_logs_shm(shm_logs, is_creator_logs)
    cleanup_logs_counter_shm(shm_logs_counter, is_creator_logs_counter)
    cleanup_shutdown_shm(shm_shutdown, is_creator_shutdown)
    cleanup_boot_time_shm(shm_boot_time, is_creator_boot_time)

    logger.info(f"Process stopped [{os.getpid()}]")
