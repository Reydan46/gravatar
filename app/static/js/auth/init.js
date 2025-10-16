import {encryptString, testCryptoSupport} from './crypto.js'
import {authByEncrypted, checkToken, logout} from './api.js'
import {showAuthError} from './ui/errorUi.js'
import {log} from '../share/logger.js'
import {constants} from '../share/constants.js'

/**
 * Проверяет, включен ли SAML и отображает кнопку.
 */
async function checkAndEnableSamlButton() {
    try {
        const response = await fetch('/saml/status')
        if (response.ok) {
            const data = await response.json()
            if (data.enabled) {
                const samlContainer = document.getElementById('samlContainer')
                const samlLoginBtn = document.getElementById('samlLoginBtn')
                samlContainer.classList.remove('hidden')
                samlLoginBtn.addEventListener('click', () => {
                    window.location.href = '/saml/sso'
                })
                log('AUTH', 'SAML is enabled, button is visible.')
            }
        }
    } catch (error) {
        log('AUTH', 'Failed to check SAML status:', error, 'error')
    }
}


/**
 * Назначает обработчики для формы входа с принудительной загрузкой публичного ключа при авторизации
 *
 * @param {object} params - Объект с параметрами (например, {next})
 */
function attachAuthButtonHandlers({next}) {
    const loginForm = document.getElementById('loginForm')
    const loginBtn = document.getElementById('loginBtn')
    const usernameInput = document.getElementById('username')
    const passwordInput = document.getElementById('password')
    const errorMessage = document.getElementById('errorMessage')

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault()
        log('AUTH', 'Отправка формы авторизации')
        loginBtn.disabled = true
        errorMessage.textContent = ''
        const username = usernameInput.value.trim()
        const password = passwordInput.value
        if (!username || !password) {
            showAuthError(constants.MSG_ENTER_USER_PASS)
            loginBtn.disabled = false
            return
        }
        try {
            // Принудительно загружаем публичный ключ с сервера
            const encrypted = await encryptString(`${username}:${password}`, true)
            await authByEncrypted(encrypted)
            log('AUTH', 'Авторизация прошла успешно, переход...')
            window.location.replace(next)
        } catch (error) {
            let msg = constants.MSG_AUTH_ERROR
            if (error instanceof Error) {
                msg = error.message
            } else if (typeof error === 'object' && error) {
                msg = JSON.stringify(error)
            }
            showAuthError(msg)
            passwordInput.value = ''
            setTimeout(() => passwordInput.focus(), constants.FOCUS_TIMEOUT_MS)
        } finally {
            loginBtn.disabled = false
        }
    })
}

async function initAuth() {
    log('AUTH', 'DOM loaded, старт инициализации')
    const params = new URLSearchParams(window.location.search)
    const next = params.get('next') || constants.URL_PAGE_HOME
    const valid = await checkToken()
    if (valid) {
        log('AUTH', 'Уже авторизованы, перенаправление на', next)
        window.location.replace(next)
        return
    } else {
        await logout()
    }
    const cryptoSupported = await testCryptoSupport()
    if (!cryptoSupported) {
        showAuthError(constants.MSG_CRYPTO_ERROR)
        document.getElementById('loginBtn').disabled = true
        return
    }

    attachAuthButtonHandlers({next})
    await checkAndEnableSamlButton()
    log('AUTH', 'Инициализация завершена')
}

export {initAuth}