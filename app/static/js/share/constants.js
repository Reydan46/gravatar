export const constants = {
    // ==== Имя сервиса ====
    SERVICE_NAME: 'gravatar',

    // ==== Значения по умолчанию для галереи ====
    DEFAULT_PAGE_SIZE: 10,
    PAGE_SIZE_OPTIONS: [6, 10, 20, 50, 100, 200, 500, 1000],
    // Размер порции для "бесконечной" прокрутки
    INFINITE_SCROLL_PAGE_SIZE: 20,
    // Размер превью аватара в галерее
    GALLERY_AVATAR_PREVIEW_SIZE: 96,


    // ==== Значения по умолчанию для логов ====

    // Формат отображения строки лога по умолчанию (шаблон)
    DEFAULT_LOG_FORMAT: "[ %(asctime)s.%(msecs)s %(module)-20s - %(funcName)25s() ][%(process)2s][%(session_id)4s][%(levelname)s] %(message)s",
    // Стандартный размер шрифта логов
    DEFAULT_FONT_SIZE: '12',
    // Сколько логов показывать по умолчанию
    DEFAULT_LOG_LIMIT: '1000',
    // Дефолтный текст фильтрации логов (пусто)
    DEFAULT_FILTER: '',
    // Цвета для уровней логирования (HEX)
    DEFAULT_LOG_COLORS: {
        debug: '#b0bec5',
        info: '#1e90ff',
        warning: '#ffcc00',
        error: '#ff6b6b'
    },
    // Начальный уровень логов в фильтре
    DEFAULT_LOG_LEVEL: 'DEBUG',


    // ==== Диапазоны, лимиты и границы ====

    // Карта уровней логов для фильтрации
    LOG_LEVEL_MAP: {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3
    },
    // Максимальное количество логов для хранения в UI
    LOG_ENTRY_MAX: 1000,
    // Минимально допустимое число логов в выводе
    LOG_ENTRY_MIN: 0,
    // Количество логов, добавляемых в DOM за одну итерацию (обычно равно LOG_ENTRY_MAX)
    LOG_FLUSH_BATCH_SIZE: 1000,
    // Минимальный размер шрифта логов (px)
    FONT_SIZE_MIN: 6,
    // Максимальный размер шрифта логов (px)
    FONT_SIZE_MAX: 32,
    // Длина вектора инициализации для AES
    AES_IV_LENGTH: 16,


    // ==== UI, скролл и анимации ====

    // Порог невидимости для появления кнопки "вниз"
    SCROLL_THRESHOLD: 70,
    // Время скролла вниз при добавлении логов (мс)
    SCROLL_ADD_LOG_DURATION_MS: 100,
    // Время скролла вниз после фильтрации логов (мс)
    SCROLL_AFTER_CHANGE_LOG_FILTER_DURATION_MS: 100,
    // Время скролла вниз после изменения логов (мс)
    SCROLL_AFTER_CHANGE_LOG_LEVEL_DURATION_MS: 0,
    // Длительность обычного скролла вниз (мс)
    SCROLL_DEFAULT_DURATION_MS: 200,

    // Время анимации добавления строки (мс)
    ENTRY_ANIMATION_ADD_DURATION: 500,
    // Время анимации удаления строки (мс)
    ENTRY_ANIMATION_REMOVE_DURATION: 200,
    // Длительность подсветки инпута (мс)
    INPUT_HIGHLIGHT_DURATION_MS: 1100,
    // Задержка перед анимацией (мс)
    ANIMATION_DELAY_MS: 60,
    // Тип анимации "добавление"
    ANIMATION_ADD: 'add',
    // Тип анимации "удаление"
    ANIMATION_REMOVE: 'remove',


    // ==== UI Поведение ====
    // Открывать меню навигации при наведении (true) или по клику (false)
    OPEN_MENU_ON_HOVER: true,
    // Открывать меню действий на странице /conf при наведении (true) или по клику (false)
    OPEN_CONF_MENU_ON_HOVER: true,

    // ==== URL-пути для переходов и страниц ====

    // Страница — Просмотр логов
    URL_PAGE_LOGS: '/logs',
    // Страница — Галерея
    URL_PAGE_GALLERY: '/gallery',
    // Страница — Настройки
    URL_PAGE_CONF: '/conf',
    // Домашняя страница
    URL_PAGE_HOME: '/logs',
    // Страница после выхода из логов
    URL_LOGOUT_LOGS: '/auth?next=/logs',
    // Страница после выхода из настроек
    URL_LOGOUT_CONF: '/auth?next=/conf',


    // ==== API endpoints ====

    // Авторизация (POST)
    ENDPOINT_LOGIN: '/auth/login',
    // Выход (GET)
    ENDPOINT_LOGOUT: '/auth/logout',
    // Проверка токена (POST)
    ENDPOINT_TOKEN_CHECK: '/auth/check_token',
    // Обновление токена (POST)
    ENDPOINT_TOKEN_REFRESH: '/auth/refresh_token',
    // SSE-поток логов (GET)
    ENDPOINT_LOGS_STREAM: '/logs/stream',
    // md5(password) (POST)
    ENDPOINT_CRYPTO_HASH_PASSWORD: '/crypto/hash_password',
    // Публичный RSA-ключ (POST)
    ENDPOINT_CRYPTO_PUBLIC_KEY: '/crypto/public_key',
    // Сгенерировать приватный ключ (POST)
    ENDPOINT_CRYPTO_GENERATE_PRIVATE_KEY: '/crypto/generate_private_key',
    // Сгенерировать сертификат из ключа (POST)
    ENDPOINT_CRYPTO_GENERATE_CERT_FROM_KEY: '/crypto/generate_cert_from_key',
    // Получить полный конфиг (POST)
    ENDPOINT_CONF_DATA: '/conf/data',
    // Обновить конфиг (POST)
    ENDPOINT_CONF_UPDATE: '/conf/update',
    // Скачать бэкап (GET)
    ENDPOINT_CONF_BACKUP: '/conf/backup',
    // Восстановить из бэкапа (POST)
    ENDPOINT_CONF_RESTORE: '/conf/restore',
    //
    ENDPOINT_LDAP_CHECK: '/ldap/check',
    //
    ENDPOINT_AVATAR_SYNC: '/avatar/sync',
    // Получить данные для галереи (GET)
    ENDPOINT_GALLERY_DATA: '/gallery/data',


    // ==== Временные интервалы и тайминги ====

    // Задержка перед показом статуса "Подключение..." (мс)
    TIME_SHOW_CONNECTING_DELAY: 250,
    // Время жизни JWT токена в секундах (3 часа)
    TOKEN_MAX_AGE_S: 60 * 60 * 3,
    // Таймаут для API авторизации (мс)
    API_TIMEOUT_AUTH: 10000,
    // Период автопродоления токена (10 мин)
    TIME_TOKEN_REFRESH: 1000 * 60 * 10,
    // Задержки для повторных попыток обновления токена при сетевой ошибке (мс)
    RETRY_DELAYS: [10000, 20000, 40000, 60000], // 10с, 20с, 40с, 1м
    // Проверка, активен ли поток логов (2 сек)
    TIME_LOGS_CHECK_INACTIVE: 1000 * 2,
    // Неактивен если нет данных 15 сек
    TIME_LOGS_INACTIVE: 1000 * 15,
    // Подключение к логам после ошибки (1 сек)
    TIME_LOGS_RECONNECT_ERROR: 1000,
    // Подключение после закрытия соединения (1 сек)
    TIME_LOGS_RECONNECT_CLOSE: 1000,
    // Повторное подключение к логам после сетевой ошибки (5 сек)
    TIME_LOGS_RECONNECT_FETCH: 1000 * 5,
    // Время между добавлением пакетов логов в DOM (мс)
    TIME_LOGS_FLUSH_BATCH: 10,
    // Задержка скрытия меню навигации (мс)
    TIME_NAV_MENU_HIDE_DELAY: 1000,
    // Задержка для фокуса на элементе (мс)
    FOCUS_TIMEOUT_MS: 70,
    // Задержка скрытия кнопки скролла (мс)
    SCROLL_BTN_HIDE_DELAY_MS: 100,
    // Задержка обновления скролла (мс)
    SCROLL_UPDATE_DEBOUNCE_MS: 300,
    // Задержка для debounce в настройках (мс)
    DEBOUNCE_SETTINGS_INPUT: 100,
    // Задержка для debounce лимита логов (мс)
    DEBOUNCE_LOG_LIMIT_APPLY: 500,
    // Задержка для debounce при сохранении прав пользователя (мс)
    DEBOUNCE_PERMISSION_SAVE_MS: 300,
    // Задержка для debounce color picker'а (мс)
    DEBOUNCE_COLOR_PICKER: 10,
    // Длительность показа tooltip'а (мс)
    TOOLTIP_FADE_DURATION_MS: 1500,


    // ==== Сообщения для показа пользователю ====

    // Сообщение о неработающем WebCrypto
    MSG_CRYPTO_ERROR: 'Браузер не поддерживает Web Crypto API или работает не в безопасном режиме (HTTPS или localhost). Обновите браузер или включите защищённое соединение.',
    // Ошибка входа
    MSG_AUTH_ERROR: 'Ошибка авторизации',
    // Пустые поля login
    MSG_ENTER_USER_PASS: 'Пожалуйста, введите имя пользователя и пароль',
    // Нет прав для раздела
    MSG_ACCESS_DENIED: 'Отказано в доступе: недостаточно прав.',
    // Нет прав к логам
    MSG_LOGS_ACCESS_DENIED: 'Отказано в доступе: недостаточно прав для просмотра логов.',
    // Нет прав к настройкам
    MSG_CONF_ACCESS_DENIED: 'Отказано в доступе: недостаточно прав для настройки конфигурации.',
    // Ошибка загрузки конфигурации
    MSG_CONF_LOAD_ERROR: 'Ошибка загрузки конфигурации',
    // Ошибка разбора конфигурации
    MSG_CONF_PARSE_ERROR: 'Ошибка обработки ответа от сервера',
    // Успешное сохранение конфига
    MSG_CONF_SAVED: 'Настройки актуальны',
    // Изменено, не сохранено
    MSG_CONF_EDITED: 'Настройки изменены, но не отправлены',
    // Общая ошибка настроек
    MSG_CONF_DEFAULT_ERROR: 'Неизвестная ошибка',
    // Ошибка при обновлении
    MSG_CONF_UPDATE_ERROR: 'Ошибка обновления конфигурации',
    // Ошибка генерации хэша
    MSG_HASH_GEN_ERROR: 'Ошибка генерации hash',
    // Нет прав к галерее
    MSG_GALLERY_ACCESS_DENIED: 'Отказано в доступе: недостаточно прав для просмотра галереи.',
    // Сообщения для копирования
    MSG_COPIED: 'Скопировано',
    MSG_COPY_ERROR: 'Ошибка!',


    // ==== Генерация API-ключей ====

    // Символы для ключа
    API_KEY_CHARS: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@!*-_^,.',

    // ==== Поля конфига (API) ====
    CONF_FIELD_USERS: 'users',
    CONF_FIELD_LDAP: 'ldap_options',
    CONF_FIELD_SAML: 'saml_options',


    // ==== Права доступа (Permissions) ====
    PERM_LOGS: 'logs',
    PERM_SETTINGS: 'settings',
    PERM_GALLERY: 'gallery',
    PERM_TITLES: {
        logs: "Доступ к странице с логами",
        settings: "Доступ к странице с настройками",
        gallery: "Доступ к странице с галереей"
    },


    // ==== Модальное окно Prompt ====
    PROMPT_MODE_ALERT: 'alert',
    PROMPT_MODE_CONFIRM: 'confirm',
    PROMPT_MODE_INPUT_TEXT: 'input_text',
    PROMPT_MODE_INPUT_PASSWORD: 'input_password',
    PROMPT_LABEL_OK: 'OK',
    PROMPT_LABEL_CANCEL: 'Отмена',


    // ==== Cookie и служебные ключи ====
    COOKIE_AUTH_STATUS: 'auth_status',
    LOCAL_STORAGE_PUB_KEY: 'pubKey',
    SAML_USER_PASSWORD_HASH_PLACEHOLDER: "saml_user",


    // ==== Регулярные выражения для валидации ====
    REGEX: {
        // Проверяет, что строка является валидным FQDN или простым hostname (например, localhost)
        HOSTNAME: /^(?!-)(?!.*--)([a-zA-Z0-9-]{1,63})(?<!-)(\.(?!-)(?!.*--)([a-zA-Z0-9-]{1,63})(?<!-))*$/,
        // Проверяет строгий синтаксис Distinguished Name (DN) с разрешенными атрибутами
        DISTINGUISHED_NAME: /^((?:CN|OU|DC|O|L|ST|C|UID)=[\w\s.-]+)(,(?:CN|OU|DC|O|L|ST|C|UID)=[\w\s.-]+)*$/i
    },


    // ==== Метки для UI ====
    UI_LABELS: {
        LDAP: {
            FIELDS: {
                LDAP_SERVER: 'Сервер',
                LDAP_USERNAME: 'Пользователь',
                LDAP_PASSWORD: 'Пароль',
                LDAP_SEARCH_BASE: 'База поиска'
            },
            PLACEHOLDERS: {
                LDAP_SERVER: 'dc.domain.com',
                LDAP_USERNAME: 'Имя пользователя',
                LDAP_PASSWORD: 'Пароль',
                LDAP_SEARCH_BASE: 'DC=domain,DC=com'
            }
        }
    },


    // ==== Сообщения токена ====
    MSG_TOKEN_UPDATED: 'Токен обновлен',
    MSG_TOKEN_NOT_UPDATED: 'Токен не обновлен',

    // ==== Подсказки для настроек безопасности SAML ====
    SAML_SECURITY_TOOLTIPS: {
        // === Настройки подписи сообщений, отправляемых вашим приложением (SP) ===
        authnRequestsSigned: "Ваше приложение (SP) будет подписывать запросы на вход. Это позволяет провайдеру идентификации (IdP) проверить, что запрос подлинный и отправлен именно вашим сервисом, а не подделан злоумышленником.",
        logoutRequestSigned: "Ваше приложение (SP) будет подписывать запросы на выход. Это позволяет IdP убедиться, что инициатива завершения сеанса исходит от вашего доверенного сервиса.",
        logoutResponseSigned: "Если выход инициирован со стороны IdP, ваше приложение (SP) подпишет свой ответ на этот запрос. Это позволяет IdP быть уверенным, что ответ получен от вас и сессия корректно завершена.",
        signMetadata: "Ваше приложение (SP) подпишет свои метаданные. При импорте метаданных IdP сможет проверить их целостность и убедиться, что конфигурация (URL, сертификаты) не была изменена при передаче.",

        // === Требования к сообщениям, получаемым от провайдера идентификации (IdP) ===
        wantMessagesSigned: "Ваше приложение (SP) будет требовать, чтобы некоторые входящие сообщения от IdP (например, запрос на выход) были подписаны. Это защищает от поддельных команд, якобы отправленных от имени IdP.",
        wantAssertionsSigned: "Ваше приложение (SP) будет требовать, чтобы блок с данными о пользователе (Assertion) внутри SAML-ответа был подписан со стороны IdP. Критически важная настройка, которая гарантирует, что атрибуты пользователя (роли, email) не были подменены в пути.",

        // === Требования к шифрованию данных от провайдера идентификации (IdP) ===
        nameIdEncrypted: "Ваше приложение (SP) будет требовать от IdP шифрования идентификатора пользователя (NameID). Это защищает идентификатор от перехвата и просмотра третьими лицами.",
        wantAssertionsEncrypted: "Ваше приложение (SP) будет требовать от IdP шифрования всего блока с данными о пользователе (Assertion). Это обеспечивает полную конфиденциальность передаваемых атрибутов (имя, email, роли), защищая их от перехвата.",
    }
};