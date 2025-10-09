import {getElements} from '../ui/ui.js'

/**
 * Открытие модального окна настроек
 *
 * :param settings: объект текущих настроек
 */
function showSettingsModal(settings) {
    const elements = getElements()
    elements.settingsModal.style.display = 'flex'
    elements.logFormatInput.value = settings.logFormat
    elements.fontSizeInput.value = settings.fontSize
    elements.logLimitInput.value = settings.logLimit
    elements.logLevelSelect.value = settings.logLevel
    updateColorInputs(settings.colors)
}

/**
 * Обновить значения color picker'ов и текстовых инпутов цветов
 *
 * :param colors: объект цветов
 */
function updateColorInputs(colors) {
    ['debug', 'info', 'warning', 'error'].forEach(level => {
        const picker = document.getElementById(`${level}Color`)
        const codeInput = document.getElementById(`${level}ColorCode`)
        if (picker && codeInput) {
            picker.value = colors[level]
            codeInput.value = colors[level].toUpperCase()
        }
    })
}

/**
 * Скрыть модальное окно настроек
 */
function hideSettingsModal() {
    const elements = getElements()
    elements.settingsModal.style.display = 'none'
}

// Навешиваем закрытие окна настроек на кнопку-крестик
document.getElementById('closeSettingsModalBtn').addEventListener('click', hideSettingsModal)

export {
    showSettingsModal,
    hideSettingsModal,
    updateColorInputs
}