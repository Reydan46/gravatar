import {loadSettings} from '../share/settings.js';
import {constants} from '../share/constants.js';
import {checkToken, logout} from '../auth/api.js';
import {getElements} from './ui/ui.js';
import {setupEventSource, closeAllConnections} from './stream/logStream.js';
import {initSettingsHandlers} from './settings/handlers.js';
import {applyLogLevelFilter} from './format/logFormatter.js';
import {initFilterUi, setFilterValue} from './ui/filterUi.js';
import {initScrollToBottomButton} from "./ui/scrollToBottomBtn.js";
import {startTokenRefresh, stopTokenRefresh} from "../auth/tokenRefresh.js";
import {initNavMenu} from "../share/navMenu.js";
import {log} from "../share/logger.js";
import {showLogsAccessControls} from './ui/accessUi.js';
import {initLogsMenu} from "./ui/logsMenuUi.js";
import {initFilterHelpModal} from "./ui/filterHelpUi.js";
import {initConnectionStatus} from './ui/connectionStatusUi.js';

let settings = loadSettings();
const elements = getElements();

function applyInitialSettings() {
    log('LOGS', 'Применение начальных настроек интерфейса логов');
    document.documentElement.style.setProperty('--log-font-size', `${settings.fontSize}px`);
    document.documentElement.style.setProperty('--debug-color', settings.colors.debug);
    document.documentElement.style.setProperty('--info-color', settings.colors.info);
    document.documentElement.style.setProperty('--warning-color', settings.colors.warning);
    document.documentElement.style.setProperty('--error-color', settings.colors.error);
    if (elements.logLevelSelect) {
        elements.logLevelSelect.value = settings.logLevel;
        applyLogLevelFilter(settings.logLevel);
    }
    if (elements.filterInput && settings.filter) {
        setFilterValue(settings.filter);
    }
    // Установить лимиты и диапазоны для input'ов из variables
    const logLimitInput = document.getElementById('logLimit');
    if (logLimitInput) {
        logLimitInput.min = constants.LOG_ENTRY_MIN;
        logLimitInput.max = constants.LOG_ENTRY_MAX;
        const logLimitRange = document.getElementById('logLimitRange');
        if (logLimitRange) {
            logLimitRange.textContent = `(${constants.LOG_ENTRY_MIN} - ${constants.LOG_ENTRY_MAX})`;
        }
    }
    const fontSizeInput = document.getElementById('fontSize');
    if (fontSizeInput) {
        fontSizeInput.min = constants.FONT_SIZE_MIN;
        fontSizeInput.max = constants.FONT_SIZE_MAX;
        const fontSizeRange = document.getElementById('fontSizeRange');
        if (fontSizeRange) {
            fontSizeRange.textContent = `(${constants.FONT_SIZE_MIN} - ${constants.FONT_SIZE_MAX})`;
        }
    }
    // Установить placeholder и стандартный формат из variables
    const logFormatTextarea = document.getElementById('logFormat');
    if (logFormatTextarea) {
        logFormatTextarea.placeholder = constants.DEFAULT_LOG_FORMAT;
    }
    const defaultFormatPre = document.getElementById('defaultFormat');
    if (defaultFormatPre) {
        defaultFormatPre.textContent = constants.DEFAULT_LOG_FORMAT;
    }
}

function initEventHandlers() {
    document.getElementById("logoBtn").onclick = () => {
        window.location.href = constants.URL_PAGE_HOME;
    }
    elements.logoutBtn.addEventListener('click', async () => {
        log('LOGS', 'Нажата кнопка "Выход" — переход на /auth/logout');
        closeAllConnections();
        stopTokenRefresh();
        window.location.href = '/auth/logout';
    });
    window.addEventListener('beforeunload', () => {
        closeAllConnections();
        stopTokenRefresh();
    });
}

/**
 * Инициализирует страницу просмотра логов: проверяет авторизацию,
 * применяет настройки, настраивает обработчики и запускает получение логов.
 * Кнопка настроек отображается только после успешной проверки.
 *
 * @return {Promise<void>}
 */
async function initLogs() {
    log('LOGS', 'DOM loaded, старт инициализации LOGS');

    const valid = await checkToken();
    if (!valid) {
        await logout();
        window.location.replace(constants.URL_LOGOUT_LOGS);
        return;
    }

    showLogsAccessControls();

    applyInitialSettings();
    initNavMenu();
    initLogsMenu(settings);
    initFilterHelpModal();
    initConnectionStatus();
    initSettingsHandlers(settings);
    initFilterUi(settings.filter);
    initEventHandlers();
    initScrollToBottomButton();
    setupEventSource(settings);
    startTokenRefresh(constants.URL_LOGOUT_LOGS);
    log('LOGS', 'Инициализация завершена');
}

export {initLogs};