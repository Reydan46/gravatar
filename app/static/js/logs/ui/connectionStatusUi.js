import {debounce} from '../../share/debounce.js';

let statusEl = null;
let statusTextEl = null;
let headerEl = null;
let fadeOutTimeout = null;
let countdownInterval = null;

/**
 * Динамически вычисляет и устанавливает позицию статус-бара под шапкой.
 */
function updateStatusPosition() {
    if (!statusEl) statusEl = document.getElementById('connectionStatus');
    if (!headerEl) headerEl = document.querySelector('.header');

    if (statusEl && headerEl) {
        statusEl.style.top = `${headerEl.offsetHeight}px`;
    }
}

/**
 * Инициализирует UI для статуса соединения.
 * Устанавливает обработчик клика и позиционирует элемент.
 */
export function initConnectionStatus() {
    statusEl = document.getElementById('connectionStatus');
    statusTextEl = document.getElementById('connectionStatusText');

    if (statusEl) {
        statusEl.addEventListener('click', hideStatus);
    }

    updateStatusPosition();
    window.addEventListener('resize', debounce(updateStatusPosition, 100));
}

function clearTimers() {
    clearTimeout(fadeOutTimeout);
    clearInterval(countdownInterval);
    fadeOutTimeout = null;
    countdownInterval = null;
}

function setStatus(className, text) {
    if (!statusEl || !statusTextEl) return;

    clearTimers(); // Очищаем все предыдущие таймеры
    statusEl.className = `connection-status ${className}`;
    statusTextEl.textContent = text;
    statusEl.style.animation = 'none'; // Сброс анимации
    statusEl.classList.remove('hidden');
    statusEl.style.pointerEvents = 'auto';
}

/**
 * Показывает статус "Подключение..."
 */
export function showConnecting() {
    setStatus('connecting', 'Подключение к потоку логов...');
}

/**
 * Показывает статус "Соединение установлено" и плавно скрывает его.
 */
export function showConnected() {
    setStatus('connected', 'Соединение установлено');
    requestAnimationFrame(() => {
        statusEl.style.animation = '';
    });
    fadeOutTimeout = setTimeout(hideStatus, 1000); // 0.5с задержка + 0.5с анимация
}

/**
 * Показывает статус "Соединение потеряно" с динамическим обратным отсчетом.
 * @param {number} reconnectDelayMs - Задержка в миллисекундах.
 */
export function showDisconnected(reconnectDelayMs) {
    let secondsLeft = Math.round(reconnectDelayMs / 1000);
    const baseText = 'Соединение потеряно. Повторная попытка через';

    setStatus('disconnected', `${baseText} ${secondsLeft} сек...`);

    countdownInterval = setInterval(() => {
        secondsLeft--;
        if (secondsLeft > 0) {
            if (statusTextEl) {
                statusTextEl.textContent = `${baseText} ${secondsLeft} сек...`;
            }
        } else {
            clearInterval(countdownInterval);
            countdownInterval = null;
            if (statusTextEl) {
                statusTextEl.textContent = 'Переподключение...';
            }
        }
    }, 1000);
}

/**
 * Принудительно скрывает статус-бар и очищает все связанные таймеры.
 */
export function hideStatus() {
    clearTimers();
    if (statusEl) {
        statusEl.classList.add('hidden');
    }
}