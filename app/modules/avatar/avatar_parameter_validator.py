from typing import Dict

from config.constants import (
    AVATAR_DEFAULT_SIZE,
    AVATAR_HASH_CHARS,
    AVATAR_HASH_LENGTHS,
)


def validate_hash(hash_value: str) -> bool:
    """
    Проверяет, является ли строка валидным MD5 или SHA256 хешем.

    :param hash_value: Строка для проверки.
    :return: True, если хеш валиден, иначе False.
    """
    hash_len = len(hash_value)
    if hash_len not in AVATAR_HASH_LENGTHS.values():
        return False
    return all(c in AVATAR_HASH_CHARS for c in hash_value)


def parse_and_validate_params(params: Dict) -> Dict:
    """
    Нормализует и валидирует параметры запроса аватара.
    Работает с унифицированными именами полей из модели AvatarParams.

    :param params: Словарь с параметрами из HTTP-запроса.
    :return: Очищенный словарь с параметрами.
    """
    validated = {}
    if params.get("size"):
        validated["size"] = params["size"]
    else:
        validated["size"] = AVATAR_DEFAULT_SIZE

    if params.get("default"):
        validated["default"] = params["default"]

    if params.get("forcedefault"):
        validated["forcedefault"] = params["forcedefault"]

    if params.get("rating"):
        validated["rating"] = params["rating"]

    if params.get("originalsize"):
        validated["originalsize"] = params["originalsize"]

    return validated
