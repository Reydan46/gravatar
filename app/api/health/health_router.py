import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from shared_memory.shm_boot_time import get_boot_time

health_router = APIRouter(prefix="/health", tags=["Health"])


@health_router.get("", response_model=Dict[str, Any])
async def health_check(
    data: Optional[str] = Query(
        None,
        description="Список дополнительных данных через запятую (например, 'time')",
    )
) -> Dict[str, Any]:
    """
    Проверяет доступность и работоспособность сервиса
    Может возвращать дополнительную информацию по запросу

    Используется для мониторинга состояния приложения и автоматических проверок
    Возвращает статус работоспособности системы

    :param data: Опциональный параметр для запроса дополнительных данных
                 'time': возвращает время запуска и текущее время сервера
    :return: Статус доступности сервиса и запрошенные данные
    """
    response: Dict[str, Any] = {"status": "OK"}

    if data:
        requested_data = {item.strip() for item in data.split(",")}
        if "time" in requested_data:
            boot_timestamp = get_boot_time()
            response["boot_time"] = datetime.fromtimestamp(boot_timestamp).isoformat()
            response["current_time"] = datetime.fromtimestamp(time.time()).isoformat()

    return response
