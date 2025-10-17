import {getCookie} from './cookie.js'
import {log} from '../share/logger.js'
import {constants} from '../share/constants.js'

/**
 * Проверка авторизации по зашифрованным данным
 *
 * @param {string} encryptedData - строка base64
 * @return {Promise<any>}
 */
async function authByEncrypted(encryptedData) {
    log('AUTH', 'Проверка авторизации по зашифрованным данным')
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), constants.API_TIMEOUT_AUTH)
    try {
        const response = await fetch(constants.ENDPOINT_LOGIN, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({enc_data: encryptedData}),
            credentials: 'include',
            signal: controller.signal
        })
        clearTimeout(timeoutId)
        log('AUTH', `Ответ сервера: ${response.status}`)
        if (!response.ok) {
            let errorData
            try {
                errorData = await response.json()
            } catch {
                errorData = null
            }
            log('AUTH', 'Ошибка авторизации:', errorData, 'error')
            throw new Error(errorData?.detail || `Ошибка авторизации (${response.status})`)
        }
        const data = await response.json()
        log('AUTH', 'Авторизация успешна:', data)
        return data
    } catch (error) {
        if (error.name === 'AbortError') {
            log('AUTH', 'Запрос отменён по таймауту', 'error')
            throw new Error('Запрос был отменен из-за таймаута.')
        }
        log('AUTH', 'Ошибка:', error, 'error')
        throw error
    }
}

/**
 * Проверить валидность токена (Cookie + fetch)
 *
 * @return {Promise<boolean>}
 */
async function checkToken() {
    const authStatus = getCookie(constants.COOKIE_AUTH_STATUS)
    if (!authStatus) {
        return false
    }
    try {
        const response = await fetch(constants.ENDPOINT_TOKEN_CHECK, {
            method: 'POST',
            credentials: 'include'
        })
        log('AUTH', `Ответ сервера: ${response.status}`)
        return response.ok
    } catch (error) {
        log('AUTH', 'Ошибка:', error, 'error')
        return false
    }
}

/**
 * Обновить токен (refresh)
 *
 * @return {Promise<{ result: 'updated' | 'not_updated' | 'error', response?: Response }>}
 */
async function refreshToken() {
    const authStatus = getCookie(constants.COOKIE_AUTH_STATUS)
    if (!authStatus) {
        log('AUTH', 'Cookie auth_status отсутствует', 'warn')
        return {result: 'error'}
    }
    try {
        const response = await fetch(constants.ENDPOINT_TOKEN_REFRESH, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
        })
        if (!response.ok) {
            return {result: 'error', response}
        }
        const data = await response.json()
        if (data.message === constants.MSG_TOKEN_UPDATED) {
            return {result: 'updated'}
        } else if (data.message === constants.MSG_TOKEN_NOT_UPDATED) {
            return {result: 'not_updated'}
        } else {
            return {result: 'error', response}
        }
    } catch (error) {
        log('AUTH', 'Ошибка:', error, 'error')
        return {result: 'error'} // Сетевая ошибка, response будет undefined
    }
}

/**
 * Выход (logout)
 *
 * @return {Promise<boolean>}
 */
async function logout() {
    const authStatus = getCookie(constants.COOKIE_AUTH_STATUS)
    if (!authStatus) {
        return false
    }
    log('AUTH', 'Запрос выхода из системы')
    try {
        await fetch(constants.ENDPOINT_LOGOUT, {
            method: 'GET',
            credentials: 'include'
        })
        log('AUTH', 'Успешный выход, cookie очищена')
        return true
    } catch (error) {
        log('AUTH', 'Ошибка выхода:', error, 'error')
        return false
    }
}

export {authByEncrypted, checkToken, refreshToken, logout}