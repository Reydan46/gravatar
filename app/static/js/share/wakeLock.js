/**
 * Управляет Wake Lock API для предотвращения "засыпания" экрана/вкладки.
 */

import { log } from './logger.js';

let wakeLock = null;
let isWakeLockRequested = false; // Флаг, указывающий на намерение удерживать блокировку

/**
 * Запрашивает блокировку экрана от "засыпания".
 * @returns {Promise<void>}
 */
const requestWakeLock = async () => {
    if (!('wakeLock' in navigator)) {
        log('WAKELOCK', 'Wake Lock API не поддерживается этим браузером', 'warn');
        return;
    }

    try {
        wakeLock = await navigator.wakeLock.request('screen');
        wakeLock.addEventListener('release', handleWakeLockRelease);
        log('WAKELOCK', 'Блокировка экрана успешно активирована');
    } catch (err) {
        // Ошибка может возникнуть, если документ не видим, поэтому сбрасываем флаг
        isWakeLockRequested = false;
        log('WAKELOCK', `Не удалось активировать блокировку экрана: ${err.name}, ${err.message}`, 'error');
    }
};

/**
 * Освобождает ранее установленную блокировку.
 * @returns {Promise<void>}
 */
const releaseWakeLock = async () => {
    if (!wakeLock) {
        return;
    }
    try {
        await wakeLock.release();
    } catch (err) {
        log('WAKELOCK', `Ошибка при освобождении блокировки экрана: ${err.name}, ${err.message}`, 'error');
    }
};

/**
 * Обрабатывает системное или ручное освобождение блокировки.
 */
const handleWakeLockRelease = () => {
    log('WAKELOCK', 'Блокировка экрана была освобождена');
    if (wakeLock) {
        wakeLock.removeEventListener('release', handleWakeLockRelease);
        wakeLock = null;
    }
};

/**
 * Обрабатывает изменение видимости страницы для переустановки блокировки.
 */
const handleVisibilityChange = () => {
    // Если мы хотим, чтобы блокировка была активна, и страница стала видимой,
    // а самой блокировки еще нет - запрашиваем ее.
    if (isWakeLockRequested && document.visibilityState === 'visible' && !wakeLock) {
        log('WAKELOCK', 'Страница снова видима, переустанавливаем блокировку экрана');
        void requestWakeLock();
    }
};

/**
 * Инициализирует Wake Lock и устанавливает обработчики.
 * Блокировка запрашивается сразу и переустанавливается при возвращении на вкладку.
 */
function initWakeLock() {
    // Если уже инициализировано, ничего не делаем
    if (isWakeLockRequested) {
        return;
    }

    isWakeLockRequested = true;
    void requestWakeLock();

    document.addEventListener('visibilitychange', handleVisibilityChange);
    // Освобождаем блокировку при закрытии вкладки
    window.addEventListener('beforeunload', () => {
        isWakeLockRequested = false;
        void releaseWakeLock();
    });
}

export { initWakeLock };