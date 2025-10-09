import {addLogEntry} from '../format/logFormatter.js'
import {getElements, scrollToBottom} from '../ui/ui.js'
import {filterAndHighlightLog} from '../ui/filterUi.js'
import {logout} from '../../auth/api.js'
import {showAccessMessage} from '../../share/accessUi.js'
import {hideLogsAccessControls} from '../ui/accessUi.js'
import {hideScrollBtn} from "../ui/scrollToBottomBtn.js";
import {log} from '../../share/logger.js';
import {constants} from '../../share/constants.js';
import {showConnecting, showConnected, showDisconnected, hideStatus} from '../ui/connectionStatusUi.js';

let eventSource = null
let fetchController = null
let reconnectTimeout = null
let showConnectingTimeout = null;
let lastActivityTime = Date.now()
let connectionMonitor = null
let flushTimeout = null

const elements = getElements()
let accessDenied = false
let logBuffer = []

/**
 * Закрытие всех потоков, fetch-запросов, мониторинга и таймеров reconnect'а
 */
function closeAllConnections() {
    hideStatus()
    if (connectionMonitor) {
        log('LOGS', 'Остановка мониторинга соединений')
        clearInterval(connectionMonitor)
        connectionMonitor = null
    }
    if (fetchController) {
        log('LOGS', 'Отмена fetch-запроса')
        fetchController.abort()
        fetchController = null
    }
    if (eventSource) {
        log('LOGS', 'Закрытие SSE соединения')
        eventSource.close()
        eventSource = null
    }
    if (reconnectTimeout) {
        log('LOGS', 'Остановка таймера reconnect')
        clearTimeout(reconnectTimeout)
        reconnectTimeout = null
    }
    if (flushTimeout) {
        clearTimeout(flushTimeout)
        flushTimeout = null
    }
    if (showConnectingTimeout) {
        clearTimeout(showConnectingTimeout);
        showConnectingTimeout = null;
    }
    logBuffer = []
}

/**
 * Добавляет логи из буфера порциями в DOM (batchSize штук за раз), фиксируя скролл сразу в конец
 *
 * :param batchSize: количество логов в одной порции
 */
function flushLogBuffer(batchSize = constants.LOG_FLUSH_BATCH_SIZE + 2) {
    if (logBuffer.length === 0) {
        flushTimeout = null
        return
    }
    const fragment = document.createDocumentFragment()
    let count = Math.min(batchSize, logBuffer.length)
    for (let i = 0; i < count; i++) {
        const {log, settings} = logBuffer.shift()
        const logEntry = addLogEntry(log, settings.logFormat)
        if (logEntry) {
            filterAndHighlightLog(logEntry)
            fragment.appendChild(logEntry)
        }
    }
    elements.logDisplay.appendChild(fragment)
    scrollToBottom(constants.SCROLL_ADD_LOG_DURATION_MS)
    hideScrollBtn()
    flushTimeout = setTimeout(() => flushLogBuffer(batchSize), constants.TIME_LOGS_FLUSH_BATCH)
}

/**
 * Обрабатывает новый лог: добавляет в буфер для последующего пакетного вывода
 *
 * :param log: объект лога
 * :param settings: глобальные настройки интерфейса
 */
function processLogData(log, settings) {
    logBuffer.push({log, settings})
    if (!flushTimeout) {
        flushTimeout = setTimeout(() => flushLogBuffer(), 0)
    }
}

/**
 * Обработка chunk-а из SSE (stream)
 *
 * :param data: строка всех новых данных
 * :param settings: настройки
 */
function processStreamData(data, settings) {
    if (!data.trim() || data.startsWith(':')) return

    const lines = data.split('\n')
    const dataLine = lines.find(line => line.startsWith('data:'))
    if (dataLine) {
        const jsonData = dataLine.slice(5).trim()
        try {
            const log = JSON.parse(jsonData)
            // Если это ошибка доступа из backend — специальная обработка:
            if (log && log.error && log.error.message && log.error.message.includes('permission')) {
                handleAccessDenied(log.error.message)
                return
            }
            processLogData(log, settings)
        } catch (error) {
            log('LOGS', 'Error parsing log data:', error, 'error')
        }
    }
}

function handleAccessDenied(message) {
    accessDenied = true
    closeAllConnections()
    hideStatus()
    showAccessMessage(message || constants.MSG_LOGS_ACCESS_DENIED, '.logs-container')
    hideLogsAccessControls()
}

/**
 * Ошибки потока: возвращение к login, попытки переподключения
 */
function handleStreamError(error, settings) {
    if (accessDenied) return;
    if (error.name === 'AbortError' || (error.message && error.message.includes('connection closed'))) {
        log('LOGS', 'Поток закрыт или прерван намеренно')
        return
    }
    if (error.message.includes('Token invalid') || error.status === 401) {
        log('LOGS', 'Токен недействителен, отправляем logout', 'warn')
        hideStatus()
        logout().then(() => {
            window.location.replace(constants.URL_LOGOUT_LOGS)
        })
        return
    }
    if (error.status === 403 || (error.message && error.message.includes('403'))) {
        handleAccessDenied(constants.MSG_LOGS_ACCESS_DENIED)
        return
    }
    log('LOGS', 'Ошибка потока логов:', error, 'error')
    if (!accessDenied) {
        log('LOGS', `Перезапуск соединения через ${constants.TIME_LOGS_RECONNECT_ERROR / 1000} сек.`)
        showDisconnected(constants.TIME_LOGS_RECONNECT_ERROR)
        reconnectTimeout = setTimeout(() => {
            log('LOGS', 'Попытка переподключения к потоку логов')
            setupEventSource(settings)
        }, constants.TIME_LOGS_RECONNECT_ERROR)
    }
}

/**
 * Основная функция подключения к потоку логов (fetch + SSE)
 */
function setupEventSource(settings) {
    if (accessDenied) return
    log('LOGS', 'Попытка установить соединение с потоком логов')
    closeAllConnections()

    showConnectingTimeout = setTimeout(() => {
        showConnecting();
    }, constants.TIME_SHOW_CONNECTING_DELAY);

    lastActivityTime = Date.now()
    connectionMonitor = setInterval(() => {
        const inactiveTime = Date.now() - lastActivityTime
        if (inactiveTime > constants.TIME_LOGS_INACTIVE) {
            log('LOGS', `Поток неактивен более ${inactiveTime / 1000} сек, переподключаемся...`, 'warn')
            clearInterval(connectionMonitor)
            setupEventSource(settings)
        }
    }, constants.TIME_LOGS_CHECK_INACTIVE)
    log('LOGS', 'Создан новый connectionMonitor')

    fetchController = new AbortController()
    log('LOGS', 'Новый fetchController инициирован')
    const fetchSignal = fetchController.signal

    fetch(constants.ENDPOINT_LOGS_STREAM + `?limit=${settings.logLimit}`, {
        method: 'GET',
        credentials: 'include',
        signal: fetchSignal
    }).then(response => {
        if (!response.ok) {
            clearTimeout(showConnectingTimeout);
            showConnectingTimeout = null;
            if (response.status === 401) {
                log('LOGS', 'Сервер вернул 401: Token invalid', 'error')
                hideStatus()
                throw new Error('Token invalid')
            }
            if (response.status === 403) {
                handleAccessDenied(constants.MSG_LOGS_ACCESS_DENIED)
                throw new Error('403')
            }
            log('LOGS', `Сервер вернул ошибку: ${response.status}`, 'error')
            throw new Error(`HTTP error: ${response.status}`)
        }

        clearTimeout(showConnectingTimeout);
        showConnectingTimeout = null;

        elements.logDisplay.innerHTML = ''
        showConnected()

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        log('LOGS', 'Соединение с потоком логов установлено')

        function processStream() {
            reader.read().then(({done, value}) => {
                if (done) {
                    log('LOGS', 'Поток log закрыт сервером')
                    if (!accessDenied) {
                        showDisconnected(constants.TIME_LOGS_RECONNECT_CLOSE)
                        reconnectTimeout = setTimeout(() => {
                            log('LOGS', 'Переподключение после закрытия потока')
                            setupEventSource(settings)
                        }, constants.TIME_LOGS_RECONNECT_CLOSE)
                    }
                    return
                }
                try {
                    buffer += decoder.decode(value, {stream: true})
                    const events = buffer.split('\n\n')
                    buffer = events.pop() || ''
                    events.forEach(event => {
                        processStreamData(event, settings)
                    })
                    lastActivityTime = Date.now()
                } catch (error) {
                    log('LOGS', 'Ошибка processStreamData:', error, 'error')
                }
                processStream()
            }).catch(error => handleStreamError(error, settings))
        }

        processStream()
    }).catch(error => {
        clearTimeout(showConnectingTimeout);
        showConnectingTimeout = null;
        if (accessDenied) return
        if (error.name === 'AbortError') {
            log('LOGS', 'Поток log закрыт клиентом', 'warn')
            return
        }
        log('LOGS', 'Fetch error:', error, 'error')
        if (error.message === 'Token invalid') {
            hideStatus()
            logout().then(() => {
                window.location.replace(constants.URL_LOGOUT_LOGS)
            })
            return
        }
        if (error.message === '403') {
            // уже обработано выше
            return
        }
        log('LOGS', 'Попытка reconnect после fetch error', 'warn')
        showDisconnected(constants.TIME_LOGS_RECONNECT_FETCH)
        reconnectTimeout = setTimeout(() => {
            log('LOGS', 'Переподключение после fetch error')
            setupEventSource(settings)
        }, constants.TIME_LOGS_RECONNECT_FETCH)
        log('LOGS', `Соединение НЕ установлено, попытка переподключения через ${constants.TIME_LOGS_RECONNECT_FETCH / 1000} сек...`, 'warn')
    })
}

export {
    setupEventSource,
    closeAllConnections
}