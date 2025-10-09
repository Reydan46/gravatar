import {constants} from "../../share/constants.js";

let elements = null

/**
 * Получение объекта всех основных интерфейсных элементов
 *
 * :return: объект с DOM-элементами
 */
function getElements() {
    if (elements) return elements
    elements = {
        // Контейнеры
        logsContainer: document.getElementById('logsContainer'),
        logDisplay: document.getElementById('logDisplay'),
        settingsModal: document.getElementById('settingsModal'),
        filterHelpModal: document.getElementById('filterHelpModal'),
        logsMenuContainer: document.getElementById('logsMenuContainer'),

        // Кнопки
        logoutBtn: document.getElementById('logoutBtn'),
        filterClear: document.getElementById('filterClear'),

        // Настройки и фильтры
        logFormatInput: document.getElementById('logFormat'),
        defaultFormatEl: document.getElementById('defaultFormat'),
        fontSizeInput: document.getElementById('fontSize'),
        logLimitInput: document.getElementById('logLimit'),
        logLevelSelect: document.getElementById('logLevelSelect'),
        filterInput: document.getElementById('filterInput'),

        // Выбор цветов
        debugColorPicker: document.getElementById('debugColor'),
        infoColorPicker: document.getElementById('infoColor'),
        warningColorPicker: document.getElementById('warningColor'),
        errorColorPicker: document.getElementById('errorColor'),
        scrollToBottomBtn: document.getElementById('scrollToBottomBtn')
    }
    return elements
}

/**
 * Плавная прокрутка к низу за заданное время

 * :param duration: Длительность анимации в миллисекундах
 */
function scrollToBottom(duration = constants.SCROLL_DEFAULT_DURATION_MS) {

    const logsContainer = document.querySelector('.logs-container')
    if (!logsContainer) return

    const start = logsContainer.scrollTop
    const end = logsContainer.scrollHeight - logsContainer.clientHeight
    const change = end - start
    const startTime = performance.now()

    function animateScroll(currentTime) {
        const elapsed = currentTime - startTime
        const progress = Math.min(elapsed / duration, 1)
        logsContainer.scrollTop = start + change * progress
        if (progress < 1) {
            requestAnimationFrame(animateScroll)
        }
    }

    requestAnimationFrame(animateScroll)
}

export {
    getElements,
    scrollToBottom
}