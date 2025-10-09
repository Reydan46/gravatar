/**
 Возвращает реальную высоту viewport

 @return {number} Высота viewport в пикселях
 */
function getRealViewportHeight() {
    if (window.visualViewport && window.visualViewport.height) {
        return window.visualViewport.height;
    }
    return window.innerHeight;
}

/**
 Фиксирует высоту viewport для корректной работы мобильных браузеров
 и устанавливает значение --app-viewport-height

 @return {void}
 */
function setAppHeight() {
    const h = getRealViewportHeight();
    document.documentElement.style.setProperty('--app-viewport-height', `${h}px`);
}

window.addEventListener('resize', setAppHeight);
window.addEventListener('DOMContentLoaded', setAppHeight);