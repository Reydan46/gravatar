let tooltipElement;
let tooltipTimeout;

/**
 * Инициализирует и добавляет элемент тултипа в DOM.
 */
function initTooltip() {
    if (document.getElementById('universal-tooltip')) return;

    tooltipElement = document.createElement('div');
    tooltipElement.id = 'universal-tooltip';
    tooltipElement.className = 'tooltip';
    document.body.appendChild(tooltipElement);
}

/**
 * Показывает тултип с заданным текстом и позиционирует его.
 * @param {string|null} text - Текст для тултипа. Если null, только обновляется позиция.
 * @param {MouseEvent} event - Событие мыши для позиционирования.
 */
function showTooltip(text, event) {
    if (!tooltipElement) return;

    clearTimeout(tooltipTimeout);

    if (text !== null) {
        tooltipElement.textContent = text;
    }

    // Если текста нет, не показываем
    if (!tooltipElement.textContent) {
        hideTooltip();
        return;
    }

    tooltipElement.classList.add('show');

    // Позиционируем относительно курсора
    const x = event.clientX + 15;
    const y = event.clientY + 15;

    tooltipElement.style.left = `${x}px`;
    tooltipElement.style.top = `${y}px`;

    // Корректировка, если тултип выходит за пределы экрана
    const rect = tooltipElement.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
        tooltipElement.style.left = `${window.innerWidth - rect.width - 15}px`;
    }
    if (rect.bottom > window.innerHeight) {
        tooltipElement.style.top = `${window.innerHeight - rect.height - 15}px`;
    }
}

/**
 * Скрывает тултип.
 */
function hideTooltip() {
    if (!tooltipElement) return;

    clearTimeout(tooltipTimeout);
    tooltipTimeout = setTimeout(() => {
        tooltipElement.classList.remove('show');
    }, 100); // Небольшая задержка перед скрытием
}

export {initTooltip, showTooltip, hideTooltip};