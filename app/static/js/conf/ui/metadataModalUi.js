import {log} from "../../share/logger.js";
import {constants} from "../../share/constants.js";
import {formatHostnameForFilename} from "../../share/textUtils.js";

let metadataContent = ''; // Храним загруженный контент для копирования

/**
 * Форматирует XML-строку, добавляя отступы для читаемости.
 * @param {string} xml - Исходная XML-строка.
 * @returns {string} - Отформатированный XML.
 */
function formatXml(xml) {
    let formatted = '', indent = '';
    const tab = '  '; // Используем два пробела для отступа
    xml.split(/>\s*</).forEach(node => {
        if (node.match(/^\/\w/)) { // Закрывающий тег
            indent = indent.substring(tab.length);
        }
        formatted += indent + '<' + node + '>\r\n';
        if (node.match(/^<?\w[^>]*[^\/]$/)) { // Открывающий тег
            indent += tab;
        }
    });
    return formatted.substring(1, formatted.length - 3);
}

/**
 * Создает DOM-структуру модального окна, если она еще не существует.
 */
function ensureMetadataModalExists() {
    if (document.getElementById('metadataModal')) return;

    const modalHTML = `
        <div id="metadataModal" class="modal metadata-modal" style="display: none;">
            <div class="modal-content">
                <div class="modal-title">SAML SP Metadata
                    <button id="closeMetadataModalBtn" class="close-btn">✕</button>
                </div>
                <div class="modal-body">
                    <pre id="metadataDisplay" class="metadata-modal-display" tabindex="0">Загрузка...</pre>
                    <div class="metadata-modal-footer">
                         <button id="copyMetadataBtn" class="btn btn-icon-text">
                            <span class="btn-icon">📋</span>
                            <span>Скопировать</span>
                        </button>
                        <button id="saveMetadataBtn" class="btn btn-icon-text">
                            <span class="btn-icon">💾</span>
                            <span>Сохранить в файл</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    const modal = document.getElementById('metadataModal');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
    document.getElementById('closeMetadataModalBtn').addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Обработчик для копирования в буфер
    document.getElementById('copyMetadataBtn').addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        const originalText = btn.querySelector('span:last-child').textContent;
        try {
            await navigator.clipboard.writeText(metadataContent);
            btn.querySelector('span:last-child').textContent = constants.MSG_COPIED;
            btn.disabled = true;
            setTimeout(() => {
                btn.querySelector('span:last-child').textContent = originalText;
                btn.disabled = false;
            }, 1500);
        } catch (err) {
            log('CONF', 'Failed to copy metadata to clipboard', err, 'error');
            btn.querySelector('span:last-child').textContent = constants.MSG_COPY_ERROR;
            setTimeout(() => {
                btn.querySelector('span:last-child').textContent = originalText;
            }, 2000);
        }
    });
}

/**
 * Открывает модальное окно и загружает метаданные.
 */
async function showMetadataModal() {
    ensureMetadataModalExists(); // Убедимся, что DOM на месте

    const modal = document.getElementById('metadataModal');
    const display = document.getElementById('metadataDisplay');
    const saveBtn = document.getElementById('saveMetadataBtn');
    const copyBtn = document.getElementById('copyMetadataBtn');

    modal.style.display = 'flex';
    display.textContent = 'Загрузка...';
    saveBtn.disabled = true;
    copyBtn.disabled = true;

    try {
        const response = await fetch('/saml/metadata');
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Ошибка ${response.status}`);
        }
        metadataContent = await response.text(); // Сохраняем оригинал для копирования
        display.textContent = formatXml(metadataContent);

        saveBtn.onclick = () => {
            const hostname = formatHostnameForFilename(window.location.hostname);
            const filename = `${constants.SERVICE_NAME}_metadata_${hostname}.xml`;
            const blob = new Blob([metadataContent], {type: 'application/xml'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        };
        saveBtn.disabled = false;
        copyBtn.disabled = false;

    } catch (error) {
        metadataContent = '';
        display.textContent = `Не удалось загрузить метаданные:\n\n${error.message}`;
        saveBtn.disabled = true;
        copyBtn.disabled = true;
    }
}

export {showMetadataModal};