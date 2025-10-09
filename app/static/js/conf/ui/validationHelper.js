import {validateUsers, validateLdapOptions, validateSamlOptions} from '../validate.js';
import {setInputErrorState} from './commonUi.js';
import {setStatusOk, setStatusEdit, setStatusError} from './statusUi.js';
import {showPromptModal} from "./promptModal.js";
import {getLastSaved, isCurrentStateSaved} from '../state.js';
import {constants} from "../../share/constants.js";


/**
 * Универсальная функция для перепроверки и подсветки всех записей в группе.
 *
 * @param {string} entrySelector - CSS-селектор для одной строки-записи.
 * @param {Array<any>} dataArray - Массив с данными для этой группы.
 * @param {function(any, number, Array<any>): Array<{selector: string, isError: boolean}>} singleEntryValidator - Функция, валидирующая одну запись и возвращающая массив объектов для подсветки.
 * @param {function(Array<any>): string} globalValidator - Функция, валидирующая всю группу и возвращающая строку ошибки.
 * @param {string} errorPrefix - Префикс для глобального сообщения об ошибке (например, "[Пользователи]").
 * @param {string} dataKey - Ключ данных, соответствующий этой группе в стейте ('users' и т.д.).
 */
function revalidateAndHighlightEntries(entrySelector, dataArray, singleEntryValidator, globalValidator, errorPrefix, dataKey) {
    document.querySelectorAll(entrySelector).forEach(row => {
        const index = parseInt(row.dataset.index, 10);
        if (isNaN(index) || index < 0 || index >= dataArray.length) return;

        const entryData = dataArray[index];
        const validationResults = singleEntryValidator(entryData, index, dataArray);

        validationResults.forEach(result => {
            const input = row.querySelector(result.selector);
            if (input) {
                setInputErrorState(input, result.isError);
            }
        });
    });

    const globalError = globalValidator(dataArray);
    if (globalError) {
        setStatusError(`${errorPrefix} ${globalError}`);
    } else {
        const lastSaved = getLastSaved();
        const fullState = {...lastSaved};
        fullState[dataKey] = dataArray; // Обновляем только нужную часть
        if (isCurrentStateSaved(fullState.passphrase, fullState.users, fullState.ldapOptions, fullState.samlOptions)) {
            setStatusOk();
        } else {
            setStatusEdit();
        }
    }
}


/**
 * Проверяет все поля конфигурации на валидность перед добавлением новой записи.
 * Если есть ошибки, показывает модальное окно и возвращает false.
 *
 * @param {object} data - Полный объект данных конфигурации.
 * @returns {Promise<boolean>} - true, если все валидно, иначе false.
 */
async function preAddValidationCheck(data) {
    const errorMessages = [];
    let err;

    err = validateUsers(data.users);
    if (err) errorMessages.push(`[Пользователи] ${err}`);

    err = validateLdapOptions(data.ldap_options);
    if (err) errorMessages.push(`[Подключение к Active Directory] ${err}`);

    err = validateSamlOptions(data.saml_options);
    if (err) errorMessages.push(`[SAML] ${err}`);


    if (errorMessages.length > 0) {
        await showPromptModal('Сначала исправьте ошибки', {
            mode: constants.PROMPT_MODE_ALERT,
            error: errorMessages.join('\n'),
            okLabel: 'Понятно',
            backdropClose: true,
        });
        return false;
    }
    return true;
}


export {revalidateAndHighlightEntries, preAddValidationCheck};