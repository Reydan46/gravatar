/**
 * Управляет модальным окном справки по фильтрации.
 */

import {getElements} from './ui.js';

/**
 * Показывает модальное окно справки по фильтрации.
 * @returns {void}
 */
function showFilterHelpModal() {
    const elements = getElements();
    if (elements.filterHelpModal) {
        elements.filterHelpModal.style.display = 'flex';
    }
}

/**
 * Скрывает модальное окно справки по фильтрации.
 * @returns {void}
 */
function hideFilterHelpModal() {
    const elements = getElements();
    if (elements.filterHelpModal) {
        elements.filterHelpModal.style.display = 'none';
    }
}

/**
 * Инициализирует обработчики для модального окна справки.
 * @returns {void}
 */
function initFilterHelpModal() {
    const elements = getElements();
    const closeBtn = document.getElementById('closeFilterHelpModalBtn');

    if (closeBtn) {
        closeBtn.addEventListener('click', hideFilterHelpModal);
    }

    if (elements.filterHelpModal) {
        elements.filterHelpModal.addEventListener('click', (e) => {
            if (e.target === elements.filterHelpModal) {
                hideFilterHelpModal();
            }
        });
    }
}

export {initFilterHelpModal, showFilterHelpModal};