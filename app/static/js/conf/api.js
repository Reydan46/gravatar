import {log} from '../share/logger.js';
import {constants} from '../share/constants.js';
import {decryptHybridLocal, encryptHybrid, generateAesKeyAndIv, encryptString} from "../auth/crypto.js";

/**
 * Форматирует имя файла для бэкапа на основе хоста.
 * @param {string} hostname - Имя хоста из window.location.
 * @returns {string} - Отформатированное имя файла.
 */
function formatBackupFilename(hostname) {
    const serviceName = constants.SERVICE_NAME || 'backup';
    if (!hostname) {
        return `${serviceName}_settings.yml`;
    }
    const sanitizedHost = hostname.replace(/[.:]/g, '_');
    return `${serviceName}_settings_${sanitizedHost}.yml`;
}

/**
 * Запускает синхронизацию аватаров и обрабатывает поток событий.
 * @param {string} passphrase - Passphrase для авторизации запроса.
 * @param {function(object): void} onMessage - Callback-функция для обработки каждого сообщения.
 * @param {function(): void} onComplete - Callback-функция, вызываемая при закрытии стрима.
 * @param {function(string): void} onError - Callback-функция для обработки ошибок.
 */
function syncAvatars(passphrase, onMessage, onComplete, onError) {
    log('CONF', 'Запуск синхронизации аватаров через EventSource');
    try {
        fetch(constants.ENDPOINT_AVATAR_SYNC, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${passphrase}`
            },
            credentials: 'include'
        }).then(response => {
            if (!response.ok) {
                response.json().then(errorData => {
                    throw new Error(errorData.detail || `HTTP ошибка: ${response.status}`);
                }).catch(() => {
                    throw new Error(`HTTP ошибка: ${response.status}`);
                });
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            function processStreamResult(result) {
                if (result.done) {
                    if (buffer) {
                        try {
                            const data = JSON.parse(buffer.substring(6));
                            onMessage(data);
                        } catch (e) {
                            // Игнорируем ошибки парсинга в конце, если остался мусор
                        }
                    }
                    log('CONF', 'Стрим синхронизации завершен.');
                    onComplete();
                    return;
                }

                buffer += decoder.decode(result.value, {stream: true});
                const events = buffer.split('\n\n');
                buffer = events.pop(); // Последний чанк может быть неполным

                for (const eventStr of events) {
                    if (eventStr.startsWith('data: ')) {
                        try {
                            const jsonData = eventStr.substring(6);
                            const data = JSON.parse(jsonData);
                            onMessage(data);
                        } catch (e) {
                            log('CONF', `Ошибка парсинга JSON из стрима: ${e}`, 'error');
                            onError(`Ошибка обработки данных: ${e.message}`);
                        }
                    }
                }
                // Читаем следующий чанк
                reader.read().then(processStreamResult).catch(err => {
                    log('CONF', `Ошибка чтения стрима: ${err}`, 'error');
                    onError(`Ошибка чтения потока: ${err.message}`);
                    onComplete();
                });
            }

            reader.read().then(processStreamResult);

        }).catch(e => {
            log('CONF', `Ошибка при запуске синхронизации: ${e}`, 'error');
            onError(e.message);
            onComplete();
        });

    } catch (e) {
        log('CONF', `Критическая ошибка при настройке fetch: ${e}`, 'error');
        onError(e.message);
        onComplete();
    }
}


/**
 * Загружает текущую конфигурацию.
 * @param {boolean} forceKeyRefresh - Флаг для принудительного обновления ключа.
 * @returns {Promise<object>} - Объект конфигурации.
 */
async function fetchConfig(forceKeyRefresh = false) {
    log('CONF', 'Загрузка текущей конфигурации');
    const {aesKey, aesb64Key} = await generateAesKeyAndIv();
    const enc_key = await encryptString(aesb64Key, forceKeyRefresh);

    const res = await fetch(constants.ENDPOINT_CONF_DATA, {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enc_key})
    });

    if (res.status === 409 && !forceKeyRefresh) {
        log('CONF', 'Сервер вернул 409 Conflict. Повторный запрос с обновлением ключа.', 'warn');
        return fetchConfig(true);
    }

    if (!res.ok) {
        let detail = null;
        try {
            const errData = await res.json();
            detail = errData.detail;
        } catch (_) {
        }
        const err = new Error();
        err.status = res.status;
        err.detail = detail;
        throw err;
    }

    try {
        const {enc_sym_data, iv} = await res.json();
        const data_str = await decryptHybridLocal(aesKey, enc_sym_data, iv);
        const data = JSON.parse(data_str);
        log('CONF', 'Загружено:', data);
        return data;
    } catch (e) {
        const err = new Error();
        err.status = 500;
        err.detail = constants.MSG_CONF_PARSE_ERROR;
        throw err;
    }
}


/**
 * Сохраняет изменения конфигурации
 *
 * :param data: объект для обновления
 * :return: ответ сервера
 */
async function updateConfig(data) {
    log('CONF', 'Сохранение конфига', data)
    try {
        const payload = await encryptHybrid(JSON.stringify(data));
        const res = await fetch(constants.ENDPOINT_CONF_UPDATE, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "include",
            body: JSON.stringify(payload)
        })
        if (!res.ok) throw new Error(constants.MSG_CONF_UPDATE_ERROR)
        const resData = await res.json()
        log('CONF', 'Сохранено:', resData)
        return resData
    } catch (e) {
        log('CONF', e, 'error')
        throw new Error(e.message || 'Update config error');
    }
}

/**
 * Запрашивает и скачивает файл резервной копии конфигурации
 * @param {boolean} forceKeyRefresh - Флаг для принудительного обновления ключа.
 */
async function downloadBackup(forceKeyRefresh = false) {
    log('CONF', 'Запрос на скачивание резервной копии');
    try {
        const {aesKey, aesb64Key} = await generateAesKeyAndIv();
        const enc_key = await encryptString(aesb64Key, forceKeyRefresh);

        const res = await fetch(constants.ENDPOINT_CONF_BACKUP, {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enc_key})
        });

        if (res.status === 409 && !forceKeyRefresh) {
            log('CONF', 'Сервер вернул 409 Conflict при скачивании бэкапа. Повторяю с обновлением ключа.', 'warn');
            return downloadBackup(true);
        }

        if (!res.ok) {
            let detail = 'Unknown backup error';
            try {
                const errData = await res.json();
                detail = errData.detail || detail;
            } catch (_) {
            }
            throw new Error(detail);
        }

        const {enc_sym_data, iv} = await res.json();
        const decrypted_content = await decryptHybridLocal(aesKey, enc_sym_data, iv);

        const blob = new Blob([decrypted_content], {type: 'application/x-yaml;charset=utf-8'});
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = formatBackupFilename(window.location.hostname);
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        log('CONF', 'Файл резервной копии успешно скачан');
        return {success: true};
    } catch (e) {
        log('CONF', e, 'error');
        return {success: false, error: e.message};
    }
}

/**
 * Загружает файл для восстановления конфигурации
 * @param {File} file - Файл для восстановления
 * @returns {Promise<Object>} - Ответ сервера
 */
async function uploadRestore(file) {
    log('CONF', 'Загрузка файла для восстановления', file.name);
    try {
        const fileContent = await file.text();
        const payload = await encryptHybrid(fileContent);

        const res = await fetch(constants.ENDPOINT_CONF_RESTORE, {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload),
        });

        const resData = await res.json();
        if (!res.ok) {
            throw new Error(resData.detail || 'Restore failed');
        }

        log('CONF', 'Файл успешно загружен и обработан:', resData);
        return resData;
    } catch (e) {
        log('CONF', e, 'error');
        throw new Error(e.message || 'Restore config error');
    }
}

/**
 * Проверяет подключение к LDAP серверу.
 * @param {Object} ldapData - Объект с настройками LDAP.
 * @returns {Promise<Object>} - Ответ сервера.
 */
async function checkLdapConnection(ldapData) {
    log('CONF', 'Проверка LDAP соединения', ldapData);
    try {
        const payload = await encryptHybrid(JSON.stringify(ldapData));
        const res = await fetch(constants.ENDPOINT_LDAP_CHECK, {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        const resData = await res.json();
        if (!res.ok) {
            throw new Error(resData.detail || 'Ошибка проверки LDAP');
        }

        log('CONF', 'Результат проверки LDAP:', resData);
        return resData;
    } catch (e) {
        log('CONF', e, 'error');
        throw new Error(e.message || 'Ошибка при обращении к серверу для проверки LDAP.');
    }
}

/**
 * Запрашивает генерацию нового приватного ключа.
 * @returns {Promise<{private_key: string}>} - PEM-строка ключа.
 */
async function generatePrivateKey() {
    log('CONF', 'Запрос на генерацию нового приватного ключа');
    try {
        const res = await fetch(constants.ENDPOINT_CRYPTO_GENERATE_PRIVATE_KEY, {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
        });
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || 'Ошибка генерации приватного ключа');
        }
        const data = await res.json();
        log('CONF', 'Приватный ключ успешно сгенерирован.');
        return data;
    } catch (e) {
        log('CONF', 'Ошибка при генерации приватного ключа:', e, 'error');
        throw e;
    }
}

/**
 * Запрашивает генерацию сертификата на основе приватного ключа.
 * @param {string} privateKey - Приватный ключ в формате PEM (однострочный Base64).
 * @returns {Promise<{certificate: string}>} - PEM-строка сертификата.
 */
async function generateCertFromKey(privateKey) {
    log('CONF', 'Запрос на генерацию сертификата из ключа');
    try {
        const res = await fetch(constants.ENDPOINT_CRYPTO_GENERATE_CERT_FROM_KEY, {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({private_key: privateKey})
        });
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || 'Ошибка генерации сертификата');
        }
        const data = await res.json();
        log('CONF', 'Сертификат успешно сгенерирован.');
        return data;
    } catch (e) {
        log('CONF', 'Ошибка при генерации сертификата:', e, 'error');
        throw e;
    }
}


export {
    fetchConfig,
    updateConfig,
    downloadBackup,
    uploadRestore,
    checkLdapConnection,
    syncAvatars,
    generatePrivateKey,
    generateCertFromKey
};