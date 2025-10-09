/**
 * Вспомогательная функция для проверки одного правила.
 * @param {string} text - Текст лога.
 * @param {object} rule - Правило для проверки.
 * @returns {boolean}
 */
function checkSingleRule(text, rule) {
    if (!rule) return false;
    if (rule.type === 'regex') {
        rule.value.lastIndex = 0;
        return rule.value.test(text);
    }
    if (rule.type === 'phrase') {
        return text.toLowerCase().includes(rule.value.toLowerCase());
    }
    return false;
}

/**
 * Проверяет, соответствует ли строка текста заданным условиям фильтрации.
 *
 * @param {string} text - Текст для проверки (строка лога).
 * @param {object} conditions - Объект с условиями, полученный от parseFilterConditions.
 * @return {boolean} - true, если текст проходит фильтрацию, иначе false.
 */
function evaluateFilterConditions(text, conditions) {
    // 1. Проверка на ИСКЛЮЧЕНИЕ. Если совпадает хоть одно, строка не проходит.
    for (const rule of conditions.exclude) {
        if (rule.type === 'or') {
            if (rule.value.some(subRule => checkSingleRule(text, subRule))) {
                return false;
            }
        } else if (checkSingleRule(text, rule)) {
            return false;
        }
    }

    // 2. Если правил включения нет, строка проходит (если не была исключена).
    if (conditions.include.length === 0) {
        return true;
    }

    // 3. Проверяем, что строка соответствует ВСЕМ правилам в AND-списке.
    return conditions.include.every(rule => {
        if (rule.type === 'or') {
            // Для OR-группы достаточно, чтобы совпало хотя бы одно внутреннее правило.
            return rule.value.some(subRule => checkSingleRule(text, subRule));
        }
        return checkSingleRule(text, rule);
    });
}

export {evaluateFilterConditions};