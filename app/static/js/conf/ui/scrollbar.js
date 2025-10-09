let permHeaders = null
const list = document.getElementById("usersList")

/**
 * Компенсация ширины скроллбара для ровных хедеров таблиц
 */
function setScrollbarCompensatorWidth(usersList) {
    /**
     * Вычисляет и устанавливает CSS-переменную для компенсации скроллбара
     */
    if (!usersList) return
    const hasScrollbar = usersList.scrollHeight > usersList.clientHeight + 1
    const scrollbarWidth = hasScrollbar ? (usersList.offsetWidth - usersList.clientWidth) : 0
    document.documentElement.style.setProperty('--scrollbar-compensator-width', `${scrollbarWidth}px`)

    if (!permHeaders) {
        permHeaders = document.getElementsByClassName('perm-header-icon')
    }
    for (let i = 0; i < permHeaders.length; i++) {
        if (permHeaders[i].style.display === 'none') {
            permHeaders[i].style.removeProperty('display')
        }
    }
}

window.addEventListener('resize', () => setScrollbarCompensatorWidth(list));

export {setScrollbarCompensatorWidth}