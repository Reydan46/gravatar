import {log} from '../share/logger.js';
import {constants} from '../share/constants.js';
import {
    decryptHybridLocal,
    encryptHybrid,
    generateAesKeyAndIv,
    encryptString
} from "../auth/crypto.js";

/**
 * Получает данные для галереи с сервера с использованием гибридного шифрования.
 * @param {object} params - Параметры запроса (page, pageSize, filters, sortBy, sortDir).
 * @returns {Promise<object>} - Расшифрованные данные от сервера.
 */
async function fetchGalleryData({page, pageSize, filters, sortBy, sortDir}) {
    log('GALLERY_API', `Запрос данных: стр ${page}, размер ${pageSize}, сорт ${sortBy} ${sortDir}, фильтры`, filters);
    try {
        const {aesKey, aesb64Key} = await generateAesKeyAndIv();
        const requestData = {page, pageSize, filters, sortBy, sortDir};

        const payload = await encryptHybrid(JSON.stringify(requestData), false, {aesKey, aesb64Key});

        const response = await fetch(constants.ENDPOINT_GALLERY_DATA, {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
                errorData = {detail: `Ошибка сервера: ${response.status}`};
            }
            throw new Error(errorData.detail || `Ошибка сервера: ${response.status}`);
        }

        const encryptedResponse = await response.json();

        const decrypted_content = await decryptHybridLocal(
            aesKey,
            encryptedResponse.enc_sym_data,
            encryptedResponse.iv
        );

        log('GALLERY_API', 'Данные успешно получены и расшифрованы');
        return JSON.parse(decrypted_content);

    } catch (error) {
        log('GALLERY_API', `Ошибка при получении данных галереи: ${error.message}`, 'error');
        throw error;
    }
}

/**
 * Запрашивает passphrase с бэкенда.
 * @returns {Promise<string|null>} - Passphrase или null в случае ошибки.
 */
async function fetchPassphrase() {
    try {
        const {aesKey, aesb64Key} = await generateAesKeyAndIv();
        const enc_key = await encryptString(aesb64Key);

        const res = await fetch(constants.ENDPOINT_CONF_DATA, {
            method: 'POST',
            credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enc_key})
        });

        if (!res.ok) {
            throw new Error(`Ошибка получения passphrase: ${res.status}`);
        }

        const {enc_sym_data, iv} = await res.json();
        const data_str = await decryptHybridLocal(aesKey, enc_sym_data, iv);
        const data = JSON.parse(data_str);
        return data.passphrase;
    } catch (e) {
        log('GALLERY_API', `Критическая ошибка при получении passphrase: ${e.message}`, 'error');
        return null;
    }
}

/**
 * Запускает синхронизацию аватаров и обрабатывает поток событий.
 * @param {string} passphrase - Passphrase для авторизации.
 * @param {function(object): void} onMessage - Callback для обработки сообщений.
 * @param {function(): void} onComplete - Callback при завершении.
 * @param {function(string): void} onError - Callback для ошибок.
 */
function syncAvatars(passphrase, onMessage, onComplete, onError) {
    fetch(constants.ENDPOINT_AVATAR_SYNC, {
        method: 'POST',
        headers: {'Authorization': `Bearer ${passphrase}`},
        credentials: 'include'
    }).then(response => {
        if (!response.ok) {
            response.json().then(errorData => {
                throw new Error(errorData.detail || `HTTP ошибка: ${response.status}`);
            }).catch(() => {
                throw new Error(`HTTP ошибка: ${response.status}`);
            });
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function processStreamResult(result) {
            if (result.done) {
                log('GALLERY_API', 'Стрим синхронизации завершен.');
                onComplete();
                return;
            }

            buffer += decoder.decode(result.value, {stream: true});
            const events = buffer.split('\n\n');
            buffer = events.pop();

            for (const eventStr of events) {
                if (eventStr.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(eventStr.substring(6));
                        onMessage(data);
                    } catch (e) {
                        onError(`Ошибка обработки данных: ${e.message}`);
                    }
                }
            }
            reader.read().then(processStreamResult).catch(err => {
                onError(`Ошибка чтения потока: ${err.message}`);
                onComplete();
            });
        }

        reader.read().then(processStreamResult);

    }).catch(e => {
        onError(e.message);
        onComplete();
    });
}


export {fetchGalleryData, fetchPassphrase, syncAvatars};