import logging
from datetime import datetime

from config.constants import AUTH_CONFIG, LOG_CONFIG
from shared_memory.shm_auth import add_auth_attempt_to_shm, get_auth_attempts_from_shm

logger = logging.getLogger(LOG_CONFIG["main_logger_name"])


def is_ip_locked(client_ip: str, now: int) -> int | None:
    """
    Проверяет наличие активного блокирования по последней попытке IP

    :param client_ip: IP клиента
    :param now: unixtime
    :return: unixtime окончания блокировки или None
    """
    attempts = [a for a in get_auth_attempts_from_shm(0) if a["ip"] == client_ip]
    if not attempts:
        return None
    last = attempts[-1]
    unlock_time = int(last.get("unlock_time") or 0)
    if unlock_time > now:
        unlock_str = datetime.fromtimestamp(unlock_time).strftime("%d.%m.%Y %H:%M:%S")
        logger.info(f"IP {client_ip} is now BANNED (until {unlock_str})")
        return unlock_time
    return None


def process_failed_attempt(client_ip: str, username: str, now: int) -> int | None:
    """
    Обрабатывает неудачную попытку авторизации, выставляя блокировку при необходимости

    :param client_ip: IP клиента
    :param username: логин
    :param now: unixtime
    :return: время конца блокировки (если установлен бан), иначе None
    """
    # Находим последнюю успешную попытку для данного IP
    all_attempts = [a for a in get_auth_attempts_from_shm(0) if a["ip"] == client_ip]
    last_success_idx = None
    for idx in range(len(all_attempts) - 1, -1, -1):
        if all_attempts[idx]["success"] == "1":
            last_success_idx = idx
            break
    # Берём неуспешные попытки после последней успешной (или все, если успеха не было)
    if last_success_idx is not None:
        failed = [
            a for a in all_attempts[last_success_idx + 1 :] if a["success"] == "0"
        ]
    else:
        failed = [a for a in all_attempts if a["success"] == "0"]
    # Учтём только recent window
    failed = [
        a for a in failed if a["timestamp"] >= now - AUTH_CONFIG["window_seconds"]
    ]
    # учитываем текущую попытку (ещё не записана)
    need_ban = len(failed) + 1 >= AUTH_CONFIG["max_attempts"]

    unlock_time = 0
    if need_ban:
        unlock_time = now + AUTH_CONFIG["lockout_time"]
        add_auth_attempt_to_shm(
            client_ip, username, now, success=False, unlock_time=unlock_time
        )
        unlock_str = datetime.fromtimestamp(unlock_time).strftime("%d.%m.%Y %H:%M:%S")
        logins_count = {}
        for att in failed:
            login_val = att["username"]
            logins_count[login_val] = logins_count.get(login_val, 0) + 1
        logins_count[username] = logins_count.get(username, 0) + 1
        logins_str = ", ".join(
            f"'{login}': {count}" for login, count in logins_count.items()
        )
        logger.info(
            f"IP {client_ip} is now BANNED (until {unlock_str}); [username: attempts]: {logins_str}"
        )
    else:
        add_auth_attempt_to_shm(client_ip, username, now, success=False, unlock_time=0)

    return unlock_time if need_ban else None
