import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

import orjson
from ldap3 import ALL, AUTO_BIND_NO_TLS, Connection, Server, SUBTREE
from ldap3.core.exceptions import LDAPException

from config.constants import LOG_CONFIG
from modules.crypto.crypto_operations import decrypt_hybrid

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


@dataclass
class LdapCheckResult:
    """
    Структурированный результат проверки соединения с LDAP.

    :param success: True, если соединение успешно.
    :param message: Сообщение о результате.
    """
    success: bool
    message: str


class LdapService:
    """
    Сервис для взаимодействия с LDAP (Active Directory).
    """

    def __init__(
            self, server_url: str, username: str, password: str, search_base: str
    ):
        """
        Инициализирует сервис с заданными учетными данными.

        :param server_url: URL LDAP сервера.
        :param username: Имя пользователя для подключения.
        :param password: Пароль для подключения.
        :param search_base: База для поиска пользователей.
        """
        self.server_url = server_url
        self.username = username
        self.password = password
        self.search_base = search_base
        self.server = Server(self.server_url, get_info=ALL)
        self.conn: Optional[Connection] = None

    def _connect(self) -> None:
        """
        Устанавливает соединение с LDAP сервером.

        :raises LDAPException: В случае ошибки подключения.
        """
        if self.conn and self.conn.bound:
            return
        try:
            self.conn = Connection(
                self.server,
                self.username,
                self.password,
                auto_bind=AUTO_BIND_NO_TLS,
                raise_exceptions=True,
            )
            logger.info(f"Successfully connected to LDAP server: {self.server_url}")
        except LDAPException as e:
            logger.error(f"Failed to connect to LDAP server: {e}")
            raise

    def unbind(self) -> None:
        """
        Закрывает соединение с LDAP, если оно было установлено.
        """
        if self.conn and self.conn.bound:
            self.conn.unbind()
            logger.info("LDAP connection closed.")

    def test_connection(self) -> bool:
        """
        Проверяет соединение с LDAP сервером.

        :return: True, если соединение успешно, иначе False.
        """
        try:
            self._connect()
            # Пробуем прочитать корневой DSE, чтобы убедиться в работоспособности
            self.conn.search(
                search_base="",
                search_filter="(objectClass=*)",
                search_scope="BASE",
                attributes=["objectClass"],
            )
            return True
        except LDAPException:
            return False
        finally:
            self.unbind()

    def search_users(
            self,
            search_filter: str = "(&(objectClass=user)(thumbnailPhoto=*))",
            attributes: Optional[List[str]] = None,
    ) -> list:
        """
        Выполняет поиск пользователей в LDAP с поддержкой постраничной загрузки.

        :param search_filter: Фильтр для поиска.
        :param attributes: Список атрибутов для получения.
        :return: Список найденных записей пользователей.
        """
        self._connect()
        if attributes is None:
            attributes = [
                "sAMAccountName",
                "thumbnailPhoto",
                "mail",
                "cn",
            ]

        raw_users = []
        try:
            paging_cookie = None
            while True:
                self.conn.search(
                    search_base=self.search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=attributes,
                    paged_size=1000,
                    paged_cookie=paging_cookie,
                )
                raw_users.extend(self.conn.entries)

                # Ищем контрол пагинации в ответе сервера
                cookie_control = self.conn.result["controls"].get(
                    "1.2.840.113556.1.4.319"
                )
                if cookie_control and cookie_control.get("value"):
                    paging_cookie = cookie_control["value"]["cookie"]
                    if not paging_cookie:
                        # Если cookie пустой, это последняя страница
                        break
                else:
                    # Если контрол не найден, пагинация не поддерживается или завершена
                    break

            sorted_entries = sorted(raw_users, key=lambda e: (e.sAMAccountName.value or "").lower())
            logger.info(f"Found {len(sorted_entries)} users in LDAP.")
            return sorted_entries
        except LDAPException as e:
            logger.error(f"An error occurred during LDAP search: {e}")
            return []
        finally:
            self.unbind()


def check_connection_from_payload(payload: Dict) -> LdapCheckResult:
    """
    Выполняет полную процедуру проверки LDAP соединения из зашифрованного payload.

    :param payload: Словарь с зашифрованными данными.
    :return: Объект LdapCheckResult с результатом.
    """
    decrypted_str = decrypt_hybrid(payload)
    ldap_data = orjson.loads(decrypted_str)

    required_keys = [
        "LDAP_SERVER",
        "LDAP_USERNAME",
        "LDAP_PASSWORD",
        "LDAP_SEARCH_BASE",
    ]
    if not all(key in ldap_data for key in required_keys):
        raise ValueError("Отсутствуют обязательные учетные данные LDAP в запросе")

    service = LdapService(
        server_url=ldap_data["LDAP_SERVER"],
        username=ldap_data["LDAP_USERNAME"],
        password=ldap_data["LDAP_PASSWORD"],
        search_base=ldap_data["LDAP_SEARCH_BASE"],
    )

    is_successful = service.test_connection()

    if is_successful:
        return LdapCheckResult(success=True, message="Подключение к LDAP успешно.")

    return LdapCheckResult(
        success=False,
        message="Не удалось подключиться к LDAP. Проверьте учетные данные и доступность сервера.",
    )
