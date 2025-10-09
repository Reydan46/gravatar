import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from starlette.datastructures import Headers

from config.constants import FINGERPRINT_HEADERS


def generate_fingerprint(headers: Headers) -> str:
    """
    Генерирует fingerprint-строку на основе заголовков

    :param headers: Заголовки
    :return: Строка fingerprint (sha256 hex)
    """
    fingerprint_elements = [headers.get(header, "") for header in FINGERPRINT_HEADERS]
    fingerprint_str = "|".join(fingerprint_elements)
    return hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()


def encrypt_data_with_fingerprint(headers: Headers, data: dict) -> str:
    """
    Шифрует данные с помощью fingerprint, полученного из headers

    :param headers: Заголовки
    :param data: Словарь с данными для шифрования
    :return: Строка вида ciphertext_hex:nonce_hex
    """
    fingerprint = generate_fingerprint(headers)
    key = bytes.fromhex(fingerprint)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(data, separators=(",", ":")).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return f"{ciphertext.hex()}:{nonce.hex()}"


def decrypt_data_with_fingerprint(fingerprint: str, enc_data: str) -> dict | None:
    """
    Расшифровывает строку, используя fingerprint

    :param fingerprint: fingerprint-строка (sha256 hex)
    :param enc_data: Строка вида ciphertext_hex:nonce_hex
    :return: Десериализованный словарь или None, если не удалось расшифровать
    """
    try:
        ciphertext_hex, nonce_hex = enc_data.split(":")
        key = bytes.fromhex(fingerprint)
        aesgcm = AESGCM(key)
        ciphertext = bytes.fromhex(ciphertext_hex)
        nonce = bytes.fromhex(nonce_hex)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))
    except Exception:
        return None
