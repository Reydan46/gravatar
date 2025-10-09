/**
 * Функция для чтения значения cookie

 * :param name: имя куки
 * :return: строка
 */
function getCookie(name) {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith(name + '='))
        ?.split('=')[1]
    return cookieValue ? decodeURIComponent(cookieValue) : ''
}

export {getCookie}