import {constants} from '../share/constants.js';

/**
 * Функции валидации полей конфигурации.
 * Каждая функция возвращает строку с текстом ошибки или пустую строку, если валидация прошла успешно.
 */

/**
 * Валидирует passphrase.
 * @param {string} passphrase - Passphrase для проверки.
 * @returns {string} Текст ошибки или пустая строка.
 */
function validatePassphrase(passphrase) {
    if (!(passphrase || "").trim()) return "Passphrase не может быть пустой";
    return "";
}

/**
 * Валидирует список пользователей с иерархией: сначала имя, потом пароль.
 *
 * @param {Array<Object>} users - Список пользователей.
 * @returns {string} Текст ошибки или пустая строка.
 */
function validateUsers(users) {
    if (!Array.isArray(users)) return "Пользователи отсутствуют";

    // 1. Проверка на пустое имя
    for (let i = 0; i < users.length; i++) {
        if (!(users[i]?.username || "").trim()) {
            return `Имя пользователя в строке ${i + 1} не может быть пустым`;
        }
    }

    // 2. Проверка на дубликаты имен
    const names = new Set();
    for (let i = 0; i < users.length; i++) {
        const username = (users[i].username || "").trim();
        if (names.has(username)) {
            return `Дубликат имени пользователя: ${username} (строка ${i + 1})`;
        }
        names.add(username);
    }

    // 3. Проверка на пустой пароль
    for (let i = 0; i < users.length; i++) {
        if (!(users[i].password_hash || "").trim()) {
            const username = (users[i].username || "").trim();
            return `Пароль для пользователя '${username}' (строка ${i + 1}) не заполнен`;
        }
    }

    return "";
}


/**
 * Валидирует настройки подключения к LDAP.
 *
 * @param {Object} options - Настройки LDAP.
 * @returns {string} Текст ошибки или пустая строка.
 */
function validateLdapOptions(options) {
    if (!options || typeof options !== 'object') {
        return "Настройки LDAP отсутствуют или имеют неверный формат";
    }

    const server = (options.LDAP_SERVER || "").trim();
    const username = (options.LDAP_USERNAME || "").trim();
    const searchBase = (options.LDAP_SEARCH_BASE || "").trim();

    if (server && !constants.REGEX.HOSTNAME.test(server)) {
        return "Некорректный формат сервера LDAP (ожидается FQDN или hostname)";
    }

    if (!username) {
        return "Имя пользователя LDAP не может быть пустым";
    }

    if (searchBase && !constants.REGEX.DISTINGUISHED_NAME.test(searchBase)) {
        return "Некорректный формат базы поиска (ожидается 'DC=...,DC=...')";
    }

    return "";
}

/**
 * Валидирует настройки SAML.
 * @param {Object} options - Настройки SAML.
 * @returns {string} Текст ошибки или "" если всё в порядке.
 */
function validateSamlOptions(options) {
    if (!options || typeof options !== 'object') {
        return "Настройки SAML отсутствуют";
    }
    if (!options.enabled) {
        return ""; // Если выключено, не валидируем
    }

    const sp = options.sp || {};
    const idp = options.idp || {};
    const security = options.security || {};

    const acsUrl = sp.assertionConsumerService?.url?.trim();
    const idpEntityId = idp.entityId?.trim();
    const idpSsoUrl = idp.singleSignOnService?.url?.trim();
    const idpCert = idp.x509cert?.trim();

    if (!acsUrl) return "ACS URL не может быть пустым.";
    if (!idpEntityId) return "Entity ID провайдера (IdP) не может быть пустым.";
    if (!idpSsoUrl) return "SSO URL провайдера (IdP) не может быть пустым.";
    if (!idpCert) return "Сертификат провайдера (IdP) не может быть пустым.";

    // Простая проверка URL
    try {
        new URL(acsUrl);
        if (idpSsoUrl) new URL(idpSsoUrl);
    } catch (e) {
        return "Один из обязательных URL адресов имеет неверный формат.";
    }

    const spPrivateKey = sp.privateKey?.trim();
    const spCert = sp.x509cert?.trim();

    // Требования к подписи
    const signingRequired = security.authnRequestsSigned || security.logoutRequestSigned || security.logoutResponseSigned || security.signMetadata;
    if (signingRequired && !spPrivateKey) {
        return "Приватный ключ SP обязателен, если включена хотя бы одна из опций подписи (..Signed).";
    }

    // Требования к шифрованию
    const encryptionRequired = security.nameIdEncrypted || security.wantAssertionsEncrypted;
    if (encryptionRequired) {
        if (!spPrivateKey) {
            return "Приватный ключ SP обязателен, если включена опция шифрования.";
        }
        if (!spCert) {
            return "Сертификат SP обязателен, если включена опция шифрования.";
        }
    }

    return "";
}


export {
    validatePassphrase,
    validateUsers,
    validateLdapOptions,
    validateSamlOptions
};