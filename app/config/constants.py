# Настройки логирования
LOG_CONFIG = {
    "level": "DEBUG",
    "main_logger_name": "gravatar",
    "in_console_enabled": True,
    "in_console_format": "[ %(asctime)s.%(msecs)03d %(module)-20s - %(funcName)25s() ][%(process)2d][%(session_id)4s][%(levelname)s] %(message)s",
    "in_console_format_datetime": "%d.%m.%Y %H:%M:%S",
    "in_file_enabled": False,
    "in_file_format": "[%(asctime)s.%(msecs)03d %(module)-20s - %(funcName)25s() ][%(session_id)4s][%(levelname)s] %(message)s",
    "in_file_format_datetime": "%d.%m.%Y %H:%M:%S",
    "show_key_press_in_input_message": False,
    "max_size_file_bytes": 1 * 1024 * 1024,
    "backup_file_count": 1,
}

# Shared memory универсальные настройки
SHARED_MEMORY_CONFIG = {
    "logs": {
        "MEMORY_NAME": "logs",
        "HEADER_SIZE": 8,
        "ENTRY_HEADER_SIZE": 4,
        "ENTRY_SIZES": {
            "asctime": 19,
            "msecs": 3,
            "module": 20,
            "funcName": 25,
            "process": 5,
            "session_id": 4,
            "levelname": 3,
            "message": 1300,
        },
        "ENTRY_ORDER": [
            "asctime",
            "msecs",
            "module",
            "funcName",
            "process",
            "session_id",
            "levelname",
            "message",
        ],
        "MAX_BUFFER_SIZE": 1000,
    },
    "logs_counter": {
        "MEMORY_NAME": "logs_counter",
        "SIZE": 4,
        "MAX_VALUE": 2_000_000_000,
    },
    "pids": {
        "MEMORY_NAME": "pids",
        "SIZE": 1024,  # Хватает для хранения 255 PIDs int32 + заголовок
    },
    "shutdown": {"MEMORY_NAME": "shutdown", "SIZE": 8},
    "settings": {
        "MEMORY_NAME": "settings",
        "HEADER_SIZE": 16,  # 8 байт mtime + 8 байт size
        "SIZE": 1024 * 64,  # 64 килобайт
    },
    "crypto": {
        "MEMORY_NAME": "crypto",
        "ENTRY_SIZES": {
            "priv_len": 4,
            "pub_len": 4,
            "rot_time": 8,
            "priv_bytes": 4096,  # ориентировочный максимум PEM (~1700-1800 для 2048-бит)
            "pub_bytes": 1024,  # ориентировочный максимум PEM (~400-600 для 2048-бит)
        },
        "ENTRY_ORDER": ["priv_len", "pub_len", "rot_time", "priv_bytes", "pub_bytes"],
    },
    "auth": {
        "MEMORY_NAME": "auth",
        "HEADER_SIZE": 8,
        "ENTRY_HEADER_SIZE": 4,
        "ENTRY_SIZES": {
            "ip": 39,  # максимально возможный размер IPv6-адреса в тексте
            "timestamp": 16,  # достаточно для числа unixtime в str
            "username": 64,  # макс. размер имени пользователя (UTF-8!)
            "success": 1,
            "unlock_time": 16,
        },
        "ENTRY_ORDER": ["ip", "timestamp", "username", "success", "unlock_time"],
        "MAX_BUFFER_SIZE": 1000,
    },
    "boot_time": {"MEMORY_NAME": "boot_time", "SIZE": 8},
}

# Уровни логирования с сокращениями
LEVEL_TO_SHORT = {
    10: "DBG",  # logging.DEBUG
    20: "INF",  # logging.INFO
    30: "WRN",  # logging.WARNING
    40: "ERR",  # logging.ERROR
    50: "FTL",  # logging.FATAL
}

# Путь к файлу с секретом JWT (относительно internal_data_path)
SECRET_FILE = "jwt_secret_key"

# Пути к файлам криптографии (относительно internal_data_path)
CRYPTO_MASTER_KEY_FILE = "crypto_master.key"
ENCRYPTED_RSA_KEY_FILE = "rsa_keypair.enc"

# Путь к файлу конфигурации (относительно internal_data_path)
CONFIG_FILE = "settings.yml"

# Интервалы для работы с логами (в секундах)
LOGS_KEEPALIVE_INTERVAL = 5
LOGS_SLOW_CHECK_INTERVAL = 1
LOGS_FAST_CHECK_INTERVAL = 0.5
LOGS_ACTIVITY_TIMEOUT = 30

# Константы для аутентификации и токенов (в секундах)
TOKEN_MAX_AGE = 60 * 60 * 3  # 3 часа
TOKEN_RENEW_THRESHOLD_SECONDS = 60 * 15  # 15 минут

# Константы для аутентификации
AUTH_CONFIG = {
    "max_attempts": 5,  # Максимальное количество попыток аутентификации
    "window_seconds": 60
    * 10,  # За какое время ограничивать количество попыток (10 минут)
    "lockout_time": 60
    * 10,  # Время блокировки после превышения лимита попыток (10 минут)
}

# Константы для криптографии
CRYPTO_RSA_CONFIG = {
    "key_size": 2048,  # Размер ключа RSA в битах
    "public_exponent": 65537,  # Публичный экспонент для генерации RSA ключа
    "key_rotation_period": 60 * 5,  # Период ротации ключей в секундах (5 минут)
    "padding_mode": "OAEP",  # 'OAEP' или 'PKCS1v15'
    "hash_algorithm": "SHA256",  # для OAEP
}

# Константы для fingerprint
FINGERPRINT_HEADERS = [
    "host",
    "accept-encoding",
    "accept-language",
    "user-agent",
    "sec-ch-ua-platform",
    "sec-ch-ua",
    "sec-ch-ua-mobile",
]

# Константы для cookies
ACCESS_TOKEN_COOKIE_NAME = "access_token"  # Имя куки для токена доступа
AUTH_STATUS_COOKIE_NAME = "auth_status"  # Имя куки для статуса аутентификации
BOOT_TIME_COOKIE_NAME = "boot_time"  # Имя куки для хранения времени запуска сервера

# Домашняя страница
URL_PAGE_HOME = "/logs"

# Исключения для логирования запросов
REQUEST_LOGGING_EXCLUDE_PATHS = [
    "/static",
    "/health",
    "/favicon",
    "/auth",
    "/crypto",
    "/logs",
    "/conf",
    "/gallery",
    "/.well-known",
]

# Список путей административных страниц, с которых могут идти "шумные" запросы
ADMIN_REFERER_PATHS = [
    "/auth",
    "/conf",
    "/gallery",
]
# Список "шумных" целевых путей, логирование которых нужно отключать,
# если запрос пришел с одной из страниц в ADMIN_REFERER_PATHS
ADMIN_REFERER_EXCLUDE_TARGETS = ["/avatar", "/gallery", "/saml"]

# Интервал (сек) для подавления лог-спама от недоверенных IP в ProxyMiddleware. 0=выкл.
PROXY_MIDDLEWARE_LOG_THROTTLE_SECONDS = 60

# Список IP-адресов для исключения из проверок ProxyMiddleware (например, для систем мониторинга)
PROXY_MIDDLEWARE_EXCLUDE_IPS = []

# Список путей для исключения из проверки HostAllowMiddleware
PROTECT_MIDDLEWARE_EXCLUDE_PATHS = ["/health"]

# Константы для аватаров
AVATARS_PATH = "avatars"  # Относительно internal_data_path
AVATAR_METADATA_FILENAME = "images_metadata.json"  # Относительно AVATARS_PATH
DEFAULT_AVATARS_PATH = "resources/avatar/default"  # Относительно корня приложения app
DEFAULT_AVATAR_TYPE = "gravatar"
AVATAR_IMG_HASH_DIR = "hash"
AVATAR_IMG_MAIL_DIR = "images"
AVATAR_HASH_LENGTHS = {"md5": 32, "sha256": 64}
AVATAR_HASH_CHARS = "0123456789abcdef"
AVATAR_DEFAULT_SIZE = 96
AVATAR_MAX_SIZE = 800
AVATAR_SYNC_PROGRESS_STEP = 5  # Шаг прогресса в процентах для отчета
AVATAR_VALID_DEFAULTS = [
    "404",
    "mm",
    "mp",
    "identicon",
    "monsterid",
    "wavatar",
    "retro",
    "robohash",
    "blank",
]
AVATAR_VALID_RATINGS = ["g", "pg", "r", "x"]

# Константы для SAML
SAML_USER_PASSWORD_HASH_PLACEHOLDER = "saml_user"
SAML_REQUEST_PREPARE_SETTINGS = {
    "https": "on",
    "http_host": "",
    "script_name": "",
    "server_port": "",
    "get_data": {},
    "post_data": {},
    "query_string": "",
}
