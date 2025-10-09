let lastSavedPassphrase = "";
let lastSavedUsers = []
let lastSavedLdapOptions = {}
let lastSavedSamlOptions = {};

/**
 * Обновляет lastSaved значения при новых данных
 *
 * @param {string} passphrase - текущий passphrase
 * @param {Array<Object>} users - текущее состояние users (array, копия!)
 * @param {Object} ldapOptions - текущее состояние ldap_options (object, копия!)
 * @param {Object} samlOptions - текущее состояние saml_options (object, копия!)
 */
function updateLastSavedState(passphrase, users, ldapOptions, samlOptions) {
    lastSavedPassphrase = passphrase || "";
    lastSavedUsers = JSON.parse(JSON.stringify(users || []));
    lastSavedLdapOptions = JSON.parse(JSON.stringify(ldapOptions || {}));
    lastSavedSamlOptions = JSON.parse(JSON.stringify(samlOptions || {}));
}

/**
 * Проверяет, совпадает ли ui-стейт с последним сохранённым
 * @param {string} passphrase
 * @param {Array<Object>} users
 * @param {Object} ldapOptions
 * @param {Object} samlOptions
 * @returns {boolean}
 */
function isCurrentStateSaved(passphrase, users, ldapOptions, samlOptions) {
    // Используем try-catch на случай, если какой-то из объектов null/undefined
    try {
        const isPassphraseSame = passphrase === lastSavedPassphrase;
        const areUsersSame = JSON.stringify(users) === JSON.stringify(lastSavedUsers);
        const areLdapSame = JSON.stringify(ldapOptions) === JSON.stringify(lastSavedLdapOptions);
        const areSamlSame = JSON.stringify(samlOptions) === JSON.stringify(lastSavedSamlOptions);

        return isPassphraseSame && areUsersSame && areLdapSame && areSamlSame;
    } catch (e) {
        // Если при сериализации возникает ошибка, считаем состояния разными
        return false;
    }
}

/**
 * Получить последний сохраненный снапшот (только для чтения!)
 */
function getLastSaved() {
    return {
        passphrase: lastSavedPassphrase,
        users: JSON.parse(JSON.stringify(lastSavedUsers)),
        ldapOptions: JSON.parse(JSON.stringify(lastSavedLdapOptions)),
        samlOptions: JSON.parse(JSON.stringify(lastSavedSamlOptions))
    }
}

export {updateLastSavedState, isCurrentStateSaved, getLastSaved}