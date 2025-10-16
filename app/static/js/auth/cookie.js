/**
 * Функция для чтения значения cookie
 *
 * @param {string} name - имя куки
 * @return {string}
 */
function getCookie(name) {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith(name + '='))
        ?.split('=')[1]
    return cookieValue ? decodeURIComponent(cookieValue) : ''
}

export {getCookie}