import { log } from '../../share/logger.js';
import {constants} from '../../share/constants.js';

/**
 * UI-утилита показа ошибок авторизации

 * :param message: string | Object
 */
function showAuthError(message) {
    log('AUTH', 'Отображение ошибки авторизации:', message)
    const errorElement = document.getElementById('errorMessage')
    if (!errorElement) return
    errorElement.textContent = typeof message === 'object'
        ? (JSON.stringify(message) || constants.MSG_AUTH_ERROR)
        : message
}

export {showAuthError}