import hashlib
import logging
from pathlib import Path
from typing import List, Optional

from PIL import Image

from config.constants import LOG_CONFIG

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def _get_part(
    parts_base_path: Path, part_name: str, part_index: int
) -> Optional[Image.Image]:
    """
    Загружает определенную часть монстра.

    :param parts_base_path: Базовый путь к директории с частями ('.../monsterid_parts').
    :param part_name: Название части (например, 'body', 'eyes').
    :param part_index: Индекс файла части.
    :return: Изображение части (PIL.Image) или None, если части не найдены.
    """
    part_dir = parts_base_path / part_name
    try:
        if not part_dir.is_dir():
            logger.warning(f"MonsterID part directory not found: {part_dir}")
            return None

        files: List[Path] = sorted(list(part_dir.glob("*.png")))
        if not files:
            logger.warning(f"No parts found in MonsterID directory: {part_dir}")
            return None

        selected_file = files[part_index % len(files)]
        return Image.open(selected_file).convert("RGBA")
    except Exception as e:
        logger.error(f"Failed to load monster part '{part_name}': {e}", exc_info=True)
        return None


def generate_monsterid(
    image_hash: str, size: int, resources_dir: Path
) -> Optional[Image.Image]:
    """
    Генерирует аватар в стиле "monsterid".

    :param image_hash: MD5 или SHA256 хеш.
    :param size: Размер конечного изображения.
    :param resources_dir: Путь к корневой директории ресурсов.
    :return: Сгенерированное изображение PIL.Image или None в случае ошибки.
    """
    monster_parts_path = resources_dir / "avatar" / "monsterid_parts"
    hash_bytes = hashlib.md5(image_hash.encode("utf-8")).digest()

    r, g, b = hash_bytes[0], hash_bytes[1], hash_bytes[2]
    color = (r, g, b)

    # Используем разные байты хеша для каждой части, включая 'arms'
    part_args = [
        (monster_parts_path, "body", hash_bytes[4]),
        (monster_parts_path, "legs", hash_bytes[5]),
        (monster_parts_path, "hair", hash_bytes[6]),
        (monster_parts_path, "arms", hash_bytes[7]),
        (monster_parts_path, "eyes", hash_bytes[8]),
        (monster_parts_path, "mouth", hash_bytes[9]),
    ]

    parts = {name: _get_part(path, name, index) for path, name, index in part_args}
    body, eyes, mouth = parts.get("body"), parts.get("eyes"), parts.get("mouth")

    # Критическими частями остаются тело, глаза и рот. Руки, ноги, волосы - опциональны.
    if not body or not eyes or not mouth:
        logger.warning("Aborting MonsterID generation due to missing critical parts.")
        return None

    monster = Image.new("RGBA", (120, 120))

    body_data = body.load()
    for y in range(body.size[1]):
        for x in range(body.size[0]):
            if body_data[x, y][3] > 0:
                body_data[x, y] = color + (body_data[x, y][3],)

    # Собираем монстра, накладывая слои в правильном порядке
    if parts.get("legs"):
        monster.paste(parts["legs"], (0, 0), parts["legs"])
    monster.paste(body, (0, 0), body)
    if parts.get("arms"):
        monster.paste(parts["arms"], (0, 0), parts["arms"])
    if parts.get("hair"):
        monster.paste(parts["hair"], (0, 0), parts["hair"])
    monster.paste(eyes, (0, 0), eyes)
    monster.paste(mouth, (0, 0), mouth)

    return monster.resize((size, size), Image.Resampling.LANCZOS)
