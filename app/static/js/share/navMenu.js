import {log} from './logger.js';
import {constants} from './constants.js';
import {initializeMenu} from './menuHandler.js';

/**
 * Инициализирует основное навигационное меню
 */
function initNavMenu() {
    log('SHARE', 'Инициализация навигационного меню');
    const menuList = document.getElementById('navMenuList');
    if (!menuList) {
        log('SHARE', 'Элемент navMenuList не найден', 'warn');
        return;
    }

    const currentPage = document.body.dataset.page;
    const menuItems = [
        {
            label: 'Просмотр логов',
            href: constants.URL_PAGE_LOGS,
            page: 'logs',
            icon: '📝'
        },
        {
            label: 'Галерея',
            href: constants.URL_PAGE_GALLERY,
            page: 'gallery',
            icon: '🖼️'
        },
        {
            label: 'Настройки',
            href: constants.URL_PAGE_CONF,
            page: 'conf',
            icon: '🔧'
        }
    ];

    menuList.innerHTML = '';
    menuItems.forEach(item => {
        if (item.page !== currentPage) {
            const li = document.createElement('li');
            li.innerHTML = `<span class="nav-menu-icon">${item.icon}</span> ${item.label}`;
            li.onclick = () => {
                window.location.href = item.href;
            };
            menuList.appendChild(li);
        }
    });

    // Используем универсальный обработчик
    initializeMenu(
        'navMenuContainer',
        'navMenuBtn',
        'navMenuList',
        constants.OPEN_MENU_ON_HOVER
    );
}

export {initNavMenu};