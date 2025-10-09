import {log} from './logger.js';
import {constants} from './constants.js';

/**
 * Загрузить текущие настройки из localStorage
 *
 * :return: объект
 */
function loadSettings() {
    log('SHARE', 'Загрузка настроек из localStorage')
    return {
        logFormat: localStorage.getItem('logFormat') || constants.DEFAULT_LOG_FORMAT,
        fontSize: localStorage.getItem('fontSize') || constants.DEFAULT_FONT_SIZE,
        logLimit: localStorage.getItem('logLimit') || constants.DEFAULT_LOG_LIMIT,
        logLevel: localStorage.getItem('logLevel') || constants.DEFAULT_LOG_LEVEL,
        filter: localStorage.getItem('filter') || constants.DEFAULT_FILTER,
        colors: {
            debug: localStorage.getItem('debugColor') || constants.DEFAULT_LOG_COLORS.debug,
            info: localStorage.getItem('infoColor') || constants.DEFAULT_LOG_COLORS.info,
            warning: localStorage.getItem('warningColor') || constants.DEFAULT_LOG_COLORS.warning,
            error: localStorage.getItem('errorColor') || constants.DEFAULT_LOG_COLORS.error
        }
    }
}

/**
 * Сохранить одну настройку логов
 *
 * :param key: ключ
 * :param value: значение
 */
function saveSettings(key, value) {
    localStorage.setItem(key, value)
}

export {
    loadSettings,
    saveSettings
}