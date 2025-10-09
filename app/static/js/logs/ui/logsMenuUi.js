import {log} from '../../share/logger.js';
import {constants} from '../../share/constants.js';
import {initializeMenu} from '../../share/menuHandler.js';
import {showSettingsModal} from '../settings/ui.js';
import {showFilterHelpModal} from './filterHelpUi.js';


/**
 * Инициализирует меню действий на странице логов.
 *
 * @param {object} settings - Текущие настройки для передачи в модальное окно.
 * @returns {void}
 */
function initLogsMenu(settings) {
    log('LOGS', 'Инициализация меню действий на странице логов');
    const menuList = document.getElementById('logsMenuList');

    if (!menuList) {
        log('LOGS', 'Элемент logsMenuList не найден', 'warn');
        return;
    }

    const menuItems = [
        {
            label: 'Настройки просмотра',
            icon: '🎨',
            onClick: () => showSettingsModal(settings),
        },
        {
            label: 'Справка по фильтрации',
            icon: '❓',
            onClick: showFilterHelpModal,
        }
    ];

    menuList.innerHTML = '';
    menuItems.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `<span class="nav-menu-icon">${item.icon}</span> ${item.label}`;
        li.onclick = () => {
            item.onClick();
            menuList.classList.remove('show'); // Закрываем меню после клика
        };
        menuList.appendChild(li);
    });

    initializeMenu(
        'logsMenuContainer',
        'logsMenuBtn',
        'logsMenuList',
        constants.OPEN_MENU_ON_HOVER
    );
}

export {initLogsMenu};