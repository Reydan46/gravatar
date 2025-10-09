import { updateConfig } from '../api.js'
import { generatePasswordHash } from '../passwordHash.js'
import { validateUsers } from '../validate.js'
import { setStatusOk, setStatusEdit, setStatusError } from './statusUi.js'
import { updateLastSavedState, isCurrentStateSaved, getLastSaved } from '../state.js'
import { animateEntryChildren, highlightInput } from './commonUi.js'
import { setScrollbarCompensatorWidth } from './scrollbar.js'
import { showPromptModal } from './promptModal.js'
import { revalidateAndHighlightEntries } from './validationHelper.js';
import { constants } from "../../share/constants.js";
import { debounce } from "../../share/debounce.js";

/**
 * Валидатор для одной записи пользователя. Подсвечивает все некорректные поля.
 * @param {Object} currentUser - Текущий пользователь.
 * @param {number} index - Индекс пользователя.
 * @param {Array<Object>} allUsers - Массив всех пользователей.
 * @returns {Array<{selector: string, isError: boolean}>} - Результаты валидации для подсветки.
 */
function singleUserValidator(currentUser, index, allUsers) {
    const user = currentUser || {};
    const username = (user.username || '').trim();

    // Оцениваем все условия независимо для полной подсветки
    const isUsernameEmpty = !username;
    const isUsernameDuplicate = username && allUsers.some((u, i) => i !== index && (u.username || '').trim() === username);
    const isPasswordEmpty = !(user.password_hash || '').trim();

    return [
        {selector: '.user-name-input', isError: isUsernameEmpty || isUsernameDuplicate},
        {selector: '.password-hash-input', isError: isPasswordEmpty}
    ];
}


/**
 * Рендерит список пользователей и навешивает обработчики
 *
 * @param {Array<Object>} users - Список пользователей
 */
function renderUsers(users) {
    users = Array.isArray(users) ? users : [];
    const list = document.getElementById("usersList");
    list.innerHTML = "";

    let isSaving = false;
    let isDirty = false;

    const revalidate = () => revalidateAndHighlightEntries(
        '.user-entry',
        users,
        singleUserValidator,
        validateUsers,
        '[Пользователи]',
        'users'
    );

    const saveUserData = async () => {
        if (isSaving) {
            isDirty = true; // Отмечаем, что есть изменения, которые нужно сохранить позже
            return false;
        }

        const globalErr = validateUsers(users);
        if (globalErr) {
            setStatusError(`[Пользователи] ${globalErr}`);
            revalidate();
            return false;
        }

        isSaving = true;
        setStatusEdit();

        try {
            const res = await updateConfig({ [constants.CONF_FIELD_USERS]: users });
            if (res?.error) {
                setStatusError(res.error);
                return false;
            } else {
                setStatusOk();
                const lastSaved = getLastSaved();
                updateLastSavedState(lastSaved.passphrase, users, lastSaved.ldapOptions, lastSaved.samlOptions);
                return true;
            }
        } catch (e) {
            setStatusError(e?.message || constants.MSG_CONF_UPDATE_ERROR);
            return false;
        } finally {
            isSaving = false;
            // Если за время сохранения были еще изменения, запускаем сохранение снова
            if (isDirty) {
                isDirty = false;
                await debouncedSave();
            }
        }
    };

    const debouncedSave = debounce(saveUserData, constants.DEBOUNCE_PERMISSION_SAVE_MS);

    users.forEach((userOrig, idx) => {
        const user = userOrig && typeof userOrig === 'object' ? userOrig : {
            username: '',
            password_hash: '',
            permissions: []
        };
        const div = document.createElement("div");
        div.className = "conf-entry user-entry";
        div.dataset.index = String(idx);

        const userInput = document.createElement("input");
        userInput.value = user.username || "";
        userInput.className = "user-name-input";
        userInput.type = "text";
        userInput.autocomplete = "username";

        const hashInput = document.createElement("input");
        hashInput.type = "text";
        hashInput.value = user.password_hash || "";
        hashInput.className = "password-hash-input";
        hashInput.style.fontFamily = "monospace";
        hashInput.placeholder = "Hash пароля";

        const handleBlur = () => {
            const lastSaved = getLastSaved();
            if (isCurrentStateSaved(lastSaved.passphrase, users, lastSaved.ldapOptions, lastSaved.samlOptions) && !validateUsers(users)) {
                setStatusOk();
            }
        };

        userInput.addEventListener("input", () => {
            users[idx].username = userInput.value;
            revalidate();
        });
        userInput.addEventListener("change", async () => {
            users[idx].username = userInput.value.trim();
            userInput.value = users[idx].username;
            if (await saveUserData()) {
                highlightInput(userInput, 'input-highlight-success');
            }
        });
        userInput.addEventListener("blur", handleBlur);

        hashInput.addEventListener("input", () => {
            users[idx].password_hash = hashInput.value;
            revalidate();
        });
        hashInput.addEventListener("change", async () => {
            users[idx].password_hash = hashInput.value.trim();
            hashInput.value = users[idx].password_hash;
            if (await saveUserData()) {
                highlightInput(hashInput, 'input-highlight-success');
            }
        });
        hashInput.addEventListener("blur", handleBlur);

        div.appendChild(userInput);
        div.appendChild(hashInput);

        const btnHash = document.createElement("button");
        btnHash.title = "Генерировать hash";
        btnHash.innerHTML = "🔑";
        btnHash.className = "btn-hash small";
        btnHash.addEventListener("click", async () => {
            const pass = await showPromptModal("Введите новый пароль для пользователя:", {
                mode: constants.PROMPT_MODE_INPUT_PASSWORD,
                placeholder: "Введите пароль",
                maxLength: 48,
                backdropClose: true,
                username: user.username || userInput.value
            });
            if (pass === null) return;
            const hash = await generatePasswordHash(pass);
            hashInput.value = hash;
            users[idx].password_hash = hash;
            revalidate();
            if (await saveUserData()) {
                highlightInput(hashInput, 'input-highlight-generated');
            }
        });
        div.appendChild(btnHash);

        [constants.PERM_LOGS, constants.PERM_GALLERY, constants.PERM_SETTINGS].forEach((perm) => {
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "perm-checkbox";
            checkbox.checked = (user.permissions || []).includes(perm);
            checkbox.title = constants.PERM_TITLES[perm] || perm;
            checkbox.addEventListener("change", () => {
                let permsUpd = [...(users[idx].permissions || [])];
                if (checkbox.checked) {
                    if (!permsUpd.includes(perm)) permsUpd.push(perm);
                } else {
                    permsUpd = permsUpd.filter(p => p !== perm);
                }
                users[idx].permissions = permsUpd;
                void debouncedSave(); // Используем debounced-версию
            });
            const td = document.createElement("span");
            td.className = "perm-checkbox-cell";
            td.appendChild(checkbox);
            div.appendChild(td);
        });

        const btnDel = document.createElement("button");
        btnDel.innerHTML = "✗";
        btnDel.title = "Удалить пользователя";
        btnDel.className = "btn-del small";
        btnDel.addEventListener("click", () => {
            animateEntryChildren(div, constants.ANIMATION_REMOVE);
            setTimeout(() => {
                users.splice(idx, 1);
                renderUsers(users); // Полная перерисовка для обновления индексов и состояний
                const err = validateUsers(users);
                if (err) {
                    setStatusError(`[Пользователи] ${err}`);
                } else {
                    void saveUserData();
                }
            }, constants.ENTRY_ANIMATION_REMOVE_DURATION);
        });
        div.appendChild(btnDel);

        list.appendChild(div);
    });

    revalidateAndHighlightEntries(
        '.user-entry',
        users,
        singleUserValidator,
        validateUsers,
        '[Пользователи]',
        'users'
    );

    requestAnimationFrame(() => setScrollbarCompensatorWidth(list));
}

export { renderUsers };