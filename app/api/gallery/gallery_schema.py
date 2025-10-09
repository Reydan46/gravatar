from typing import List

from pydantic import BaseModel, Field


class AvatarInfo(BaseModel):
    """
    Схема с информацией об одном аватаре.
    """

    email: str = Field(..., description="Email пользователя (имя файла без расширения)")
    size: str = Field(..., description="Размер изображения в формате 'Ширина x Высота'")
    width: int = Field(..., description="Ширина изображения в пикселях")
    height: int = Field(..., description="Высота изображения в пикселях")
    file_size: int = Field(..., description="Размер файла в байтах")
    md5: str = Field(..., description="MD5 хеш email")
    sha256: str = Field(..., description="SHA256 хеш email")


class PaginatedAvatarsResponse(BaseModel):
    """
    Схема для ответа с пагинированным списком аватаров.
    """

    items: List[AvatarInfo] = Field(..., description="Список аватаров на странице")
    total_items: int = Field(..., description="Общее количество аватаров")
    total_pages: int = Field(..., description="Общее количество страниц")
    current_page: int = Field(..., description="Текущая страница")
