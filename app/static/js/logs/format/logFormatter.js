import {getElements} from '../ui/ui.js'
import {filterAndHighlightLog} from '../ui/filterUi.js'
import {log} from '../../share/logger.js';
import {constants} from '../../share/constants.js';

/**
 * Экранирует специальные символы для безопасного вывода в HTML
 *
 * :param text: Входной текст
 * :return: Экранированная строка
 */
function escapeHtml(text) {
    if (typeof text !== 'string') return text
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
}

/**
 * Форматирование сообщения лога согласно шаблону
 *
 * :param log: объект лога
 * :param logFormat: строковый шаблон
 * :return: строка форматированного лога
 */
function formatLogMessage(log, logFormat) {
    let formattedMessage = logFormat
    Object.keys(log).forEach(key => {
        const value = log[key] !== undefined ? String(log[key]) : ''
        formattedMessage = formattedMessage.replace(new RegExp(`%\\(${key}\\)s`, 'g'), value)
        const widthRegex = new RegExp(`%\\(${key}\\)-(\\d+)s`, 'g')
        formattedMessage = formattedMessage.replace(widthRegex, (match, width) => {
            return value.padEnd(parseInt(width));
        });
        const rightWidthRegex = new RegExp(`%\\(${key}\\)(\\d+)s`, 'g')
        formattedMessage = formattedMessage.replace(rightWidthRegex, (match, width) => {
            return value.padStart(parseInt(width));
        });
    })
    return formattedMessage
}

/**
 * Оформляет класс CSS уровня лога
 *
 * :param logLevel: строка уровня
 * :return: имя класса
 */
function getLogLevelClass(logLevel) {
    switch (logLevel) {
        case 'INFO':
        case 'INF':
            return 'info'
        case 'WARNING':
        case 'WRN':
            return 'warning'
        case 'ERROR':
        case 'ERR':
            return 'error'
        case 'DEBUG':
        case 'DBG':
        default:
            return 'debug'
    }
}

/**
 * Преобразует сокращённые уровни логирования к полным
 */
function normalizeLogLevel(logLevel) {
    switch (logLevel) {
        case 'DBG':
            return 'DEBUG'
        case 'INF':
            return 'INFO'
        case 'WRN':
            return 'WARNING'
        case 'ERR':
            return 'ERROR'
        case 'FTL':
            return 'ERROR'
        default:
            return logLevel
    }
}

/**
 * Добавление лог-сообщения в DOM со всеми параметрами.
 * Все логи всегда добавляются, их видимость регулируется filterAndHighlightLog.
 *
 * :param log: объект лога
 * :param logFormat: шаблон
 * :param maxEntries: int ограничение количества
 * :return: созданный DOM-элемент записи лога или null
 */
function addLogEntry(log, logFormat, maxEntries = constants.LOG_ENTRY_MAX + 2) {
    const elements = getElements()
    const entry = document.createElement('div')
    entry.className = 'log-entry'
    entry.dataset.logData = JSON.stringify(log)
    entry.dataset.logLevel = log.levelname

    const levelClass = getLogLevelClass(log.levelname)
    const formattedMessage = formatLogMessage(log, logFormat)
    const escapedMessage = escapeHtml(formattedMessage)

    entry.innerHTML = `<span class="${levelClass}">${escapedMessage}</span>`
    elements.logDisplay.appendChild(entry)

    const entries = document.querySelectorAll('.log-entry')
    if (entries.length > maxEntries) {
        for (let i = 0; i < entries.length - maxEntries; i++) {
            elements.logDisplay.removeChild(entries[i])
        }
    }

    // После добавления — сразу применяем фильтрацию по уровню + текстовому фильтру
    filterAndHighlightLog(entry)

    return entry
}

/**
 * Применяет фильтр уровня ко всем логам
 *
 * :param minLogLevel: выбранный уровень
 */
function applyLogLevelFilter(minLogLevel) {
    log('LOGS', 'Применяем фильтр уровня:', minLogLevel)
    const logEntries = document.querySelectorAll('.log-entry')
    logEntries.forEach(entry => {
        filterAndHighlightLog(entry)
    })
}

/**
 * Применяет новый формат ко всем логам
 *
 * :param newFormat: строка-формат
 */
function updateAllLogFormats(newFormat) {
    log('LOGS', 'Меняем формат для всех сообщений')
    const logEntries = document.querySelectorAll('.log-entry')
    logEntries.forEach(entry => {
        const logData = entry.dataset.logData
        if (logData) {
            try {
                const log = JSON.parse(logData)
                const formattedMessage = formatLogMessage(log, newFormat)
                entry.dataset.originalContent = escapeHtml(formattedMessage)
                import('../ui/filterUi.js').then(({filterAndHighlightLog}) => {
                    entry.querySelector('span').innerHTML = formattedMessage
                    filterAndHighlightLog(entry)
                })
            } catch (e) {
                log('LOGS', 'Error parsing log data:', e, 'error')
            }
        }
    })
}

export {
    formatLogMessage,
    addLogEntry,
    updateAllLogFormats,
    applyLogLevelFilter,
    getLogLevelClass,
    normalizeLogLevel
}