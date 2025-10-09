import {buildHighlightMap} from '../format/highlighter.js'
import {evaluateFilterConditions} from '../format/evaluator.js'
import {parseFilterConditions} from '../format/parser.js'
import {getElements, scrollToBottom} from './ui.js'
import {saveSettings} from '../../share/settings.js'
import {normalizeLogLevel} from '../format/logFormatter.js'
import {hideScrollBtn} from "./scrollToBottomBtn.js";
import {log} from '../../share/logger.js';
import {constants} from "../../share/constants.js";

let currentFilterText = ''
let currentFilterConditions = {
    include: [],
    exclude: []
};


/**
 * Фильтрует и подсвечивает одну запись лога.
 * Проверяет как текстовый фильтр, так и уровень логов (по текущему select'у).
 *
 * :param entry: DOM-элемент log-entry
 * :return: true, если отображается; false — скрыт
 */
function filterAndHighlightLog(entry) {
    try {
        const span = entry.querySelector('span');
        if (!span) return false;

        // Получаем выбранный minLogLevel из селектора
        const elements = getElements();
        let minLogLevel = constants.DEFAULT_LOG_LEVEL;
        if (elements.logLevelSelect && elements.logLevelSelect.value) {
            minLogLevel = elements.logLevelSelect.value;
        }

        // Проверяем соответствие уровню
        const logLevel = entry.dataset.logLevel;
        const normalizedLogLevel = normalizeLogLevel(logLevel);
        const showByLevel = constants.LOG_LEVEL_MAP[normalizedLogLevel] >= constants.LOG_LEVEL_MAP[minLogLevel];

        // Получаем оригинальный текст для фильтрации
        if (!entry.dataset.originalContent) {
            // Сохраняем изначальное содержимое, включая HTML-теги, если они есть
            entry.dataset.originalContent = span.innerHTML;
        }
        const originalText = entry.textContent || ''; // Для фильтрации используем чистый текст

        // Проверяем по текстовому фильтру
        const showByText = evaluateFilterConditions(originalText, currentFilterConditions);

        const shouldShow = showByLevel && showByText;
        entry.style.display = shouldShow ? '' : 'none';

        if (shouldShow) {
            // Подсветка применяется только если есть условия включения
            if (currentFilterConditions.include.length > 0) {
                applyHighlighting(span, entry.dataset.originalContent, currentFilterConditions);
            } else {
                // Если фильтров включения нет, возвращаем оригинальный контент без подсветки
                span.innerHTML = entry.dataset.originalContent;
            }
            return true;
        }
        return false;
    } catch (error) {
        log('LOGS', 'Error in filterAndHighlightLog:', error, 'error');
        return true; // В случае ошибки лучше показать лог, чем скрыть
    }
}

/**
 * Применяет подсветку к содержимому элемента на основе карты подсветки.
 *
 * @param {HTMLElement} spanElement - Элемент span, куда будет вставлен результат.
 * @param {string} originalContent - Исходное HTML-содержимое элемента.
 * @param {object} filterConditions - Условия фильтрации для создания карты.
 */
function applyHighlighting(spanElement, originalContent, filterConditions) {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = originalContent;
    const plainText = tempDiv.textContent || "";

    if (!plainText) {
        spanElement.innerHTML = originalContent;
        return;
    }

    const highlightMap = buildHighlightMap(plainText, filterConditions);

    let resultHTML = '';
    let textIndex = 0;
    let inHighlight = false;

    function processNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent;
            for (let i = 0; i < text.length; i++, textIndex++) {
                const shouldHighlight = highlightMap[textIndex];
                if (shouldHighlight && !inHighlight) {
                    resultHTML += '<mark class="highlight">';
                    inHighlight = true;
                } else if (!shouldHighlight && inHighlight) {
                    resultHTML += '</mark>';
                    inHighlight = false;
                }
                resultHTML += text[i].replace(/[&<>"']/g, c => ({
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#39;'
                }[c]));
            }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            resultHTML += `<${node.tagName.toLowerCase()}`;
            for (const attr of node.attributes) {
                resultHTML += ` ${attr.name}="${attr.value}"`;
            }
            resultHTML += '>';
            node.childNodes.forEach(processNode);
            resultHTML += `</${node.tagName.toLowerCase()}>`;
        }
    }

    tempDiv.childNodes.forEach(processNode);

    if (inHighlight) {
        resultHTML += '</mark>';
    }

    spanElement.innerHTML = resultHTML;
}


function filterLogs(filterText) {
    log('LOGS', 'Фильтрация логов по фильтру:', filterText);
    currentFilterText = filterText;
    saveSettings('filter', filterText);

    currentFilterConditions = parseFilterConditions(filterText);

    const elements = getElements();
    const logEntries = elements.logDisplay.querySelectorAll('.log-entry');
    logEntries.forEach(entry => {
        filterAndHighlightLog(entry);
    });
    scrollToBottom(constants.SCROLL_AFTER_CHANGE_LOG_FILTER_DURATION_MS);
    hideScrollBtn();
}

function initFilterUi(initialValue = '') {
    const elements = getElements()
    if (elements.filterInput) {
        elements.filterInput.value = initialValue
        if (initialValue) {
            filterLogs(initialValue)
        }
        elements.filterInput.addEventListener('input', () => {
            filterLogs(elements.filterInput.value)
        })
        elements.filterClear.addEventListener('click', () => {
            elements.filterInput.value = ''
            filterLogs('')
        })
    }
}

function setFilterValue(value) {
    const elements = getElements()
    if (elements.filterInput) {
        elements.filterInput.value = value
        filterLogs(value)
    }
}

export {
    filterLogs,
    filterAndHighlightLog,
    initFilterUi,
    setFilterValue
}