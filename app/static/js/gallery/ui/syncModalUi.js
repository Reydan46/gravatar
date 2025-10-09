import {syncAvatars} from '../api.js';
import {loadAndRenderGallery} from './galleryUi.js';
import {getLogLevelClass} from '../../logs/format/logFormatter.js';
import {getFormattedTime, log} from '../../share/logger.js';

let syncModal, syncLog, closeSyncModalBtn, startSyncBtn;
let isSyncing = false;

/**
 * Инициализирует модальное окно синхронизации.
 * @param {string|null} passphrase - Passphrase для выполнения запроса.
 */
function initSyncModal(passphrase) {
    syncModal = document.getElementById('syncModal');
    syncLog = document.getElementById('syncLog');
    closeSyncModalBtn = document.getElementById('closeSyncModalBtn');

    startSyncBtn = document.createElement('button');
    startSyncBtn.id = 'startSyncBtn-trigger';
    startSyncBtn.style.display = 'none';
    document.body.appendChild(startSyncBtn);

    startSyncBtn.addEventListener('click', () => startSync(passphrase));
    closeSyncModalBtn.addEventListener('click', hideModal);
    syncModal.addEventListener('click', (e) => {
        if (e.target === syncModal && !isSyncing) {
            hideModal();
        }
    });
}

/**
 * Начинает процесс синхронизации.
 * @param {string} passphrase - Passphrase.
 */
function startSync(passphrase) {
    if (isSyncing || !passphrase) return;
    isSyncing = true;

    showModal();
    syncLog.innerHTML = '';
    appendToLog('Запуск синхронизации...', 'starting');

    startSyncBtn.disabled = true;
    closeSyncModalBtn.disabled = true;

    syncAvatars(
        passphrase,
        (message) => { // onMessage
            log('SYNC', `Сообщение от сервера: ${message.message}`);
            appendToLog(message.message, message.status);
        },
        () => { // onComplete
            appendToLog('Синхронизация завершена.', 'completed');
            isSyncing = false;
            startSyncBtn.disabled = false;
            closeSyncModalBtn.disabled = false;
            void loadAndRenderGallery();
        },
        (error) => { // onError
            appendToLog(`ОШИБКА: ${error}`, 'error');
        }
    );
}

function showModal() {
    syncModal.style.display = 'flex';
}

function hideModal() {
    if (isSyncing) return;
    syncModal.style.display = 'none';
}

/**
 * Добавляет отформатированную запись в лог синхронизации.
 * @param {string} text - Текст сообщения.
 * @param {string} status - Статус сообщения ('starting', 'error', 'completed', etc.).
 */
function appendToLog(text, status) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const statusToLevelMap = {
        'error': 'ERROR',
        'completed': 'INFO',
        'starting': 'INFO',
        'fetching': 'DEBUG',
        'processing': 'DEBUG',
        'progress': 'DEBUG'
    };
    const level = statusToLevelMap[status] || 'DEBUG';
    const levelClass = getLogLevelClass(level);

    const span = document.createElement('span');
    span.className = levelClass;

    span.textContent = `[${getFormattedTime()}] ${text}`;

    entry.appendChild(span);
    syncLog.appendChild(entry);
    syncLog.scrollTop = syncLog.scrollHeight;
}

export {initSyncModal};