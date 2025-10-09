import {checkLdapConnection, syncAvatars, updateConfig} from '../api.js';
import {validateLdapOptions} from '../validate.js';
import {setStatusOk, setStatusEdit, setStatusError} from './statusUi.js';
import {updateLastSavedState, isCurrentStateSaved, getLastSaved} from '../state.js';
import {highlightInput, setInputErrorState} from './commonUi.js';
import {getEyeIconSVG} from './svg.js';
import {constants} from '../../share/constants.js';
import {log} from '../../share/logger.js';

/**
 * Устанавливает статус проверки LDAP.
 * @param {'idle'|'checking'|'ok'|'error'|'progress'} state - Состояние.
 * @param {string} [message=''] - Сообщение.
 */
function setLdapCheckStatus(state, message = '') {
    const statusEl = document.getElementById('ldapStatus');
    if (!statusEl) return;

    let icon = '';
    let text = message;

    switch (state) {
        case 'checking':
            icon = '⏳';
            text = 'Проверка...';
            break;
        case 'ok':
            icon = '✔️';
            text = message || 'Подключение успешно';
            break;
        case 'error':
            icon = '❌';
            break;
        case 'progress':
            icon = '⏳';
            break;
        case 'idle':
        default:
            statusEl.innerHTML = '';
            statusEl.className = 'ldap-status';
            return;
    }

    statusEl.className = `ldap-status ${state}`;
    statusEl.innerHTML = `
        <span class="ldap-status-icon">${icon}</span>
        <span class="ldap-status-text">${text}</span>
    `;
}


/**
 * Рендерит поля для настроек LDAP и навешивает обработчики.
 * @param {Object} ldapOptionsData - Объект с данными LDAP.
 * @param {Object} fullConfigData - Полный объект конфигурации для сохранения.
 */
function renderLdapOptions(ldapOptionsData, fullConfigData) {
    const container = document.getElementById("ldapOptionsContainer");
    container.innerHTML = "";

    const fieldOrder = ['LDAP_SERVER', 'LDAP_USERNAME', 'LDAP_PASSWORD', 'LDAP_SEARCH_BASE'];
    const labels = constants.UI_LABELS.LDAP;
    const placeholders = constants.UI_LABELS.LDAP.PLACEHOLDERS;

    const syncBtn = document.getElementById('syncAvatarsBtn');
    const checkBtn = document.getElementById('checkLdapBtn');

    const revalidateAndHighlight = () => {
        const options = fullConfigData.ldap_options;
        const server = (options.LDAP_SERVER || "").trim();
        const username = (options.LDAP_USERNAME || "").trim();
        const searchBase = (options.LDAP_SEARCH_BASE || "").trim();

        const isServerError = server && !constants.REGEX.HOSTNAME.test(server);
        setInputErrorState(document.getElementById('ldap-input-LDAP_SERVER'), isServerError);

        const isUsernameError = !username;
        setInputErrorState(document.getElementById('ldap-input-LDAP_USERNAME'), isUsernameError);

        const isBaseError = searchBase && !constants.REGEX.DISTINGUISHED_NAME.test(searchBase);
        setInputErrorState(document.getElementById('ldap-input-LDAP_SEARCH_BASE'), isBaseError);

        setInputErrorState(document.getElementById('ldap-input-LDAP_PASSWORD'), false);

        updateOverallStatus();
    };

    const updateOverallStatus = () => {
        const globalError = validateLdapOptions(fullConfigData.ldap_options);
        if (globalError) {
            setStatusError(`[Подключение к Active Directory] ${globalError}`);
        } else {
            const lastSaved = getLastSaved();
            if (isCurrentStateSaved(lastSaved.passphrase, lastSaved.users, fullConfigData.ldap_options, fullConfigData.saml_options)) {
                setStatusOk();
            } else {
                setStatusEdit();
            }
        }
    };

    const saveLdapOptions = async () => {
        const globalError = validateLdapOptions(fullConfigData.ldap_options);
        if (globalError) {
            setStatusError(`[Подключение к Active Directory] ${globalError}`);
            revalidateAndHighlight();
            return false;
        }

        setStatusEdit();
        try {
            const res = await updateConfig({[constants.CONF_FIELD_LDAP]: fullConfigData.ldap_options});
            if (res?.error) {
                setStatusError(res.error);
            } else {
                setStatusOk();
                const lastSaved = getLastSaved();
                updateLastSavedState(lastSaved.passphrase, lastSaved.users, fullConfigData.ldap_options, lastSaved.saml_options);
                return true;
            }
        } catch (e) {
            setStatusError(e?.message || constants.MSG_CONF_UPDATE_ERROR);
        }
        return false;
    };

    fieldOrder.forEach(fieldKey => {
        const isPasswordField = fieldKey.includes('PASSWORD');

        const label = document.createElement("label");
        label.className = "ldap-label";
        label.textContent = labels.FIELDS[fieldKey] || fieldKey;
        label.htmlFor = `ldap-input-${fieldKey}`;

        const wrapper = document.createElement("div");
        wrapper.className = "ldap-input-wrapper";

        const input = document.createElement("input");
        input.id = `ldap-input-${fieldKey}`;
        input.type = isPasswordField ? "password" : "text";
        input.value = ldapOptionsData[fieldKey] !== undefined ? ldapOptionsData[fieldKey] : '';
        input.className = "ldap-input";
        input.placeholder = placeholders[fieldKey] || '';
        input.autocomplete = "off";

        input.addEventListener("input", () => {
            fullConfigData.ldap_options[fieldKey] = input.value;
            revalidateAndHighlight();
            setLdapCheckStatus('idle');
            syncBtn.disabled = true;
        });

        input.addEventListener("change", async (event) => {
            fullConfigData.ldap_options[fieldKey] = event.target.value.trim();
            event.target.value = fullConfigData.ldap_options[fieldKey];
            revalidateAndHighlight();
            if (await saveLdapOptions()) {
                highlightInput(input, 'input-highlight-success');
            }
        });

        wrapper.appendChild(input);

        if (isPasswordField) {
            const eyeBtn = document.createElement('button');
            eyeBtn.type = 'button';
            eyeBtn.tabIndex = -1;
            eyeBtn.className = 'btn-eye small';
            eyeBtn.title = 'Показать/скрыть пароль';

            const eyeIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            eyeIcon.setAttribute('width', '22');
            eyeIcon.setAttribute('height', '22');
            eyeIcon.setAttribute('viewBox', '0 0 24 24');
            eyeIcon.innerHTML = getEyeIconSVG();
            eyeBtn.appendChild(eyeIcon);

            let isPasswordVisible = false;
            eyeBtn.addEventListener('click', () => {
                isPasswordVisible = !isPasswordVisible;
                input.type = isPasswordVisible ? 'text' : 'password';
                eyeIcon.innerHTML = getEyeIconSVG(isPasswordVisible);
            });
            wrapper.appendChild(eyeBtn);
        }

        container.appendChild(label);
        container.appendChild(wrapper);
    });

    checkBtn.addEventListener('click', async () => {
        const globalError = validateLdapOptions(fullConfigData.ldap_options);
        if (globalError) {
            setLdapCheckStatus('error', 'Сначала исправьте ошибки в полях');
            syncBtn.disabled = true;
            return;
        }

        setLdapCheckStatus('checking');
        syncBtn.disabled = true;
        checkBtn.disabled = true;
        try {
            const result = await checkLdapConnection(fullConfigData.ldap_options);
            if (result.success) {
                setLdapCheckStatus('ok', result.message);
                syncBtn.disabled = false;
            } else {
                setLdapCheckStatus('error', result.message);
                syncBtn.disabled = true;
            }
        } catch (e) {
            log('Error checking LDAP connection', e, 'error');
            setLdapCheckStatus('error', e.message || 'Ошибка сети');
            syncBtn.disabled = true;
        } finally {
            checkBtn.disabled = false;
        }
    });

    syncBtn.addEventListener('click', async () => {
        checkBtn.disabled = true;
        syncBtn.disabled = true;

        syncAvatars(
            fullConfigData.passphrase,
            (data) => {
                const statusMap = {
                    starting: 'progress',
                    fetching: 'progress',
                    processing: 'progress',
                    progress: 'progress',
                    completed: 'ok',
                    error: 'error'
                };
                const state = statusMap[data.status] || 'progress';
                setLdapCheckStatus(state, data.message);
            },
            () => {
                checkBtn.disabled = false;
                const statusEl = document.getElementById('ldapStatus');
                if (statusEl && statusEl.classList.contains('ok')) {
                    syncBtn.disabled = false;
                }
            },
            (errorMessage) => {
                setLdapCheckStatus('error', errorMessage);
            }
        );
    });

    revalidateAndHighlight();
}

export {renderLdapOptions};