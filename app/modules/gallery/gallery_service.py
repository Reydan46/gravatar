import hashlib
import logging
import math
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import orjson
from PIL import Image

from api.gallery.gallery_schema import AvatarInfo, PaginatedAvatarsResponse
from config.constants import (
    AVATARS_PATH,
    AVATAR_IMG_MAIL_DIR,
    AVATAR_METADATA_FILENAME,
    LOG_CONFIG,
)
from config.settings import settings
from utils.session_context import suppress_app_logging_var

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def _parse_size_filter(filter_str: str) -> Optional[Tuple[str, int]]:
    """
    Парсит строку фильтра размера в оператор и значение.
    Поддерживает форматы: >300, <300, >=300, <=300, =300, а также с оператором в конце (300>, 300<).

    :param filter_str: Строка фильтра, например, ">=100" или "100<".
    :return: Кортеж (оператор, значение) или None при ошибке.
    """
    # Регулярное выражение для поиска оператора (в начале или в конце) и числа
    match = re.match(r"^\s*([<>=]{1,2})?\s*(\d+)\s*([<>=]{1,2})?\s*$", filter_str)
    if not match:
        return None

    op_prefix, value_str, op_postfix = match.groups()

    # Недопустимый формат, если операторы с обеих сторон
    if op_prefix and op_postfix:
        return None

    operator_raw = op_prefix or op_postfix
    is_postfix = bool(op_postfix)

    if not operator_raw:
        operator_raw = "="  # Если оператор не указан, считаем равенством

    # Если оператор находится после числа (postfix), его нужно "отзеркалить"
    # Пример: "100<" означает "100 < ВЫСОТА", что эквивалентно "ВЫСОТА > 100"
    if is_postfix:
        flip_map = {
            ">": "<",
            "<": ">",
            ">=": "<=",
            "<=": ">=",
            "=>": "<=",  # => это >=, при отзеркаливании становится <=
            "=<": ">=",  # =< это <=, при отзеркаливании становится >=
        }
        operator_raw = flip_map.get(operator_raw, operator_raw)

    # Нормализация операторов для использования в Python
    op_map = {
        ">": ">",
        "<": "<",
        "=": "==",
        "==": "==",
        ">=": ">=",
        "=>": ">=",
        "<=": "<=",
        "=<": "<=",
    }
    operator = op_map.get(operator_raw)

    if not operator:
        return None

    try:
        value = int(value_str)
        return operator, value
    except (ValueError, TypeError):
        return None


def _get_avatars_from_metadata(metadata_path: Path) -> List[AvatarInfo]:
    """
    Загружает информацию об аватарах из файла images_metadata.json.
    Обеспечивает обратную совместимость, догружая размер файла, если он отсутствует.

    :param metadata_path: Путь к файлу images_metadata.json.
    :return: Список объектов AvatarInfo.
    """
    metadata_bytes = metadata_path.read_bytes()
    metadata = orjson.loads(metadata_bytes)
    image_dir = metadata_path.parent / AVATAR_IMG_MAIL_DIR

    avatars = []
    for filename, data in metadata.items():
        email = filename[: -len(".jpg")]
        email_bytes = email.encode("utf-8")

        # Получаем размер файла: сначала из метаданных, а если нет - из файловой системы
        file_size = data.get("file_size")
        if file_size is None:
            try:
                file_path = image_dir / filename
                file_size = file_path.stat().st_size if file_path.exists() else 0
            except Exception:
                file_size = 0  # На случай, если файл был удален, а в метаданных остался

        avatars.append(
            AvatarInfo(
                email=email,
                size=f"{data.get('width', 0)} x {data.get('height', 0)}",
                width=data.get("width", 0),
                height=data.get("height", 0),
                file_size=file_size,
                md5=hashlib.md5(email_bytes).hexdigest(),
                sha256=hashlib.sha256(email_bytes).hexdigest(),
            )
        )
    return avatars


def _get_avatars_from_filesystem(image_dir: Path) -> List[AvatarInfo]:
    """
    Сканирует файловую систему для получения информации об аватарах (fallback-метод).

    :param image_dir: Путь к директории с изображениями.
    :return: Список объектов AvatarInfo.
    """
    avatars = []
    for filename in os.listdir(image_dir):
        if not filename.lower().endswith(".jpg"):
            continue

        full_path = image_dir / filename
        try:
            with Image.open(full_path) as img:
                width, height = img.size
            file_size = full_path.stat().st_size
        except Exception as e:
            logger.warning(f"Could not read image info for {filename}: {e}")
            continue

        email = filename[: -len(".jpg")]
        email_bytes = email.encode("utf-8")
        avatars.append(
            AvatarInfo(
                email=email,
                size=f"{width} x {height}",
                width=width,
                height=height,
                file_size=file_size,
                md5=hashlib.md5(email_bytes).hexdigest(),
                sha256=hashlib.sha256(email_bytes).hexdigest(),
            )
        )
    return avatars


def get_all_avatars() -> List[AvatarInfo]:
    """
    Получает список информации о всех аватарах.

    Приоритетно использует кэш images_metadata.json. Если он недоступен,
    сканирует файловую систему.

    :return: Список объектов AvatarInfo.
    """
    base_avatar_path = Path(settings.internal_data_path) / AVATARS_PATH
    image_dir = base_avatar_path / AVATAR_IMG_MAIL_DIR

    if not base_avatar_path.exists() or not base_avatar_path.is_dir():
        logger.warning(f"Base avatar directory not found: {base_avatar_path}")
        return []

    metadata_path = base_avatar_path / AVATAR_METADATA_FILENAME
    avatars = []
    if metadata_path.exists():
        try:
            if not suppress_app_logging_var.get():
                logger.debug(
                    f"Loading avatar info from {AVATAR_METADATA_FILENAME} cache."
                )
            avatars = _get_avatars_from_metadata(metadata_path)
        except Exception as e:
            logger.error(
                f"Failed to load {AVATAR_METADATA_FILENAME}, falling back to filesystem scan. Error: {e}"
            )
            if image_dir.exists():
                avatars = _get_avatars_from_filesystem(image_dir)
    else:
        logger.warning(
            f"{AVATAR_METADATA_FILENAME} not found, scanning filesystem. This may be slow."
        )
        if image_dir.exists():
            avatars = _get_avatars_from_filesystem(image_dir)

    return avatars


def get_paginated_avatars(
    page: int,
    page_size: int,
    filters: Optional[Dict[str, str]] = None,
    sort_by: str = "email",
    sort_dir: str = "asc",
) -> PaginatedAvatarsResponse:
    """
    Получает пагинированный, отфильтрованный и отсортированный список аватаров.

    :param page: Номер страницы.
    :param page_size: Размер страницы (0 для получения всех).
    :param filters: Словарь с фильтрами.
    :param sort_by: Поле для сортировки.
    :param sort_dir: Направление сортировки ('asc' или 'desc').
    :return: Объект PaginatedAvatarsResponse.
    """
    all_avatars = get_all_avatars()

    filtered_avatars = all_avatars
    if filters:
        # Фильтрация по текстовым полям
        text_filters = {
            k: v.lower()
            for k, v in filters.items()
            if k in ["email", "md5", "sha256"] and v
        }
        for key, value in text_filters.items():
            filtered_avatars = [
                avatar
                for avatar in filtered_avatars
                if value in getattr(avatar, key).lower()
            ]

        # Фильтрация по размеру (высоте) и размеру файла
        size_filters_map = {"size": "height", "file_size": "file_size"}
        for filter_key, model_attr in size_filters_map.items():
            size_filter_str = filters.get(filter_key)
            if size_filter_str:
                parsed_filter = _parse_size_filter(size_filter_str)
                if parsed_filter:
                    operator, value = parsed_filter
                    filter_expression = f"lambda a: a.{model_attr} {operator} {value}"
                    try:
                        filter_func = eval(filter_expression)
                        filtered_avatars = [
                            a for a in filtered_avatars if filter_func(a)
                        ]
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply size filter '{size_filter_str}': {e}"
                        )
                else:
                    logger.warning(f"Invalid size filter format: '{size_filter_str}'")

    # Сортировка
    valid_sort_fields = {"email", "md5", "sha256", "height", "width", "file_size"}
    if sort_by not in valid_sort_fields:
        sort_by = "email"

    try:
        # Для числовых полей используем числовую сортировку, для остальных - строковую
        is_numeric_sort = sort_by in ["height", "width", "file_size"]
        key_func = (
            (lambda x: getattr(x, sort_by))
            if is_numeric_sort
            else (lambda x: str(getattr(x, sort_by)).lower())
        )
        sorted_avatars = sorted(
            filtered_avatars, key=key_func, reverse=(sort_dir == "desc")
        )
    except AttributeError:
        logger.warning(f"Invalid sort field '{sort_by}', falling back to default.")
        sorted_avatars = sorted(filtered_avatars, key=lambda x: x.email)

    total_items = len(sorted_avatars)

    # Пагинация
    if page_size > 0:
        total_pages = math.ceil(total_items / page_size) if page_size > 0 else 1
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_items = sorted_avatars[start_index:end_index]
    else:  # page_size=0 означает "вернуть все"
        paginated_items = sorted_avatars
        total_pages = 1
        page = 1

    return PaginatedAvatarsResponse(
        items=paginated_items,
        total_items=total_items,
        total_pages=total_pages,
        current_page=page,
    )
