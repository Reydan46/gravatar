/**
 Универсальная функция debounce

 @param {Function} func Функция, которую необходимо дебаунсить
 @param {number} [delay=150] Задержка в миллисекундах
 @return {Function} Дебаунс-обёртка
 */
function debounce(func, delay = 150) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}

export {debounce};