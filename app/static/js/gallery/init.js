import {checkToken, logout} from "../auth/api.js";
import {fetchPassphrase, fetchGalleryData} from "./api.js";
import {initNavMenu} from "../share/navMenu.js";
import {startTokenRefresh, stopTokenRefresh} from "../auth/tokenRefresh.js";
import {initGalleryControls} from "./ui/galleryUi.js";
import {initSyncModal} from "./ui/syncModalUi.js";
import {log} from '../share/logger.js';
import {constants} from '../share/constants.js';
import {initializeMenu} from "../share/menuHandler.js";
import {showAccessMessage} from "../share/accessUi.js";
import {showPromptModal} from "../conf/ui/promptModal.js";

/**
 * Инициализирует страницу галереи.
 * @returns {Promise<void>}
 */
async function initGallery() {
    log('GALLERY', 'DOM loaded, старт инициализации');
    document.getElementById("logoBtn").onclick = () => {
        window.location.href = constants.URL_PAGE_HOME;
    };
    document.getElementById("logoutBtn").addEventListener('click', async () => {
        log('GALLERY', 'Нажата кнопка "Выход" — переход на /auth/logout');
        stopTokenRefresh();
        window.location.href = '/auth/logout';
    });

    const valid = await checkToken();
    if (!valid) {
        await logout();
        window.location.replace('/auth?next=/gallery');
        return;
    }

    try {
        // Пробный запрос для проверки прав доступа
        await fetchGalleryData({page: 1, pageSize: 1, filters: {}});

        // Если доступ есть, показываем основной контент
        const contentWrapper = document.querySelector('.gallery-content-wrapper');
        if (contentWrapper) {
            contentWrapper.classList.remove('hidden');
        }

        const passphrase = await fetchPassphrase();
        if (!passphrase) {
            log('GALLERY', 'Не удалось получить passphrase, функционал синхронизации будет недоступен', 'warn');
        }

        initNavMenu();
        initGalleryControls(); // Инициализация всего UI галереи
        initSyncModal(passphrase);

        // Инициализация меню действий
        const menuList = document.getElementById('galleryMenuList');
        if (menuList) {
            const syncItem = document.createElement('li');
            syncItem.innerHTML = `<span class="nav-menu-icon">🔄</span> Синхронизация`;

            if (passphrase) {
                syncItem.onclick = () => {
                    document.getElementById('startSyncBtn-trigger')?.click();
                    menuList.classList.remove('show');
                };
            } else {
                syncItem.style.opacity = '0.5';
                syncItem.title = "Синхронизация недоступна: требуются права на доступ к настройкам.";
                syncItem.onclick = async (e) => {
                    e.stopPropagation(); // Предотвращаем закрытие меню
                    await showPromptModal('Доступ запрещен', {
                        mode: constants.PROMPT_MODE_ALERT,
                        error: "Для выполнения синхронизации требуются права на доступ к странице настроек.",
                        okLabel: 'Понятно',
                        backdropClose: true,
                    });
                };
            }

            menuList.appendChild(syncItem);
            initializeMenu('galleryMenuContainer', 'galleryMenuBtn', 'galleryMenuList', true);
        }

    } catch (e) {
        const message = e.message.includes('permission')
            ? constants.MSG_GALLERY_ACCESS_DENIED
            : `Произошла ошибка: ${e.message}`;

        showAccessMessage(message, '.gallery-content-wrapper');

        initNavMenu(); // Навигация и выход должны работать даже при ошибке
        // Скрываем меню действий галереи, если доступа нет
        const galleryMenu = document.getElementById('galleryMenuContainer');
        if (galleryMenu) {
            galleryMenu.style.display = 'none';
        }
    }

    startTokenRefresh('/auth?next=/gallery');
    log('GALLERY', 'Инициализация завершена');
}

export {initGallery};