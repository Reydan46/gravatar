import {updateConfig} from '../api.js';
import {validatePassphrase} from '../validate.js';
import {setStatusOk, setStatusEdit, setStatusError} from './statusUi.js';
import {updateLastSavedState, isCurrentStateSaved, getLastSaved} from '../state.js';
import {highlightInput} from './commonUi.js';
import {generateRandomString} from '../../share/textUtils.js';
import {constants} from "../../share/constants.js";
import {getEyeIconSVG} from "./svg.js";

/**
 * Рендерит поле для passphrase и навешивает обработчики.
 * @param {string} passphrase - Текущий passphrase.
 * @param {Object} fullConfigData - Полный объект конфигурации для сохранения.
 */
function renderPassphrase(passphrase, fullConfigData) {
    const container = document.getElementById("passphraseContainer");
    container.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "conf-entry passphrase-wrapper";

    const passInput = document.createElement("input");
    passInput.type = "password";
    passInput.value = passphrase || "";
    passInput.className = "passphrase-input";
    passInput.placeholder = "Введите основной пароль...";
    passInput.autocomplete = "new-password";

    const revalidate = () => {
        const error = validatePassphrase(fullConfigData.passphrase);
        const isError = !!error;
        passInput.classList.toggle('input-error', isError);

        if (error) {
            setStatusError(`[Passphrase] ${error}`);
        } else {
            const lastSaved = getLastSaved();
            if (isCurrentStateSaved(fullConfigData.passphrase, fullConfigData.users, fullConfigData.ldap_options, fullConfigData.saml_options)) {
                setStatusOk();
            } else {
                setStatusEdit();
            }
        }
    };

    const savePassphrase = async () => {
        const err = validatePassphrase(fullConfigData.passphrase);
        if (err) {
            setStatusError(`[Passphrase] ${err}`);
            revalidate();
            return false;
        }
        setStatusEdit();
        try {
            const res = await updateConfig(fullConfigData);
            if (res?.error) {
                setStatusError(res.error);
            } else {
                setStatusOk();
                updateLastSavedState(fullConfigData.passphrase, fullConfigData.users, fullConfigData.ldap_options, fullConfigData.saml_options);
                return true;
            }
        } catch (e) {
            setStatusError(e?.message || constants.MSG_CONF_UPDATE_ERROR);
        }
        return false;
    };

    passInput.addEventListener("input", (e) => {
        fullConfigData.passphrase = e.target.value;
        revalidate();
    });

    passInput.addEventListener("change", async (e) => {
        fullConfigData.passphrase = e.target.value.trim();
        passInput.value = fullConfigData.passphrase;
        if (await savePassphrase()) {
            highlightInput(passInput, 'input-highlight-success');
        }
    });

    passInput.addEventListener("blur", () => {
        revalidate();
    });

    wrapper.appendChild(passInput);

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
        passInput.type = isPasswordVisible ? 'text' : 'password';
        eyeIcon.innerHTML = getEyeIconSVG(isPasswordVisible);
    });
    wrapper.appendChild(eyeBtn);

    const btnGenPass = document.createElement("button");
    btnGenPass.title = "Сгенерировать Passphrase";
    btnGenPass.innerHTML = "🔑";
    btnGenPass.type = "button";
    btnGenPass.className = "btn-hash small";
    btnGenPass.addEventListener("click", async () => {
        const newPass = generateRandomString(24, constants.API_KEY_CHARS);
        passInput.value = newPass;
        fullConfigData.passphrase = newPass;
        revalidate();
        if (await savePassphrase()) {
            highlightInput(passInput, 'input-highlight-generated');
        }
    });

    wrapper.appendChild(btnGenPass);
    container.appendChild(wrapper);

    revalidate();
}

export {renderPassphrase};