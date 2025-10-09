from typing import Optional

import httpx


class HttpClient:
    """
    Обертка для хранения глобального экземпляра httpx.AsyncClient

    :param client: Экземпляр клиента httpx.AsyncClient или None
    """

    client: Optional[httpx.AsyncClient] = None


http_client_wrapper = HttpClient()
