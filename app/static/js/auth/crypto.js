import {getFormattedTime, log} from '../share/logger.js'
import {constants} from '../share/constants.js'

let decryptionErrorOccurred = false;

/**
 * Проверка поддержки WebCrypto API
 */
async function testCryptoSupport() {
    log('AUTH', 'Проверка поддержки WebCrypto API')
    if (!window.crypto?.subtle) {
        log('AUTH', 'WebCrypto API НЕ поддерживается', 'warn')
        return false
    }
    try {
        const key = await window.crypto.subtle.generateKey(
            {
                name: "RSA-OAEP",
                modulusLength: 2048,
                publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
                hash: {name: "SHA-256"}
            },
            true,
            ["encrypt", "decrypt"]
        )
        const data = new TextEncoder().encode("crypto")
        const encrypted = await window.crypto.subtle.encrypt({name: "RSA-OAEP"}, key.publicKey, data)
        await window.crypto.subtle.decrypt({name: "RSA-OAEP"}, key.privateKey, encrypted)
        log('AUTH', 'WebCrypto API работает корректно')
        return true
    } catch (e) {
        log('AUTH_CRYPTO', 'Ошибка работы WebCrypto API:', e, 'warn')
        return false
    }
}

/**
 * Переводит ArrayBuffer в base64
 */
function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i])
    }
    return window.btoa(binary)
}

/**
 * Проверяет валидность ключа в localStorage относительно срока жизни ключа
 *
 * @param {object} parsedKey JWK публичного ключа
 * @return {boolean} true если ключ валиден
 */
function isPubKeyStillValid(parsedKey) {
    if (!parsedKey || typeof parsedKey !== "object") return false
    if (!parsedKey.lr || !parsedKey.krp) return false

    const lastRotation = Number(parsedKey.lr)
    const keyRotationPeriod = Number(parsedKey.krp)

    if (!isFinite(lastRotation) || !isFinite(keyRotationPeriod)) return false

    // Ключ считается валидным, если текущее время не превышает время его создания плюс период ротации
    const now = Date.now() / 1000
    return now <= lastRotation + keyRotationPeriod
}

/**
 * Загружает и импортирует публичный ключ с учётом кеша и времени запуска сервера
 *
 * @param {boolean} [forceReload=false] Если true — игнорировать кеш и загрузить ключ заново с сервера
 * @return {Promise<CryptoKey>} Импортированный публичный ключ для шифрования
 */
async function fetchAndImportPublicKey(forceReload = false) {
    // Проверяем локальный кеш
    const cache = localStorage.getItem(constants.LOCAL_STORAGE_PUB_KEY)
    if (!forceReload && cache) {
        try {
            const parsed = JSON.parse(cache)
            if (isPubKeyStillValid(parsed)) {
                log('AUTH', `Публичный ключ из кеша (last_rotation: ${getFormattedTime(parsed.lr * 1000)}, valid_until: ${getFormattedTime((parsed.lr + parsed.krp) * 1000)})`)
                return await importPublicKey(parsed)
            } else {
                log('AUTH', 'Ключ из localStorage истёк, удалён')
                localStorage.removeItem(constants.LOCAL_STORAGE_PUB_KEY)
            }
        } catch (e) {
            log('AUTH', 'Ошибка чтения pubKey из localStorage: ' + e, 'warn')
            localStorage.removeItem(constants.LOCAL_STORAGE_PUB_KEY)
        }
    } else if (forceReload) {
        log('AUTH', 'Принудительная загрузка публичного ключа с сервера, кеш игнорируется')
        if (cache) localStorage.removeItem(constants.LOCAL_STORAGE_PUB_KEY)
    }

    // Получаем ключ с сервера
    const response = await fetch(constants.ENDPOINT_CRYPTO_PUBLIC_KEY, {
        method: 'POST'
    })
    log('AUTH', `Публичный ключ получен с сервера (статус: ${response.status})`)
    if (!response.ok)
        throw new Error(`Не удалось получить публичный ключ. Статус: ${response.status}`)
    const publicKeyJWK = await response.json()
    if (!publicKeyJWK?.kty || !publicKeyJWK?.n || !publicKeyJWK?.e || !publicKeyJWK?.alg || !publicKeyJWK?.lr || !publicKeyJWK?.krp) {
        log('AUTH', 'Некорректный JWK: отсутствует kty/n/e/alg/lr/krp', publicKeyJWK, 'error')
        throw new Error('Некорректный JWK: отсутствует kty/n/e/alg/lr/krp')
    }
    localStorage.setItem(constants.LOCAL_STORAGE_PUB_KEY, JSON.stringify(publicKeyJWK))
    decryptionErrorOccurred = false; // Сбрасываем флаг ошибки после успешной загрузки ключа
    log('AUTH', `Публичный ключ сохранён (last_rotation: ${getFormattedTime(publicKeyJWK.lr * 1000)}, valid_until: ${getFormattedTime((publicKeyJWK.lr + publicKeyJWK.krp) * 1000)})`)
    return await importPublicKey(publicKeyJWK)
}

/**
 * Импортирует публичный ключ JWK согласно используемому alg
 *
 * @param {object} publicKeyJWK - Ключ
 * @return {Promise<CryptoKey>} Импортированная ключ-структура
 */
async function importPublicKey(publicKeyJWK) {
    const map = {
        "RSA-OAEP": {name: "RSA-OAEP", hash: "SHA-1"},
        "RSA-OAEP-256": {name: "RSA-OAEP", hash: "SHA-256"},
        "RSA-OAEP-384": {name: "RSA-OAEP", hash: "SHA-384"},
        "RSA-OAEP-512": {name: "RSA-OAEP", hash: "SHA-512"},
        "RSA1_5": {name: "RSAES-PKCS1-v1_5"}
    }
    const alg = publicKeyJWK.alg.toUpperCase()
    if (!map[alg]) {
        log('AUTH', `JWK alg не поддерживается этим клиентом: ${alg}`, 'error')
        throw new Error(`Клиент не поддерживает данный тип ключа/алгоритма: ${alg}`)
    }
    const scheme = map[alg].name
    const params = {name: scheme}
    if (map[alg].hash)
        params.hash = {name: map[alg].hash}

    const key = await window.crypto.subtle.importKey(
        "jwk",
        publicKeyJWK,
        params,
        false,
        ["encrypt"]
    )
    log('AUTH', `Ключ успешно импортирован. Алгоритм: ${scheme}, hash: ${map[alg].hash || "-/-"}`)
    return key
}

/**
 * Шифрует произвольную строку с помощью публичного ключа сервера
 *
 * @param {string} plainText - Строка, которую нужно зашифровать
 * @param {boolean} [forceKeyReload=false] - Принудительно загрузить публичный ключ с сервера (игнорировать кеш)
 * @return {Promise<string>} Зашифрованная строка (base64)
 */
async function encryptString(plainText, forceKeyReload = false) {
    const shouldForceReload = forceKeyReload || decryptionErrorOccurred;
    const publicCryptoKey = await fetchAndImportPublicKey(shouldForceReload);
    const encryptedBuffer = await window.crypto.subtle.encrypt(
        {name: publicCryptoKey.algorithm.name},
        publicCryptoKey,
        new TextEncoder().encode(plainText)
    )
    return arrayBufferToBase64(encryptedBuffer)
}

/**
 * Генерирует AES-ключ, возвращает объект с ключом, его raw и base64 представлением, а также случайный IV
 *
 * @return {Promise<{ aesKey: CryptoKey, aesb64Key: string }>}
 */
async function generateAesKeyAndIv() {
    const aesKey = await window.crypto.subtle.generateKey(
        {name: "AES-CBC", length: 256},
        true,
        ["encrypt", "decrypt"]
    )
    const aesKeyRaw = await window.crypto.subtle.exportKey("raw", aesKey)
    const aesb64Key = arrayBufferToBase64(aesKeyRaw)
    return {aesKey, aesb64Key}
}

/**
 * Шифрует данные с помощью гибридного шифрования (AES + RSA).
 * Может использовать предварительно сгенерированный AES-ключ.
 *
 * @param {string} plainText - Строка для шифрования.
 * @param {boolean} [forceKeyReload=false] - Принудительно загрузить публичный RSA-ключ.
 * @param {object} [preGeneratedKey=null] - Необязательный объект с ключами `{aesKey, aesb64Key}`.
 * @returns {Promise<{enc_sym_data: string, iv: string, enc_key: string}>} - Зашифрованный payload.
 */
async function encryptHybrid(plainText, forceKeyReload = false, preGeneratedKey = null) {
    let localAesKey, localAesB64Key

    if (preGeneratedKey) {
        localAesKey = preGeneratedKey.aesKey
        localAesB64Key = preGeneratedKey.aesb64Key
    } else {
        const generated = await generateAesKeyAndIv()
        localAesKey = generated.aesKey
        localAesB64Key = generated.aesb64Key
    }

    const iv = window.crypto.getRandomValues(new Uint8Array(constants.AES_IV_LENGTH))
    const data = new TextEncoder().encode(plainText)
    const encryptedSymData = await window.crypto.subtle.encrypt(
        {name: "AES-CBC", iv},
        localAesKey,
        data
    )

    const shouldForceReload = forceKeyReload || decryptionErrorOccurred;
    const enc_key = await encryptString(localAesB64Key, shouldForceReload)

    return {
        enc_sym_data: arrayBufferToBase64(encryptedSymData),
        iv: arrayBufferToBase64(iv),
        enc_key
    }
}

/**
 * Дешифрует данные (AES-CBC) с PKCS7
 *
 * @param {CryptoKey} symmetricKey - CryptoKey (AES)
 * @param {string} enc_sym_data - строка (base64)
 * @param {string} iv - строка (base64)
 * @return {Promise<string>}
 */
async function decryptHybridLocal(symmetricKey, enc_sym_data, iv) {
    const encryptedDataBuf = Uint8Array.from(atob(enc_sym_data), c => c.charCodeAt(0))
    const ivBuf = Uint8Array.from(atob(iv), c => c.charCodeAt(0))
    try {
        const decrypted = await window.crypto.subtle.decrypt(
            {name: "AES-CBC", iv: ivBuf},
            symmetricKey,
            encryptedDataBuf
        );
        decryptionErrorOccurred = false;
        return new TextDecoder().decode(new Uint8Array(decrypted));
    } catch (e) {
        decryptionErrorOccurred = true;
        log('AUTH_CRYPTO', 'Ошибка локальной расшифровки, устанавливаем флаг decryptionErrorOccurred', e, 'error');
        throw e;
    }
}

export {encryptString, testCryptoSupport, encryptHybrid, decryptHybridLocal, generateAesKeyAndIv}