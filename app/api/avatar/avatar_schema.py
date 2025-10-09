from typing import Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from config.constants import (
    AVATAR_DEFAULT_SIZE,
    AVATAR_MAX_SIZE,
    AVATAR_VALID_DEFAULTS,
    AVATAR_VALID_RATINGS,
)


class AvatarParams(BaseModel):
    """
    Схема для валидации и сбора параметров запроса аватара как зависимость.
    Поддерживает короткие и полные имена параметров через псевдонимы.
    """
    size: int = Field(
        default=AVATAR_DEFAULT_SIZE,
        ge=1,
        le=AVATAR_MAX_SIZE,
        validation_alias=AliasChoices("s", "size"),
    )
    default: Optional[str] = Field(
        default=None,
        pattern=f"^({'|'.join(AVATAR_VALID_DEFAULTS)})$",
        validation_alias=AliasChoices("d", "default"),
    )
    forcedefault: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("f", "forcedefault"),
    )
    rating: Optional[str] = Field(
        default=None,
        pattern=f"^({'|'.join(AVATAR_VALID_RATINGS)})$",
        validation_alias=AliasChoices("r", "rating"),
    )
    originalsize: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("o", "originalsize"),
    )

    @field_validator("forcedefault", "originalsize", mode="before")
    @classmethod
    def validate_boolean_params(cls, v: str, info: ValidationInfo) -> bool | str:
        """
        Обрабатывает параметр 'y' как True для forcedefault и originalsize.

        :param v: Входящее значение параметра.
        :param info: Информация о валидации.
        :return: Булево значение.
        """
        if v == 'y':
            return True
        return v
