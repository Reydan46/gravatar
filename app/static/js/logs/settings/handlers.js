import {saveSettings} from '../../share/settings.js'
import {updateAllLogFormats, applyLogLevelFilter} from '../format/logFormatter.js'
import {getElements, scrollToBottom} from '../ui/ui.js'
import {hideScrollBtn} from "../ui/scrollToBottomBtn.js";
import {closeAllConnections, setupEventSource} from "../stream/logStream.js"
import {debounce} from '../../share/debounce.js'
import {hideSettingsModal} from "./ui.js";
import {log} from "../../share/logger.js";
import {constants} from "../../share/constants.js";

let logLimitApplyTimeout = null
const elements = getElements()

/**
 * Применяет новый формат логов
 *
 * :param settings: настройки логов
 */
function applyLogFormat(settings) {
    const newFormat = elements.logFormatInput.value.trim()
    if (newFormat && newFormat !== settings.logFormat) {
        settings.logFormat = newFormat
        saveSettings('logFormat', newFormat)
        updateAllLogFormats(newFormat)
    }
}

/**
 * Применяет размер шрифта
 *
 * :param settings: настройки логов
 */
function applyFontSettings(settings) {
    const newFontSize = elements.fontSizeInput.value
    if (newFontSize !== settings.fontSize) {
        settings.fontSize = newFontSize
        saveSettings('fontSize', newFontSize)
        document.documentElement.style.setProperty('--log-font-size', `${newFontSize}px`)
    }
}

/**
 * Применяет лимит логов (кол-во отображаемых)
 *
 * :param settings: настройки логов
 */
function applyLogLimitSettings(settings) {
    const newLogLimit = elements.logLimitInput.value
    if (newLogLimit !== settings.logLimit) {
        settings.logLimit = newLogLimit
        saveSettings('logLimit', newLogLimit)
        if (logLimitApplyTimeout) clearTimeout(logLimitApplyTimeout)
        logLimitApplyTimeout = setTimeout(() => {
            closeAllConnections()
            setupEventSource(settings)
        }, constants.DEBOUNCE_LOG_LIMIT_APPLY)
    }
}

/**
 * Обновляет цвет уровня логирования в UI и настройках
 *
 * :param level: уровень лога
 * :param color: строка цвета
 * :param settings: настройки логов
 */
function updateColorValue(level, color, settings) {
    document.documentElement.style.setProperty(`--${level}-color`, color)
    settings.colors[level] = color
    saveSettings(`${level}Color`, color)
    const codeElement = document.getElementById(`${level}ColorCode`)
    if (codeElement) {
        codeElement.value = color.toUpperCase()
    }
}

/**
 * Сброс всех цветов к дефолтным
 *
 * :param settings: настройки логов
 */
function resetColors(settings) {
    Object.keys(settings.colors).forEach(level => {
        const defaultColor = settings.colors[level]
        settings.colors[level] = defaultColor
        document.documentElement.style.setProperty(`--${level}-color`, defaultColor)
        saveSettings(`${level}Color`, defaultColor)
        const colorInput = document.getElementById(`${level}Color`)
        if (colorInput) {
            colorInput.value = defaultColor
        }
        const codeElement = document.getElementById(`${level}ColorCode`)
        if (codeElement) {
            codeElement.value = defaultColor.toUpperCase()
            codeElement.classList.remove('invalid')
        }
    })
}

/**
 * Применяет выбор минимального уровня отображаемых логов
 *
 * :param settings: настройки логов
 */
function applyLogLevelSettings(settings) {
    const newLogLevel = elements.logLevelSelect.value
    if (newLogLevel !== settings.logLevel) {
        settings.logLevel = newLogLevel
        saveSettings('logLevel', newLogLevel)
        applyLogLevelFilter(newLogLevel)
        scrollToBottom(constants.SCROLL_AFTER_CHANGE_LOG_LEVEL_DURATION_MS)
        hideScrollBtn()
    }
}

/**
 * Проверяет валидность hex цвета
 *
 * :param color: строка
 * :return: boolean
 */
function isValidColorCode(color) {
    return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(color)
}

/**
 * Приводит hex short (#abc) в full (#aabbcc)
 *
 * :param color: hex-код
 * :return: нормализованный hex-код
 */
function normalizeColorCode(color) {
    if (color.length === 4) {
        const r = color[1]
        const g = color[2]
        const b = color[3]
        return `#${r}${r}${g}${g}${b}${b}`.toUpperCase()
    }
    return color.toUpperCase()
}

/**
 * Инициализация обработчиков всех элементов формы настроек логов
 *
 * :param settings: настройки логов
 */
function initSettingsHandlers(settings) {
    elements.logFormatInput.addEventListener('input', () => {
        clearTimeout(elements.logFormatInput.timeout)
        elements.logFormatInput.timeout = setTimeout(() => applyLogFormat(settings), constants.DEBOUNCE_SETTINGS_INPUT)
    })
    initFontSizeHandlers(settings)
    initLogLimitHandlers(settings)
    initDefaultFormatHandler()
    initModalCloseHandler()
    elements.logLevelSelect.addEventListener('change', () => applyLogLevelSettings(settings))

    // Цвета
    const colorInputs = document.querySelectorAll('.color-picker')
    colorInputs.forEach(input => {
        const debouncedSetColor = debounce(() => {
            const level = input.dataset.level
            const color = input.value
            updateColorValue(level, color, settings)
        }, constants.DEBOUNCE_COLOR_PICKER)
        input.addEventListener('input', debouncedSetColor)
    })
    const colorCodeInputs = document.querySelectorAll('.color-code')
    colorCodeInputs.forEach(input => {
        input.addEventListener('input', function () {
            let value = this.value
            if (value && !value.startsWith('#')) {
                value = '#' + value
                this.value = value
            }
            const isValid = isValidColorCode(value)
            this.classList.toggle('invalid', !isValid)
            if (isValid) {
                if (value.length === 4) {
                    value = normalizeColorCode(value)
                }
                const levelId = this.id.replace('ColorCode', '')
                const pickerElement = document.getElementById(`${levelId}Color`)
                if (pickerElement) {
                    pickerElement.value = value
                }
                updateColorValue(levelId, value, settings)
            }
        })
        input.addEventListener('blur', function () {
            let value = this.value.trim()
            const levelId = this.id.replace('ColorCode', '')
            if (!value || !isValidColorCode(value)) {
                this.value = settings.colors[levelId].toUpperCase()
                this.classList.remove('invalid')
                return
            }
            this.value = normalizeColorCode(value)
        })
    })

    // Сброс цветов по кнопке
    document.getElementById('resetColorsBtn')
        .addEventListener('click', () => resetColors(settings))
}

function initModalCloseHandler() {
    const elements = getElements()
    if (elements.settingsModal) {
        elements.settingsModal.addEventListener('click', (e) => {
            // Проверяем, что клик был именно по overlay, а не по окну настроек
            if (e.target === elements.settingsModal) {
                hideSettingsModal()
            }
        })
    }
}

/**
 * Навешивает обработчики на кнопки управления размером шрифта
 *
 * :param settings: настройки логов
 */
function initFontSizeHandlers(settings) {
    elements.fontSizeInput.addEventListener('input', () => applyFontSettings(settings))
    document.querySelector('.font-control.up').addEventListener('click', () => {
        const input = elements.fontSizeInput
        const currentValue = parseInt(input.value)
        const maxValue = parseInt(input.max)
        if (currentValue < maxValue) {
            input.value = currentValue + 1
            applyFontSettings(settings)
        }
    })
    document.querySelector('.font-control.down').addEventListener('click', () => {
        const input = elements.fontSizeInput
        const currentValue = parseInt(input.value)
        const minValue = parseInt(input.min)
        if (currentValue > minValue) {
            input.value = currentValue - 1
            applyFontSettings(settings)
        }
    })
}

/**
 * Навешивает обработчики на кнопки управления лимитом логов
 *
 * :param settings: настройки логов
 */
function initLogLimitHandlers(settings) {
    elements.logLimitInput.addEventListener('input', () => applyLogLimitSettings(settings))
    document.querySelector('.log-limit-control.up').addEventListener('click', () => {
        const input = elements.logLimitInput
        const currentValue = parseInt(input.value)
        const maxValue = parseInt(input.max)
        if (currentValue < maxValue) {
            input.value = Math.min(currentValue + 1, maxValue)
            applyLogLimitSettings(settings)
        }
    })
    document.querySelector('.log-limit-control.down').addEventListener('click', () => {
        const input = elements.logLimitInput
        const currentValue = parseInt(input.value)
        const minValue = parseInt(input.min)
        if (currentValue > minValue) {
            input.value = Math.max(currentValue - 1, minValue)
            applyLogLimitSettings(settings)
        }
    })
}

function initDefaultFormatHandler() {
    const elements = getElements()
    if (elements.defaultFormatEl) {
        elements.defaultFormatEl.addEventListener('click', async function () {
            const selection = window.getSelection()
            const range = document.createRange()
            range.selectNodeContents(this)
            selection.removeAllRanges()
            selection.addRange(range)

            const text = this.textContent
            let copySuccess = true
            let errorMsg = ''

            try {
                await navigator.clipboard.writeText(text)
            } catch (e) {
                try {
                    // noinspection JSDeprecatedSymbols
                    document.execCommand('copy')
                } catch (err) {
                    copySuccess = false
                    errorMsg = 'Ошибка копирования!'
                    log('LOGS', 'Clipboard copy failed:', err, 'error')
                }
            }
            selection.removeAllRanges()
            const oldTooltip = this.querySelector('.copy-tooltip')
            if (oldTooltip) oldTooltip.remove()
            const tooltip = document.createElement('div')
            tooltip.className = 'copy-tooltip'
            tooltip.textContent = copySuccess ? 'Скопировано!' : (errorMsg || 'Не удалось скопировать')
            tooltip.style.userSelect = 'none'
            this.appendChild(tooltip)
            this.classList.add('copied-background')
            setTimeout(() => {
                this.classList.remove('copied-background')
                tooltip.remove()
            }, constants.TOOLTIP_FADE_DURATION_MS)
        })
    }
}

export {
    applyLogFormat,
    applyFontSettings,
    applyLogLimitSettings,
    resetColors,
    applyLogLevelSettings,
    initSettingsHandlers
}