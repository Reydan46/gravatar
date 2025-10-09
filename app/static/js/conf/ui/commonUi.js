import {constants} from "../../share/constants.js";

/**
 * Анимация появления/удаления строки таблицы
 *
 * :param entryRow: DOM-элемент строки
 * :param animation: 'add' | 'remove'
 */
function animateEntryChildren(entryRow, animation) {
    if (!entryRow) return
    const cls = animation === constants.ANIMATION_REMOVE ? 'animate-entry-child-remove' : 'animate-entry-child-add'
    const duration = animation === constants.ANIMATION_REMOVE
        ? constants.ENTRY_ANIMATION_REMOVE_DURATION
        : constants.ENTRY_ANIMATION_ADD_DURATION

    const children = entryRow.querySelectorAll('input, button')
    children.forEach(el => {
        el.style.animationDuration = `${duration}ms`
        el.classList.add(cls)
        setTimeout(() => {
            el.classList.remove(cls)
            el.style.animationDuration = ''
        }, duration)
    })

    if (animation === constants.ANIMATION_ADD) {
        const firstInput = entryRow.querySelector('input')
        if (firstInput) {
            firstInput.focus()
            firstInput.scrollIntoView({behavior: 'smooth', block: 'center'})
        }
    }
}

/**
 * Подсвечивает инпут на короткое время, добавляя CSS-класс
 * @param {HTMLInputElement} input - Элемент инпута
 * @param {string} highlightClass - CSS-класс для подсветки
 */
function highlightInput(input, highlightClass) {
    if (!input) return;
    input.classList.remove('input-highlight-success', 'input-highlight-generated');
    requestAnimationFrame(() => {
        input.classList.add(highlightClass);
        setTimeout(() => {
            input.classList.remove(highlightClass);
        }, constants.INPUT_HIGHLIGHT_DURATION_MS);
    });
}

/**
 * Устанавливает или снимает состояние ошибки для инпута
 * @param {HTMLInputElement} input - Элемент инпута
 * @param {boolean} isError - true, если есть ошибка
 */
function setInputErrorState(input, isError) {
    if (!input) return;
    input.classList.toggle('input-error', isError);
}


export {animateEntryChildren, highlightInput, setInputErrorState};