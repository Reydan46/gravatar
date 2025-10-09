import {constants} from "./constants.js";

/**
 Показывает сообщение об ограничении доступа в указанном контейнере.
 Заменяет содержимое контейнера сообщением и центрирует его.

 @param {string} message Текст сообщения
 @param {string} containerSelector CSS-селектор контейнера
 @return {void}
 */
function showAccessMessage(message, containerSelector) {
    const container = document.querySelector(containerSelector);
    if (container) {
        // Заменяем содержимое контейнера на сообщение об ошибке
        container.innerHTML = `<div class="access-denied-message">${message || constants.MSG_ACCESS_DENIED}</div>`;

        // Применяем стили для центрирования
        container.style.display = 'flex';
        container.style.alignItems = 'center';
        container.style.justifyContent = 'center';

        // Если это основной контейнер, заставляем его занять все доступное место
        if (container.classList.contains('conf-container') ||
            container.classList.contains('gallery-content-wrapper') ||
            container.classList.contains('logs-content-wrapper')) {
            container.style.flexGrow = '1';
        }

        // Для /conf отменяем многоколоночную верстку
        if (container.classList.contains('conf-container')) {
            container.style.columnCount = '1';
        }

        // Убираем класс 'hidden', если он есть, чтобы контейнер стал видимым
        container.classList.remove('hidden');
    }
}

export {showAccessMessage};