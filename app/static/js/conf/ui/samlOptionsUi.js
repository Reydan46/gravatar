import {log} from '../../share/logger.js';
import {generateCertFromKey, generatePrivateKey, updateConfig} from "../api.js";
import {constants} from "../../share/constants.js";
import {setStatusEdit, setStatusError, setStatusOk} from "./statusUi.js";
import {getLastSaved, isCurrentStateSaved, updateLastSavedState} from "../state.js";
import {highlightInput} from "./commonUi.js";
import {validateSamlOptions} from "../validate.js";
import {showTooltip, hideTooltip} from "../../share/tooltip.js";
import {showMetadataModal} from "./metadataModalUi.js";

/**
 * Обновляет видимость опций SAML и кнопки "Показать метаданные".
 */
function toggleSamlOptionsVisibility() {
    const container = document.getElementById('samlOptionsContainer');
    const enabledCheckbox = document.getElementById('samlEnabled');
    if (container && enabledCheckbox) {
        container.classList.toggle('saml-enabled', enabledCheckbox.checked);
    }
}

/**
 * Рендерит UI для настроек SAML.
 * @param {object} fullConfigData - Полный объект конфигурации.
 */
function renderSamlOptions(fullConfigData) {
    const container = document.getElementById('samlOptionsContainer');
    if (!container) {
        log('CONF', 'SAML options container not found!', 'error');
        return;
    }

    const samlOptions = fullConfigData.saml_options || {};
    const sp = samlOptions.sp || {};
    const idp = samlOptions.idp || {};
    const security = samlOptions.security || {};

    container.innerHTML = `
        <div class="conf-group-header">
             <div class="header-left-content" style="display: flex; align-items: center; gap: 10px;">
                <h4>Основные параметры</h4>
                <button id="showMetadataBtn" class="btn btn-show-metadata btn-icon-text" title="Показать XML метаданные Service Provider">
                     <span>Metadata</span>
                </button>
            </div>
            <div class="saml-enable-toggle">
                <label for="samlEnabled" class="saml-enable-label-text">Включить SAML</label>
                <div class="toggle-switch">
                    <input type="checkbox" id="samlEnabled" ${samlOptions.enabled ? 'checked' : ''}>
                    <label for="samlEnabled" class="toggle-switch-label"></label>
                </div>
            </div>
        </div>
        <div class="conf-group-body saml-options-group">
            <h5>Service Provider (SP) - это приложение</h5>
            <div class="conf-row">
                <label for="spEntityId">Entity ID</label>
                <input type="text" id="spEntityId" value="${sp.entityId || ''}" placeholder="https://gravatar.example.com/saml/metadata">
            </div>
            <div class="conf-row">
                <label for="spAcsUrl">ACS URL</label>
                <input type="text" id="spAcsUrl" value="${sp.assertionConsumerService?.url || ''}" placeholder="https://gravatar.example.com/saml/acs">
            </div>
            <div class="conf-row">
                <label for="spSloUrl">SLS URL</label>
                <input type="text" id="spSloUrl" value="${sp.singleLogoutService?.url || ''}" placeholder="https://gravatar.example.com/saml/sls">
            </div>
            <div class="conf-row conf-row--textarea">
                <label for="spKey">Ключ SP</label>
                <div class="saml-textarea-wrapper">
                    <textarea id="spKey" placeholder="Приватный ключ Service Provider">${sp.privateKey || ''}</textarea>
                    <button id="generateSpKeyBtn" class="btn-icon-inline btn-generate-key" title="Сгенерировать новый приватный ключ">🔑</button>
                </div>
            </div>
            <div class="conf-row conf-row--textarea">
                <label for="spCert">Сертификат SP</label>
                <div class="saml-textarea-wrapper">
                    <textarea id="spCert" placeholder="Публичный сертификат Service Provider">${sp.x509cert || ''}</textarea>
                    <button id="generateSpCertBtn" class="btn-icon-inline btn-generate-key" title="Сгенерировать сертификат на основе ключа">🔑</button>
                </div>
            </div>

            <h5>Identity Provider (IdP) - внешний провайдер</h5>
            <div class="conf-row">
                <label for="idpEntityId">Entity ID</label>
                <input type="text" id="idpEntityId" value="${idp.entityId || ''}" placeholder="https://idp.example.com/idp/shibboleth">
            </div>
            <div class="conf-row">
                <label for="idpSsoUrl">SSO URL</label>
                <input type="text" id="idpSsoUrl" value="${idp.singleSignOnService?.url || ''}" placeholder="https://idp.example.com/idp/profile/SAML2/Redirect/SSO">
            </div>
             <div class="conf-row">
                <label for="idpSloUrl">SLO URL</label>
                <input type="text" id="idpSloUrl" value="${idp.singleLogoutService?.url || ''}" placeholder="https://idp.example.com/idp/profile/SAML2/Redirect/SLO">
            </div>
            <div class="conf-row conf-row--textarea">
                <label for="idpCert">Сертификат IdP</label>
                <textarea id="idpCert" placeholder="Вставьте сертификат IdP">${idp.x509cert || ''}</textarea>
            </div>

            <h5>Настройки безопасности</h5>
            <div class="security-options" id="securityOptionsContainer">
                <!-- Сюда будут вставлены группы с кнопками-переключателями -->
            </div>
        </div>
    `;

    const revalidateAndSetStatus = () => {
        const currentData = getSamlOptionsFromForm(fullConfigData);
        const validationError = validateSamlOptions(currentData);
        if (validationError) {
            setStatusError(`[SAML] ${validationError}`);
        } else {
            const lastSaved = getLastSaved();
            if (isCurrentStateSaved(lastSaved.passphrase, lastSaved.users, lastSaved.ldapOptions, currentData)) {
                setStatusOk();
            } else {
                setStatusEdit();
            }
        }
    };

    const saveSamlOptions = async (inputElement) => {
        fullConfigData.saml_options = getSamlOptionsFromForm(fullConfigData);
        const validationError = validateSamlOptions(fullConfigData.saml_options);
        if (validationError) {
            setStatusError(`[SAML] ${validationError}`);
            return false;
        }

        setStatusEdit();
        try {
            const res = await updateConfig({[constants.CONF_FIELD_SAML]: fullConfigData.saml_options});
            if (res?.error) {
                setStatusError(res.error);
                return false;
            } else {
                setStatusOk();
                const lastSaved = getLastSaved();
                updateLastSavedState(lastSaved.passphrase, lastSaved.users, lastSaved.ldapOptions, fullConfigData.saml_options);
                if (inputElement && inputElement.type !== 'checkbox') {
                    highlightInput(inputElement, 'input-highlight-success');
                }
                return true;
            }
        } catch (e) {
            setStatusError(e?.message || constants.MSG_CONF_UPDATE_ERROR);
            return false;
        }
    };

    // Helper to create a toggle button
    const createToggle = (key, value) => {
        const label = document.createElement('label');
        label.className = `security-toggle ${value ? 'active' : ''}`;
        label.dataset.tooltip = constants.SAML_SECURITY_TOOLTIPS[key] || '';
        label.textContent = key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `saml-toggle-${key}`;
        checkbox.checked = value;
        label.prepend(checkbox);

        label.addEventListener('click', (e) => {
            e.preventDefault();
            checkbox.checked = !checkbox.checked;
            label.classList.toggle('active', checkbox.checked);
            saveSamlOptions(checkbox);
        });

        label.addEventListener('mouseenter', (e) => showTooltip(e.currentTarget.dataset.tooltip, e));
        label.addEventListener('mousemove', (e) => showTooltip(null, e));
        label.addEventListener('mouseleave', hideTooltip);
        return label;
    };

    // Render security group toggles
    const securityContainer = document.getElementById('securityOptionsContainer');
    if (securityContainer && security && typeof security === 'object') {
        const securityGroups = {
            general: {
                title: 'Проверка подписи IdP',
                keys: ['wantMessagesSigned', 'wantAssertionsSigned'],
                class: ''
            },
            crypto: {
                title: 'Требуется ключ и сертификат SP (для подписи и шифрования)',
                keys: ['authnRequestsSigned', 'logoutRequestSigned', 'logoutResponseSigned', 'signMetadata', 'nameIdEncrypted', 'wantAssertionsEncrypted'],
                class: 'crypto-required'
            }
        };

        Object.values(securityGroups).forEach(group => {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'security-group';
            if (group.class) groupDiv.classList.add(group.class);

            const title = document.createElement('h6');
            title.textContent = group.title;
            groupDiv.appendChild(title);

            const contentDiv = document.createElement('div');
            contentDiv.className = 'security-group-content';

            group.keys.forEach(key => {
                const toggle = createToggle(key, security[key] === true);
                contentDiv.appendChild(toggle);
            });
            groupDiv.appendChild(contentDiv);
            securityContainer.appendChild(groupDiv);
        });
    }

    container.querySelectorAll('input[type="text"], textarea').forEach(input => {
        input.addEventListener('input', () => revalidateAndSetStatus());
        input.addEventListener('change', async () => saveSamlOptions(input));
    });

    document.getElementById('samlEnabled').addEventListener('change', (e) => {
        toggleSamlOptionsVisibility();
        saveSamlOptions(e.target);
    });

    document.getElementById('showMetadataBtn').addEventListener('click', showMetadataModal);

    document.getElementById('generateSpKeyBtn').addEventListener('click', async () => {
        try {
            const {private_key} = await generatePrivateKey();
            const spKeyEl = document.getElementById('spKey');
            spKeyEl.value = private_key;
            if (await saveSamlOptions(spKeyEl)) {
                highlightInput(spKeyEl, 'input-highlight-generated');
            }
        } catch (error) {
            setStatusError(error.message || 'Ошибка генерации приватного ключа.');
        }
    });

    document.getElementById('generateSpCertBtn').addEventListener('click', async () => {
        try {
            const spKeyEl = document.getElementById('spKey');
            let privateKey = spKeyEl.value.trim();

            if (!privateKey) {
                const generated = await generatePrivateKey();
                privateKey = generated.private_key;
                spKeyEl.value = privateKey;
                highlightInput(spKeyEl, 'input-highlight-generated');
            }

            const {certificate} = await generateCertFromKey(privateKey);
            const spCertEl = document.getElementById('spCert');
            spCertEl.value = certificate;

            if (await saveSamlOptions(spCertEl)) {
                highlightInput(spCertEl, 'input-highlight-generated');
            }
        } catch (error) {
            setStatusError(error.message || 'Ошибка генерации сертификата.');
        }
    });


    toggleSamlOptionsVisibility();
    log('CONF', 'SAML options UI rendered and handlers attached.');
}

/**
 * Собирает данные из формы настроек SAML, сохраняя неизменные поля.
 * @param {object} fullConfigData - Полный объект конфигурации для получения текущих значений.
 * @returns {object} - Объект с настройками SAML.
 */
function getSamlOptionsFromForm(fullConfigData) {
    const getNested = (obj, ...args) => args.reduce((o, level) => o && o[level], obj);
    const currentSettings = fullConfigData.saml_options || {};

    const securitySettings = {...(getNested(currentSettings, 'security') || {})};
    document.querySelectorAll('.security-group input[type="checkbox"]').forEach(chk => {
        const key = chk.id.replace('saml-toggle-', '');
        securitySettings[key] = chk.checked;
    });

    const data = {
        ...currentSettings,
        enabled: document.getElementById('samlEnabled').checked,
        sp: {
            ...(getNested(currentSettings, 'sp') || {}),
            entityId: document.getElementById('spEntityId').value.trim(),
            assertionConsumerService: {
                ...(getNested(currentSettings, 'sp', 'assertionConsumerService') || {}),
                url: document.getElementById('spAcsUrl').value.trim()
            },
            singleLogoutService: {
                ...(getNested(currentSettings, 'sp', 'singleLogoutService') || {}),
                url: document.getElementById('spSloUrl').value.trim()
            },
            x509cert: document.getElementById('spCert').value.trim(),
            privateKey: document.getElementById('spKey').value.trim()
        },
        idp: {
            ...(getNested(currentSettings, 'idp') || {}),
            entityId: document.getElementById('idpEntityId').value.trim(),
            singleSignOnService: {
                ...(getNested(currentSettings, 'idp', 'singleSignOnService') || {}),
                url: document.getElementById('idpSsoUrl').value.trim()
            },
            singleLogoutService: {
                ...(getNested(currentSettings, 'idp', 'singleLogoutService') || {}),
                url: document.getElementById('idpSloUrl').value.trim()
            },
            x509cert: document.getElementById('idpCert').value.trim()
        },
        security: securitySettings
    };
    return data;
}

export {renderSamlOptions, getSamlOptionsFromForm};