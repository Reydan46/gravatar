/**
 * Возвращает правильную форму множественного числа для русского языка.
 * @param {number} number - Число.
 * @param {string} one - Форма для 1 (день).
 * @param {string} few - Форма для 2-4 (дня).
 * @param {string} many - Форма для 5+ (дней).
 * @returns {string} - Правильная форма слова.
 */
function getPluralForm(number, one, few, many) {
    number = Math.abs(number) % 100;
    const lastDigit = number % 10;

    if (number > 10 && number < 20) return many;
    if (lastDigit > 1 && lastDigit < 5) return few;
    if (lastDigit === 1) return one;
    return many;
}

/**
 * Конвертирует объект с единицами времени в человекочитаемый формат.
 * Суммирует все переданные единицы и форматирует результат.
 * @param {object} timeUnits - Объект с единицами времени.
 * @param {number} [timeUnits.days=0] - Количество дней.
 * @param {number} [timeUnits.hours=0] - Количество часов.
 * @param {number} [timeUnits.minutes=0] - Количество минут.
 * @param {number} [timeUnits.seconds=0] - Количество секунд.
 * @returns {string} - Отформатированная строка.
 */
function formatTimeDuration({days = 0, hours = 0, minutes = 0, seconds = 0} = {}) {
    const totalSeconds = (days * 24 * 60 * 60) + (hours * 60 * 60) + (minutes * 60) + seconds;

    if (isNaN(totalSeconds) || totalSeconds < 0) {
        return '';
    }
    if (totalSeconds === 0) {
        return '0 секунд';
    }

    const secondsInMinute = 60;
    const secondsInHour = 60 * secondsInMinute;
    const secondsInDay = 24 * secondsInHour;

    const calculatedDays = Math.floor(totalSeconds / secondsInDay);
    let remainingSeconds = totalSeconds % secondsInDay;

    const calculatedHours = Math.floor(remainingSeconds / secondsInHour);
    remainingSeconds %= secondsInHour;

    const calculatedMinutes = Math.floor(remainingSeconds / secondsInMinute);
    const calculatedSeconds = remainingSeconds % secondsInMinute;

    const parts = [];
    if (calculatedDays > 0) {
        parts.push(`${calculatedDays} ${getPluralForm(calculatedDays, 'день', 'дня', 'дней')}`);
    }
    if (calculatedHours > 0) {
        parts.push(`${calculatedHours} ${getPluralForm(calculatedHours, 'час', 'часа', 'часов')}`);
    }
    if (calculatedMinutes > 0) {
        parts.push(`${calculatedMinutes} ${getPluralForm(calculatedMinutes, 'минута', 'минуты', 'минут')}`);
    }
    if (calculatedSeconds > 0) {
        parts.push(`${calculatedSeconds} ${getPluralForm(calculatedSeconds, 'секунда', 'секунды', 'секунд')}`);
    }

    return parts.join(' ');
}


/**
 * Случайная строка
 *
 * @param {number} length - длина
 * @param {string} characters - Набор символов для генерации
 * @return {string} строка
 */
function generateRandomString(length, characters) {
    const array = new Uint8Array(length)
    window.crypto.getRandomValues(array)
    let res = ''
    for (let i = 0; i < length; i++) {
        res += characters[array[i] % characters.length]
    }
    return res
}

/**
 * Преобразует имя хоста в безопасный для имени файла формат.
 * @param {string} hostname - Имя хоста из `window.location.hostname`.
 * @returns {string} - Отформатированная строка.
 */
function formatHostnameForFilename(hostname) {
    if (!hostname) {
        return '';
    }
    // Заменяем точки и двоеточия на подчеркивания, удаляем небезопасные символы
    return hostname.replace(/[.:]/g, '_').replace(/[^a-zA-Z0-9_-]/g, '');
}


export {generateRandomString, formatTimeDuration, formatHostnameForFilename}