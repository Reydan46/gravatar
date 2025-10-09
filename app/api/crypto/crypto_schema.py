from typing import Optional

from pydantic import BaseModel, Field


class EncryptedData(BaseModel):
    """
    Зашифрованные данные для передачи на сервер

    :param enc_data: Зашифрованные данные в формате base64
    """

    enc_data: str = Field(..., description="Зашифрованные данные")


class HybridEncryptedData(BaseModel):
    """
    Данные, зашифрованные с помощью гибридного шифрования (RSA+AES)

    :param enc_sym_data: Зашифрованное сообщение с помощью AES, закодированное в base64
    :param iv: Вектор инициализации (IV) AES, закодированный в base64
    :param enc_key: Зашифрованный публичным ключом RSA симметричный ключ AES, закодированный в base64
    """

    enc_key: str = Field(
        ..., description="Зашифрованный публичным RSA ключом AES-ключ (base64)"
    )
    iv: Optional[str] = Field(..., description="Вектор инициализации для AES (base64)")
    enc_sym_data: Optional[str] = Field(
        ..., description="Зашифрованные данные с помощью AES (base64)"
    )


class EncryptedSymmetricKey(BaseModel):
    """
    Зашифрованный публичным RSA ключом AES-ключ (base64)

    :param enc_key: Зашифрованный публичным ключом RSA симметричный ключ AES, закодированный в base64
    """

    enc_key: str = Field(
        ..., description="Зашифрованный публичным RSA ключом AES-ключ (base64)"
    )


class PrivateKeyRequest(BaseModel):
    """
    Запрос, содержащий приватный ключ для генерации сертификата.

    :param private_key: Приватный ключ в формате PEM (однострочный Base64).
    """

    private_key: str = Field(
        ..., description="Приватный ключ в формате PEM (однострочный Base64)"
    )
