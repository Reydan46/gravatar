import io
from pathlib import Path
from typing import Dict, Optional

from PIL import Image

from config.constants import AVATARS_PATH, AVATAR_IMG_HASH_DIR
from config.settings import settings
from modules.avatar.avatar_default_handler import get_default_avatar, get_fallback_avatar
from modules.avatar.avatar_image_processor import (
    image_to_jpeg_buffer,
    open_image,
    resize_image,
)
from modules.avatar.avatar_parameter_validator import (
    parse_and_validate_params,
    validate_hash,
)


def get_avatar_image(image_hash: str, params: Dict) -> Optional[io.BytesIO]:
    """
    Основная функция для получения изображения аватара.

    Координирует поиск аватара, обработку изображений по умолчанию и
    применение параметров (размер, original).

    :param image_hash: "грязный" хеш из URL.
    :param params: Словарь с параметрами запроса.
    :return: Буфер io.BytesIO с изображением в формате JPEG или None.
    """
    clean_hash = image_hash.split(".")[0].lower()
    if not validate_hash(clean_hash):
        raise ValueError(f"Invalid hash format: {clean_hash}")

    validated_params = parse_and_validate_params(params)
    size = validated_params.get("size")

    image: Optional[Image.Image] = None
    hash_dir = Path(settings.internal_data_path) / AVATARS_PATH / AVATAR_IMG_HASH_DIR
    avatar_path = hash_dir / f"{clean_hash}.jpg"

    if validated_params.get("forcedefault"):
        image = get_default_avatar(validated_params, clean_hash, size)
    elif avatar_path.is_file():
        image = open_image(avatar_path)
    elif "default" in validated_params:
        image = get_default_avatar(validated_params, clean_hash, size)

    if image is None:
        if validated_params.get("default") == "404":
            return None
        image = get_fallback_avatar()

    # Финальная проверка: если даже fallback-аватар не найден,
    # мы не можем продолжать. Это предотвратит AttributeError.
    if image is None:
        raise FileNotFoundError("Fallback avatar could not be loaded. Check resource files.")

    is_generated = validated_params.get("default") in ["monsterid", "retro", "wavatar"]
    if not is_generated and not validated_params.get("originalsize"):
        image = resize_image(image, size)

    return image_to_jpeg_buffer(image)