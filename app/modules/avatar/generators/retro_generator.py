import hashlib

from PIL import Image, ImageDraw


def generate_retro(image_hash: str, size: int) -> Image.Image:
    """
    Генерирует аватар в стиле "retro" (симметричный пиксельный узор).

    Создает симметричное изображение 5x5 на основе хеша.

    :param image_hash: MD5 или SHA256 хеш.
    :param size: Размер конечного изображения.
    :return: Сгенерированное изображение PIL.Image.
    """
    # Используем хеш для определения цвета и узора
    hash_bytes = hashlib.md5(image_hash.encode("utf-8")).digest()

    # Цвет (первые 3 байта)
    r, g, b = hash_bytes[0], hash_bytes[1], hash_bytes[2]
    foreground_color = (r, g, b)
    background_color = (240, 240, 240)

    # Создаем изображение и холст для рисования
    image = Image.new("RGB", (5, 5), background_color)
    draw = ImageDraw.Draw(image)

    # Создаем матрицу 5x5, отражая первые 3 столбца
    grid = [[False] * 5 for _ in range(5)]
    byte_index = 3
    for x in range(3):
        for y in range(5):
            # Используем каждый бит для определения, закрашивать ли пиксель
            if byte_index >= len(hash_bytes):
                bit = 0
            else:
                # Берем бит из байта, циклически проходя по 8 битам
                bit = (hash_bytes[byte_index] >> (y % 8)) & 1

            if bit == 1:
                grid[y][x] = True
                grid[y][4 - x] = True  # Зеркальное отражение

        # Переходим к следующему байту для следующего столбца
        if y == 4:
            byte_index += 1

    # Рисуем пиксели на холсте 5x5
    for y in range(5):
        for x in range(5):
            if grid[y][x]:
                draw.point((x, y), fill=foreground_color)

    # Масштабируем до нужного размера
    return image.resize((size, size), Image.Resampling.NEAREST)
