import {log} from './logger.js';
import {constants} from './constants.js';

/**
 * Инициализирует выпадающее меню с поведением по наведению или клику.
 *
 * @param {string} containerId - ID элемента-контейнера меню.
 * @param {string} buttonId - ID кнопки, открывающей меню.
 * @param {string} listId - ID элемента-списка (выпадающей части).
 * @param {boolean} openOnHover - true для открытия по наведению, false для клика.
 */
function initializeMenu(containerId, buttonId, listId, openOnHover) {
    const menuContainer = document.getElementById(containerId);
    const menuBtn = document.getElementById(buttonId);
    const menuList = document.getElementById(listId);

    if (!menuContainer || !menuBtn || !menuList) {
        log('SHARE', `Menu elements not found for container #${containerId}`, 'warn');
        return;
    }

    let menuHideTimeout = null;

    const showMenu = () => {
        clearTimeout(menuHideTimeout);
        // Сначала скроем другие открытые меню, если они есть
        document.querySelectorAll('.nav-menu-list.show').forEach(otherMenu => {
            if (otherMenu !== menuList) {
                otherMenu.classList.remove('show');
            }
        });
        menuList.classList.add('show');
    };

    const hideMenu = () => {
        menuHideTimeout = setTimeout(() => {
            menuList.classList.remove('show');
        }, constants.TIME_NAV_MENU_HIDE_DELAY);
    };

    if (openOnHover) {
        menuContainer.addEventListener('mouseenter', showMenu);
        menuContainer.addEventListener('mouseleave', hideMenu);
    } else {
        menuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            menuList.classList.contains('show') ? hideMenu() : showMenu();
        });
    }
}

// Глобальный слушатель для закрытия меню по клику вне его области
document.addEventListener('click', (e) => {
    document.querySelectorAll('.nav-menu-container').forEach(container => {
        if (!container.contains(e.target)) {
            const list = container.querySelector('.nav-menu-list');
            if (list && list.classList.contains('show')) {
                list.classList.remove('show');
            }
        }
    });
});

export {initializeMenu};