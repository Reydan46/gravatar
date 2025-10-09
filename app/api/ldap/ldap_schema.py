from pydantic import BaseModel, Field

from api.crypto.crypto_schema import HybridEncryptedData


class LdapCheckRequest(HybridEncryptedData):
    """
    Схема для запроса проверки подключения к LDAP.
    Наследуется от HybridEncryptedData для поддержки шифрования.
    """
    pass


class LdapCheckResponse(BaseModel):
    """
    Схема для ответа о статусе подключения к LDAP.

    :param success: True, если подключение успешно.
    :param message: Сообщение о результате.
    """
    success: bool = Field(..., description="Статус успешности подключения")
    message: str = Field(..., description="Сообщение о результате")
