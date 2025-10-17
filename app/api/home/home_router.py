from fastapi import APIRouter, HTTPException
from starlette.responses import RedirectResponse
from starlette.status import HTTP_404_NOT_FOUND

from config.constants import URL_PAGE_HOME
from config.settings import settings

home_router = APIRouter()


@home_router.get("/")
async def root():
    """
    Корневой маршрут приложения.
    - Если `ENABLE_ROOT_REDIRECT` установлен в `True` (по умолчанию),
      перенаправляет на домашнюю страницу.
    - В противном случае, возвращает 404 Not Found.

    :return: RedirectResponse или вызывает HTTPException.
    """
    if settings.enable_root_redirect:
        return RedirectResponse(url=URL_PAGE_HOME)
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Not Found")
