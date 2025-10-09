import {fetchConfig} from './api.js';
import {renderUsers} from './ui/usersUi.js';
import {renderLdapOptions} from "./ui/ldapOptionsUi.js";
import {renderSamlOptions, getSamlOptionsFromForm} from "./ui/samlOptionsUi.js";
import {setStatusOk, setStatusEdit} from './ui/statusUi.js';
import {updateLastSavedState, isCurrentStateSaved} from './state.js';
import {animateEntryChildren} from "./ui/commonUi.js";
import {showAccessMessage} from '../share/accessUi.js';
import {startTokenRefresh, stopTokenRefresh} from "../auth/tokenRefresh.js";
import {checkToken, logout} from "../auth/api.js";
import {initNavMenu} from "../share/navMenu.js";
import {initConfMenu} from "./ui/confMenuUi.js";
import {preAddValidationCheck} from './ui/validationHelper.js';
import {log} from '../share/logger.js';
import {constants} from '../share/constants.js';
import {renderPassphrase} from "./ui/passphraseUi.js";

let accessDenied = false;

/**
 * Собирает полное текущее состояние из UI и сравнивает его с последним сохраненным,
 * устанавливая корректный начальный статус (OK или EDIT).
 * @param {object} configData - Объект конфигурации, который обновлялся при рендеринге.
 */
function checkInitialStatus(configData) {
    // SAML-опции собираются из DOM, в отличие от остальных, обновляемых в объекте
    configData.saml_options = getSamlOptionsFromForm(configData);

    if (isCurrentStateSaved(configData.passphrase, configData.users, configData.ldap_options, configData.saml_options)) {
        setStatusOk();
    } else {
        // Эта ветка может сработать, если при рендеринге данные были нормализованы
        // (например, null стал пустой строкой), что считается изменением.
        log('CONF', 'Initial state differs from saved state after render, setting status to EDIT.');
        setStatusEdit();
    }
}

function attachGlobalButtonHandlers() {
    document.getElementById("logoBtn").onclick = () => {
        window.location.href = constants.URL_PAGE_HOME;
    }
    document.getElementById("logoutBtn").addEventListener('click', () => {
        log('CONF', 'Нажата кнопка "Выход" — переход на /auth/logout');
        stopTokenRefresh();
        window.location.href = '/auth/logout';
    });
}

function attachConfButtonHandlers(data) {
    if (!data) return

    document.getElementById("addUserBtn").onclick = async () => {
        if (accessDenied) return;
        log('CONF', 'Нажата кнопка "Добавить пользователя"');

        if (!await preAddValidationCheck(data)) return;

        data.users.push({username: "", password_hash: "", permissions: [constants.PERM_LOGS]});
        renderUsers(data.users);

        setTimeout(() => {
            const userRows = document.querySelectorAll('.user-entry');
            if (userRows.length > 0) {
                const entryRow = userRows[userRows.length - 1];
                const nameInput = entryRow.querySelector('.user-name-input');
                if (nameInput) {
                    nameInput.focus();
                }
                animateEntryChildren(entryRow, constants.ANIMATION_ADD);
            }
        }, constants.ANIMATION_DELAY_MS);
    };
}

/**
 * Инициализирует страницу настроек: проверяет авторизацию, загружает данные,
 * рендерит компоненты и настраивает обработчики событий. При отказе в доступе
 * скрывает функциональные элементы и показывает сообщение.
 *
 * @return {Promise<void>}
 */
async function initConf() {
    log('CONF', 'DOM loaded, старт инициализации');
    attachGlobalButtonHandlers();
    const valid = await checkToken();
    if (!valid) {
        await logout();
        window.location.replace(constants.URL_LOGOUT_CONF);
        return;
    }

    initNavMenu(); // Навигация должна работать всегда

    let data;
    try {
        data = await fetchConfig();
        // setStatusOk() будет вызван позже, после полного рендеринга
        updateLastSavedState(data.passphrase, data.users, data.ldap_options, data.saml_options);
        const confMenuContainer = document.getElementById('confMenuContainer');
        if (confMenuContainer) {
            confMenuContainer.classList.remove('hidden');
        }
    } catch (e) {
        let msg = constants.MSG_CONF_LOAD_ERROR;
        if (
            (e?.status === 403) ||
            (e?.detail && typeof e.detail === "string" && e.detail.includes("permission"))
        ) {
            msg = constants.MSG_CONF_ACCESS_DENIED;
        } else if (e?.detail) {
            msg = String(e.detail);
        }
        accessDenied = true;
        showAccessMessage(msg, '.conf-container');
        return; // Прерываем выполнение, если нет данных
    }

    attachConfButtonHandlers(data);

    initConfMenu();
    data.passphrase = data.passphrase || "";
    data.users = Array.isArray(data.users) ? data.users : [];
    data.ldap_options = typeof data.ldap_options === 'object' && data.ldap_options !== null ? data.ldap_options : {};
    data.saml_options = typeof data.saml_options === 'object' && data.saml_options !== null ? data.saml_options : {};

    // Сначала рендерим содержимое во все контейнеры
    renderPassphrase(data.passphrase, data);
    renderUsers(data.users);
    renderLdapOptions(data.ldap_options, data);
    renderSamlOptions(data);

    // Финальная проверка статуса ПОСЛЕ рендеринга всех компонентов
    checkInitialStatus(data);

    // Только после рендеринга показываем родительские блоки
    document.querySelectorAll('.conf-group.hidden').forEach(el => el.classList.remove('hidden'));

    ["addUserBtn"].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.className = "conf-btn";
    });

    startTokenRefresh(constants.URL_LOGOUT_CONF);
    log('CONF', 'Инициализация завершена');
}

export {initConf};