import hashlib
from typing import Tuple

from PIL import Image, ImageDraw


def generate_wavatar(image_hash: str, size: int) -> Image.Image:
    """
    Генерирует аватар в стиле "wavatar" (пиксель-арт лицо).

    Создает пиксельное лицо 9x9 на основе хеша.

    :param image_hash: MD5 или SHA256 хеш.
    :param size: Размер конечного изображения.
    :return: Сгенерированное изображение PIL.Image.
    """
    hash_bytes = hashlib.md5(image_hash.encode("utf-8")).digest()

    # Определяем цвета
    background_color: Tuple[int, int, int] = (
        hash_bytes[0],
        hash_bytes[1],
        hash_bytes[2],
    )
    # Цвет кожи - более светлый оттенок основного цвета
    skin_color: Tuple[int, int, int] = (
        min(255, background_color[0] + 40),
        min(255, background_color[1] + 40),
        min(255, background_color[2] + 40),
    )
    # Цвет волос/бороды - более темный
    hair_color: Tuple[int, int, int] = (
        max(0, background_color[0] - 40),
        max(0, background_color[1] - 40),
        max(0, background_color[2] - 40),
    )
    # Цвет глаз и рта
    eye_color: Tuple[int, int, int] = (hash_bytes[3], hash_bytes[4], hash_bytes[5])
    mouth_color: Tuple[int, int, int] = (hash_bytes[6], hash_bytes[7], hash_bytes[8])

    # Создаем сетку 9x9 для лица
    grid_size = 9
    image = Image.new("RGB", (grid_size, grid_size), background_color)
    draw = ImageDraw.Draw(image)

    # Рисуем основу лица (кожа)
    for x in range(1, grid_size - 1):
        for y in range(1, grid_size - 1):
            draw.point((x, y), fill=skin_color)

    # Добавляем черты лица на основе байтов хеша
    byte_index = 9

    # Волосы (верхние 2 ряда)
    if hash_bytes[byte_index] % 2 == 0:
        for x in range(1, 8):
            draw.point((x, 1), fill=hair_color)
        if hash_bytes[byte_index + 1] % 2 == 0:
            for x in range(2, 7):
                draw.point((x, 2), fill=hair_color)

    # Борода/усы
    if hash_bytes[byte_index + 2] % 3 == 1:  # Усы
        draw.line([(2, 6), (6, 6)], fill=hair_color)
    elif hash_bytes[byte_index + 2] % 3 == 2:  # Борода
        for x in range(2, 7):
            draw.point((x, 7), fill=hair_color)
        draw.point((3, 6), fill=hair_color)
        draw.point((5, 6), fill=hair_color)

    # Глаза
    eye_y = 4
    draw.point((2, eye_y), fill=eye_color)
    draw.point((6, eye_y), fill=eye_color)
    if hash_bytes[byte_index + 3] % 2 == 0:  # "Зрачки"
        draw.point((2, eye_y), fill=skin_color)
        draw.point((6, eye_y), fill=skin_color)

    # Рот
    mouth_y = 6
    mouth_type = hash_bytes[byte_index + 4] % 4
    if mouth_type == 0:  # Прямой
        draw.line([(3, mouth_y), (5, mouth_y)], fill=mouth_color)
    elif mouth_type == 1:  # Улыбка
        draw.point((3, mouth_y), fill=mouth_color)
        draw.point((4, mouth_y + 1), fill=mouth_color)
        draw.point((5, mouth_y), fill=mouth_color)
    elif mouth_type == 2:  # Грустный
        draw.point((3, mouth_y + 1), fill=mouth_color)
        draw.point((4, mouth_y), fill=mouth_color)
        draw.point((5, mouth_y + 1), fill=mouth_color)
    # 4-й тип - без рта

    return image.resize((size, size), Image.Resampling.NEAREST)
