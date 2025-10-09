import asyncio
import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator, Dict

import orjson
from PIL import Image
from ldap3.core.exceptions import LDAPException

from config.constants import (
    AVATARS_PATH,
    AVATAR_IMG_HASH_DIR,
    AVATAR_IMG_MAIL_DIR,
    AVATAR_SYNC_PROGRESS_STEP,
    LOG_CONFIG,
    AVATAR_METADATA_FILENAME,
)
from config.settings import settings
from modules.ldap.ldap_service import LdapService

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


async def sse_pack(data: Dict) -> str:
    """
    Форматирует данные в строку Server-Sent Event (SSE) и обеспечивает немедленную отправку.

    :param data: Словарь с данными для отправки.
    :return: Строка в формате SSE.
    """
    packed_data = f"data: {orjson.dumps(data).decode('utf-8')}\n\n"
    # Этот sleep(0) критически важен. Он передает управление циклу событий asyncio,
    # что заставляет ASGI-сервер (Uvicorn) сбросить буфер и немедленно отправить
    # данные клиенту, а не копить их.
    await asyncio.sleep(0)
    return packed_data


async def sync_avatars_from_ldap_stream() -> AsyncGenerator[str, None]:
    """
    Синхронизирует аватары из LDAP в локальное хранилище в потоковом режиме.

    Отправляет события (SSE) о ходе выполнения: начало, прогресс, завершение, ошибки.

    :return: Асинхронный генератор строк в формате SSE.
    """
    try:
        yield await sse_pack(
            {"status": "starting", "message": "Синхронизация запущена..."}
        )

        ldap_opts = settings.ldap_options
        ldap_service = LdapService(
            server_url=ldap_opts["LDAP_SERVER"],
            username=ldap_opts["LDAP_USERNAME"],
            password=ldap_opts["LDAP_PASSWORD"],
            search_base=ldap_opts["LDAP_SEARCH_BASE"],
        )
        yield await sse_pack(
            {
                "status": "fetching",
                "message": "Получение списка пользователей из LDAP...",
            }
        )
        users = ldap_service.search_users()
        total_users = len(users)
        logger.info(f"Successfully fetched {total_users} users from LDAP.")
        yield await sse_pack(
            {
                "status": "processing",
                "message": f"Найдено {total_users} пользователей. Начинается обработка...",
            }
        )

        base_avatar_path = Path(settings.internal_data_path) / AVATARS_PATH
        image_path = base_avatar_path / AVATAR_IMG_MAIL_DIR
        hash_path = base_avatar_path / AVATAR_IMG_HASH_DIR
        metadata_file = base_avatar_path / AVATAR_METADATA_FILENAME

        # Очищаем директории и старый файл метаданных
        if metadata_file.exists():
            metadata_file.unlink()
        for dir_path in [image_path, hash_path]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
            dir_path.mkdir(parents=True, exist_ok=True)
        logger.info("Avatar directories and metadata have been cleaned.")

        users_processed = 0
        last_reported_milestone = -1
        images_metadata = {}

        for i, entry in enumerate(users):
            mail_val = entry.mail.value if "mail" in entry else None
            thumb_val = (
                entry.thumbnailPhoto.value if "thumbnailPhoto" in entry else None
            )

            if not (mail_val and thumb_val):
                logger.warning(
                    f"Skipping user {entry.cn.value}: missing mail or photo."
                )
                continue

            safe_mail = mail_val.strip().lower()
            image_file_path = image_path / f"{safe_mail}.jpg"

            with image_file_path.open("wb") as f:
                f.write(thumb_val)

            # Получаем размеры изображения и файла для метаданных
            try:
                with Image.open(image_file_path) as img:
                    width, height = img.size
                file_size = image_file_path.stat().st_size
                images_metadata[f"{safe_mail}.jpg"] = {
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                }
            except Exception as e:
                logger.warning(f"Could not read image info for {safe_mail}.jpg: {e}")
                continue

            md5_hash = hashlib.md5(safe_mail.encode("utf-8")).hexdigest()
            link_path_md5 = hash_path / f"{md5_hash}.jpg"
            relative_image_path = os.path.relpath(image_file_path, hash_path)
            os.symlink(relative_image_path, link_path_md5)

            sha256_hash = hashlib.sha256(safe_mail.encode("utf-8")).hexdigest()
            link_path_sha256 = hash_path / f"{sha256_hash}.jpg"
            os.symlink(relative_image_path, link_path_sha256)

            users_processed += 1

            if total_users > 0:
                progress_percent = int(((i + 1) / total_users) * 100)
                current_milestone = progress_percent // AVATAR_SYNC_PROGRESS_STEP

                if (
                    current_milestone > last_reported_milestone
                    and progress_percent < 100
                ):
                    last_reported_milestone = current_milestone
                    rounded_percent = current_milestone * AVATAR_SYNC_PROGRESS_STEP
                    yield await sse_pack(
                        {
                            "status": "progress",
                            "progress": rounded_percent,
                            "message": f"Обработано {i + 1} из {total_users} (~{rounded_percent}%)",
                        }
                    )

        # Сохраняем метаданные в JSON файл с помощью orjson
        metadata_file.write_bytes(orjson.dumps(images_metadata))
        logger.info(f"Image metadata saved to {metadata_file}")

        logger.info(f"Avatar sync finished. Processed users: {users_processed}")
        yield await sse_pack(
            {
                "status": "completed",
                "message": f"Синхронизация завершена. Обработано: {users_processed} пользователей.",
                "processed": users_processed,
            }
        )
    except LDAPException as e:
        error_message = f"Ошибка LDAP: {e}"
        logger.error(f"Avatar sync failed: {error_message}")
        yield await sse_pack({"status": "error", "message": error_message})
    except Exception as e:
        logger.error(f"Avatar sync failed: {e}", exc_info=True)
        yield await sse_pack(
            {"status": "error", "message": f"Внутренняя ошибка сервера: {str(e)}"}
        )
