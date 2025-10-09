import {log} from '../share/logger.js';
import {constants} from "../share/constants.js";
import {encryptString} from "../auth/crypto.js";

/**
 * Генерация password hash через backend (по зашифрованному паролю)

 * :param password: строка, пароль
 * :return: Promise<string> hash пароля
 */
async function generatePasswordHash(password) {
    log('CONF', 'Генерация hash пароля')
    const enc_data = await encryptString(password);
    const res = await fetch(constants.ENDPOINT_CRYPTO_HASH_PASSWORD, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        credentials: "include",
        body: JSON.stringify({enc_data})
    })
    if (!res.ok) {
        log('CONF', 'Сервер вернул ошибку:', res, 'error')
        throw new Error(constants.MSG_HASH_GEN_ERROR)
    }
    const data = await res.json()
    log('CONF', 'Сгенерирован hash', data.hash)
    return data.hash
}

export {generatePasswordHash}