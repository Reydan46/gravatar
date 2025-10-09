/**
 * Экранирование спецсимволов для использования в new RegExp() из строки
 *
 * @param {string} string - строка для экранирования
 * @return {string} экранированная строка
 */
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Создает карту подсветки для текста на основе условий включения.
 *
 * @param {string} plainText - Чистый текст строки лога.
 * @param {object} filterConditions - Условия фильтрации.
 * @return {Array<boolean>} - Массив boolean, где true означает, что символ нужно подсветить.
 */
function buildHighlightMap(plainText, filterConditions) {
    const highlightMap = new Array(plainText.length).fill(false);
    if (!filterConditions || !filterConditions.include) {
        return highlightMap;
    }

    const allInclusionRules = [];
    filterConditions.include.forEach(rule => {
        if (rule.type === 'or') {
            allInclusionRules.push(...rule.value);
        } else {
            allInclusionRules.push(rule);
        }
    });

    allInclusionRules.forEach(rule => {
        if (!rule) return;
        let match;
        if (rule.type === 'phrase' && rule.value) {
            const phraseRegex = new RegExp(escapeRegExp(rule.value), 'gi');
            while ((match = phraseRegex.exec(plainText)) !== null) {
                if (match.index === phraseRegex.lastIndex) {
                    phraseRegex.lastIndex++;
                }
                for (let i = match.index; i < match.index + match[0].length; i++) {
                    highlightMap[i] = true;
                }
            }
        } else if (rule.type === 'regex') {
            const regex = new RegExp(rule.value, rule.value.flags.includes('g') ? rule.value.flags : rule.value.flags + 'g');
            regex.lastIndex = 0;
            while ((match = regex.exec(plainText)) !== null) {
                if (match[0].length === 0) break;
                for (let i = match.index; i < match.index + match[0].length; i++) {
                    highlightMap[i] = true;
                }
            }
        }
    });

    return highlightMap;
}

export {buildHighlightMap};