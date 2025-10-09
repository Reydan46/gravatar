import io
from pathlib import Path
from typing import Optional

from PIL import Image


def open_image(path: Path) -> Optional[Image.Image]:
    """
    Открывает изображение из файла.

    :param path: Путь к файлу изображения.
    :return: Объект PIL.Image или None, если файл не найден.
    """
    if not path.is_file():
        return None
    return Image.open(path)


def resize_image(image: Image.Image, size: int) -> Image.Image:
    """
    Изменяет размер изображения.

    :param image: Исходное изображение.
    :param size: Целевой размер (ширина и высота).
    :return: Измененное изображение.
    """
    return image.resize((size, size), Image.Resampling.LANCZOS)


def image_to_jpeg_buffer(image: Image.Image) -> io.BytesIO:
    """
    Конвертирует изображение в формат JPEG и сохраняет в байтовый буфер.

    :param image: Изображение для конвертации.
    :return: io.BytesIO буфер с данными изображения в формате JPEG.
    """
    output = io.BytesIO()
    # Конвертируем в RGB, если есть альфа-канал (RGBA) или палитра (P)
    if image.mode in ["RGBA", "P"]:
        image = image.convert("RGB")
    image.save(output, format="JPEG")
    output.seek(0)
    return output
