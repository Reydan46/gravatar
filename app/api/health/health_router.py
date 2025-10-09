from typing import Dict

from fastapi import APIRouter

health_router = APIRouter(prefix="/health", tags=["Health"])


@health_router.get("", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """
    Проверяет доступность и работоспособность сервиса

    Используется для мониторинга состояния приложения и автоматических проверок
    Возвращает статус работоспособности системы

    :return: Статус доступности сервиса в формате ключ-значение
    """
    return {"status": "OK"}
