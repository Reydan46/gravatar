/**
 * Скрывает элементы управления логами при недостатке прав
 *
 * @return {void}
 */
function hideLogsAccessControls() {
    const menu = document.getElementById("logsMenuContainer");
    if (menu) menu.classList.add('hidden');

    const filterContainer = document.querySelector('.filter-container');
    if (filterContainer) filterContainer.classList.add('hidden');
}

/**
 * Показывает элементы управления логами, если есть права
 *
 * @return {void}
 */
function showLogsAccessControls() {
    const menu = document.getElementById("logsMenuContainer");
    if (menu) menu.classList.remove('hidden');

    const filterContainer = document.querySelector('.filter-container');
    if (filterContainer) filterContainer.classList.remove('hidden');
}

export {hideLogsAccessControls, showLogsAccessControls};