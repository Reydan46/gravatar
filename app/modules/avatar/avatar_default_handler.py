from pathlib import Path
from typing import Dict, Optional

from PIL import Image

from config.constants import DEFAULT_AVATAR_TYPE
from modules.avatar.generators.monsterid_generator import generate_monsterid
from modules.avatar.generators.retro_generator import generate_retro
from modules.avatar.generators.wavatar_generator import generate_wavatar
from modules.avatar.avatar_image_processor import open_image

# Более надежный способ найти корневую директорию 'app'
# __file__ -> .../app/modules/avatar/avatar_default_handler.py
# Идем вверх по дереву, пока не найдем директорию с именем 'app'
APP_DIR = Path(__file__).resolve()
while APP_DIR.name != "app":
    APP_DIR = APP_DIR.parent
    if APP_DIR == APP_DIR.parent:  # Защита от бесконечного цикла, если 'app' не найдено
        raise FileNotFoundError("Could not find the 'app' directory root.")

RESOURCES_DIR = APP_DIR / "resources"

# Карта генерируемых аватаров
GENERATOR_MAP = {
    "monsterid": lambda h, s: generate_monsterid(h, s, RESOURCES_DIR),
    "retro": generate_retro,
    "wavatar": generate_wavatar,
}


def get_default_avatar(
    params: Dict, image_hash: str, size: int
) -> Optional[Image.Image]:
    """
    Возвращает изображение по умолчанию на основе параметров запроса.

    Может вернуть как статическое изображение, так и сгенерированное на лету.

    :param params: Словарь с параметрами ('default', 'forcedefault').
    :param image_hash: Хеш для использования в генераторах.
    :param size: Размер изображения для генераторов.
    :return: Объект PIL.Image или None, если запрошен '404'.
    """
    default_type = params.get("default", DEFAULT_AVATAR_TYPE)

    if default_type == "404":
        return None

    if default_type in GENERATOR_MAP:
        generator_func = GENERATOR_MAP[default_type]
        # Для monsterid передаем путь к ресурсам
        if default_type == "monsterid":
            return generator_func(image_hash, size)
        return generator_func(image_hash, size)

    # В противном случае, ищем статический файл
    image_path = RESOURCES_DIR / "avatar" / "default" / f"{default_type}.png"
    return open_image(image_path)


def get_fallback_avatar() -> Optional[Image.Image]:
    """
    Возвращает самый базовый аватар по умолчанию, если другие не найдены.

    :return: Объект PIL.Image.
    """
    image_path = RESOURCES_DIR / "avatar" / "default" / f"{DEFAULT_AVATAR_TYPE}.png"
    return open_image(image_path)
