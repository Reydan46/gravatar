import {closeAllConnections} from "../logs/stream/logStream.js";
import {logout, refreshToken} from "./api.js";
import {log} from '../share/logger.js';
import {constants} from '../share/constants.js';
import {getCookie} from "./cookie.js";

// === Переменные состояния для логики обновления токена ===
let refreshTimer = null // Может быть как интервалом, так и таймаутом
let isIntervalMode = true // true для штатного 10-минутного интервала, false для повторных попыток
let retryCount = 0 // Счетчик попыток

/**
 * Проверяет, истек ли токен, на основе cookie 'auth_status'.
 * @returns {boolean} - true, если токен предположительно истек.
 */
function isTokenExpiredClientSide() {
    const authStatusCookie = getCookie(constants.COOKIE_AUTH_STATUS)
    if (!authStatusCookie) {
        return true // Нет cookie - считаем, что токен истек
    }

    // Парсим дату из формата "ДД.ММ.ГГГГ ЧЧ:ММ:СС.мс"
    const parts = authStatusCookie.match(/(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}):(\d{2})\.(\d{3})/)
    if (!parts) {
        log('AUTH', 'Не удалось распарсить дату из auth_status cookie', 'warn')
        return true
    }

    // parts[0] - вся строка, parts[1] - день, ..., parts[7] - мс
    const issueDate = new Date(parts[3], parts[2] - 1, parts[1], parts[4], parts[5], parts[6], parts[7]);
    if (isNaN(issueDate.getTime())) {
        log('AUTH', 'Невалидная дата в auth_status cookie', 'warn')
        return true
    }

    const expirationTime = issueDate.getTime() + constants.TOKEN_MAX_AGE_S * 1000
    const isExpired = Date.now() > expirationTime

    if (isExpired) {
        log('AUTH', 'Клиентская проверка: токен истек', 'warn')
    }

    return isExpired
}

/**
 * Выполняет выход из системы и перезагрузку страницы.
 * @param {string} logoutUrl - URL для перенаправления после выхода.
 * @param {string} reason - Причина выхода для логирования.
 */
async function forceLogout(logoutUrl, reason) {
    log('AUTH', reason)
    stopTokenRefresh()
    closeAllConnections()
    await logout()
    window.location.replace(logoutUrl)
}

/**
 * Основная функция, которая выполняет проверку и обновление токена.
 * @param {string} logoutUrl - URL для перенаправления при выходе.
 */
async function performTokenRefresh(logoutUrl) {
    // Проверка на стороне клиента, чтобы не делать лишних запросов
    if (isTokenExpiredClientSide()) {
        await forceLogout(logoutUrl, 'Токен истек (клиентская проверка), выход из системы')
        return
    }

    try {
        log('AUTH', 'Запрос на обновление токена...')
        const {result, response} = await refreshToken()

        if (result === 'updated' || result === 'not_updated') {
            log('AUTH', `Токен ${result === 'updated' ? 'успешно обновлён' : 'не требует обновления'}`)
            // Если мы были в режиме повторных попыток, возвращаемся к штатному интервалу
            if (!isIntervalMode) {
                log('AUTH', 'Соединение восстановлено, возврат к штатному режиму обновления')
                startTokenRefresh(logoutUrl)
            }
            return
        }

        // Обработка ошибок
        // Любая ошибка 4xx считается фатальной для сессии
        if (response && response.status >= 400 && response.status < 500) {
            await forceLogout(logoutUrl, `Фатальная ошибка при обновлении токена (статус ${response.status}), выход`)
        } else {
            // Перед переходом в режим повторов, останавливаем текущий таймер (интервал)
            if (isIntervalMode) {
                stopTokenRefresh()
                isIntervalMode = false
            }

            if (retryCount < constants.RETRY_DELAYS.length) {
                const delay = constants.RETRY_DELAYS[retryCount]
                log('AUTH', `Сетевая ошибка или ошибка сервера при обновлении. Попытка #${retryCount + 1} через ${delay / 1000} сек.`, 'warn')
                retryCount++
                refreshTimer = setTimeout(() => performTokenRefresh(logoutUrl), delay)
            } else {
                await forceLogout(logoutUrl, 'Все попытки восстановления соединения исчерпаны, выход из системы')
            }
        }
    } catch (error) {
        await forceLogout(logoutUrl, `Критическая ошибка в цикле обновления токена: ${error.message}`)
    }
}

/**
 * Запускает основной цикл обновления токена.
 * @param {string} logoutUrl - URL для перенаправления при выходе.
 */
function startTokenRefresh(logoutUrl) {
    stopTokenRefresh()
    log('AUTH', 'Запуск штатного интервала обновления токена')
    isIntervalMode = true
    retryCount = 0
    refreshTimer = setInterval(() => performTokenRefresh(logoutUrl), constants.TIME_TOKEN_REFRESH)
}

/**
 * Полностью останавливает все таймеры обновления.
 */
function stopTokenRefresh() {
    if (refreshTimer) {
        if (isIntervalMode) {
            clearInterval(refreshTimer)
        } else {
            clearTimeout(refreshTimer)
        }
        refreshTimer = null
        log('AUTH', 'Таймер обновления токена остановлен')
    }
    retryCount = 0
}

export {startTokenRefresh, stopTokenRefresh}