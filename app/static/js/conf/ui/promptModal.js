import {constants} from '../../share/constants.js';
import {getEyeIconSVG} from './svg.js';

/**
 * Показывает модальное окно для ввода или подтверждения
 *
 * @param {string} label - Основное сообщение или заголовок запроса
 * @param {Object} [options={}] - Объект настроек:
 * @param {string} [options.help] - Мелкая подсказка под заголовком
 * @param {string} [options.error] - Текст ошибки (опционально)
 * @param {string} [options.mode="alert"] - Режим окна: "input_text", "input_password", "confirm", "alert"
 * @param {string} [options.placeholder] - Placeholder для поля ввода
 * @param {string} [options.defaultValue] - Значение по умолчанию для поля ввода
 * @param {string} [options.okLabel] - Текст кнопки OK
 * @param {string} [options.cancelLabel] - Текст кнопки отмены
 * @param {number} [options.maxLength] - Максимальная длина ввода
 * @param {boolean} [options.backdropClose=true] - Закрывать ли по клику на фон
 * @returns {Promise<string|boolean|null>} Возвращает введённое значение (для input), true (для confirm) или null (если отмена)
 */
function showPromptModal(label, options = {}) {
    return new Promise((resolve) => {
        const old = document.getElementById('promptModal')
        if (old) old.remove()

        const mode = options.mode || "alert"
        const hasInput = mode === 'input_text' || mode === 'input_password'
        const hasCancelButton = hasInput || mode === 'confirm'

        const modal = document.createElement('div')
        modal.id = 'promptModal'
        modal.className = 'prompt-modal'

        const backdrop = document.createElement('div')
        backdrop.className = 'prompt-modal__backdrop'
        if (options.backdropClose !== false) {
            backdrop.addEventListener('click', () => {
                modal.remove()
                resolve(null)
            })
        }
        modal.appendChild(backdrop)

        const box = document.createElement('div')
        box.className = 'prompt-modal__box'
        box.addEventListener('click', e => e.stopPropagation())

        // Сообщение/заголовок
        const labelEl = document.createElement('div')
        labelEl.className = 'prompt-modal__label'
        labelEl.textContent = label || ''
        if (options.help) labelEl.classList.add('prompt-modal__label--with-help')
        box.appendChild(labelEl)

        // Подпись
        if (options.help) {
            const helpEl = document.createElement('div')
            helpEl.className = 'prompt-modal__help'
            helpEl.textContent = options.help
            box.appendChild(helpEl)
        }

        // Ошибка
        if (options.error) {
            const errorEl = document.createElement('div')
            errorEl.className = 'prompt-modal__error'
            errorEl.textContent = options.error
            box.appendChild(errorEl)
        }

        let input, inputWrapper, eyeBtn, eyeIcon, isPasswordVisible = false

        if (mode === 'input_password') {
            inputWrapper = document.createElement('div')
            inputWrapper.className = 'prompt-modal__input-wrapper'

            input = document.createElement('input')
            input.type = 'password'
            input.value = options.defaultValue || ''
            input.placeholder = options.placeholder || ''
            if (typeof options.maxLength === 'number') input.maxLength = options.maxLength
            input.className = 'prompt-modal__input prompt-modal__input--password'

            eyeBtn = document.createElement('button')
            eyeBtn.type = 'button'
            eyeBtn.tabIndex = -1
            eyeBtn.className = 'prompt-modal__eye-btn'

            eyeIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
            eyeIcon.setAttribute('width', '22')
            eyeIcon.setAttribute('height', '22')
            eyeIcon.setAttribute('viewBox', '0 0 24 24')
            eyeIcon.innerHTML = getEyeIconSVG()

            eyeBtn.appendChild(eyeIcon)

            eyeBtn.addEventListener('click', () => {
                isPasswordVisible = !isPasswordVisible
                input.type = isPasswordVisible ? 'text' : 'password'
                eyeIcon.innerHTML = getEyeIconSVG(isPasswordVisible)
                input.focus()
                input.select()
            })

            inputWrapper.appendChild(input)
            inputWrapper.appendChild(eyeBtn)
            box.appendChild(inputWrapper)
            setTimeout(() => input.focus(), constants.FOCUS_TIMEOUT_MS)
            input.addEventListener("focus", () => input.select())
        } else if (mode === 'input_text') {
            input = document.createElement('input')
            input.type = 'text'
            input.value = options.defaultValue || ''
            input.placeholder = options.placeholder || ''
            if (typeof options.maxLength === 'number') input.maxLength = options.maxLength
            input.className = 'prompt-modal__input'
            box.appendChild(input)
            setTimeout(() => input.focus(), constants.FOCUS_TIMEOUT_MS)
            input.addEventListener("focus", () => input.select())
        }

        const btnRow = document.createElement('div')
        btnRow.className = 'prompt-modal__btn-row'

        const btnOk = document.createElement('button')
        btnOk.type = 'button'
        btnOk.textContent = options.okLabel || constants.PROMPT_LABEL_OK
        btnOk.className = 'shared-btn'
        btnOk.onclick = () => {
            modal.remove()
            if (hasInput) {
                resolve(input.value)
            } else if (mode === 'confirm') {
                resolve(true);
            } else { // alert
                resolve(true);
            }
        }
        btnRow.appendChild(btnOk)

        if (hasCancelButton) {
            const btnCancel = document.createElement('button')
            btnCancel.type = 'button'
            btnCancel.textContent = options.cancelLabel || constants.PROMPT_LABEL_CANCEL
            btnCancel.className = 'shared-btn'
            btnCancel.onclick = () => {
                modal.remove()
                resolve(null)
            }
            btnRow.appendChild(btnCancel)
        }

        box.appendChild(btnRow)

        const handleKeyDown = (e) => {
            if (e.key === 'Enter') btnOk.click()
            if (e.key === 'Escape' && hasCancelButton) {
                const btnCancel = btnRow.querySelector('.shared-btn:last-child');
                if (btnCancel) btnCancel.click();
            }
        };

        if (hasInput) {
            input.addEventListener('keydown', handleKeyDown);
        } else {
            box.addEventListener('keydown', handleKeyDown);
            setTimeout(() => box.focus(), constants.FOCUS_TIMEOUT_MS)
            box.tabIndex = -1
        }

        modal.appendChild(box)
        document.body.appendChild(modal)
    })
}

export {showPromptModal}