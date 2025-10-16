from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

from config.constants import URL_PAGE_HOME

home_router: APIRouter = APIRouter()


@home_router.get("/", include_in_schema=False)
async def redirect_to_auth(request: Request) -> RedirectResponse:
    """
    Перенаправляет пользователя с корневого URL на страницу аутентификации.

    Этот обработчик является точкой входа в приложение и направляет
    пользователей на страницу входа.

    :param request: Объект HTTP-запроса.
    :return: Ответ с перенаправлением на страницу /auth.
    """
    return RedirectResponse(url=URL_PAGE_HOME)