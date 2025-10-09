/**
 * Вспомогательная функция для создания одного условия из строки-токена.
 * @param {string} token - Строка, представляющая один токен (фраза, regex или слово).
 * @returns {{type: 'phrase'|'regex', value: any}|null}
 */
function createConditionFromToken(token) {
    // 1. Регулярное выражение: /.../flags
    if (token.startsWith('/') && token.lastIndexOf('/') > 0) {
        const lastSlashIndex = token.lastIndexOf('/');
        const pattern = token.substring(1, lastSlashIndex);
        const flags = token.substring(lastSlashIndex + 1);
        try {
            return {type: 'regex', value: new RegExp(pattern, flags)};
        } catch (e) {
            console.warn(`Invalid regex: ${pattern}`);
            return null;
        }
    }

    // 2. Фраза в кавычках: "..."
    if (token.startsWith('"') && token.endsWith('"')) {
        const phrase = token.substring(1, token.length - 1);
        return {type: 'phrase', value: phrase};
    }

    // 3. Обычное слово
    return {type: 'phrase', value: token};
}

/**
 * Парсит строку фильтра и извлекает из нее условия для фильтрации.
 * Использует посимвольный обход строки для создания токенов.
 *
 * @param {string} filterText - Строка, введенная пользователем.
 * @return {{
 *   include: Array<{type: 'phrase'|'regex'|'or', value: any}>,
 *   exclude: Array<{type: 'phrase'|'regex'|'or', value: any}>
 * }} - Объект с условиями.
 */
function parseFilterConditions(filterText) {
    const conditions = {include: [], exclude: []};
    if (!filterText.trim()) return conditions;

    const andGroups = [];
    let currentOrGroup = [];
    let currentToken = '';
    let inQuote = false;
    let inRegex = false;
    let isEscaped = false;

    const finalizeToken = () => {
        if (currentToken) {
            currentOrGroup.push(currentToken);
            currentToken = '';
        }
    };

    const finalizeAndGroup = () => {
        finalizeToken();
        if (currentOrGroup.length > 0) {
            andGroups.push(currentOrGroup);
            currentOrGroup = [];
        }
    };

    for (const char of filterText) {
        if (isEscaped) {
            currentToken += char;
            isEscaped = false;
            continue;
        }

        if (char === '\\') {
            currentToken += char;
            isEscaped = true;
            continue;
        }

        if (inQuote || (inRegex && char !== '/')) {
            currentToken += char;
            if (char === '"' && !isEscaped) {
                inQuote = false;
            }
            continue;
        }

        if (char === '"') {
            inQuote = true;
            currentToken += char;
            continue;
        }
        if (char === '/') {
            if (!inRegex) {
                inRegex = true;
            } else {
                const nextChar = filterText[filterText.indexOf(char, currentToken.length - 1) + 1];
                const flags = 'gim';
                if (!isEscaped && (!nextChar || /\s/.test(nextChar) || !flags.includes(nextChar))) {
                    inRegex = false;
                }
            }
            currentToken += char;
            continue;
        }

        if (char === '|') {
            finalizeToken();
        } else if (/\s/.test(char)) {
            finalizeAndGroup();
        } else {
            currentToken += char;
        }
    }
    finalizeAndGroup();

    for (const group of andGroups) {
        let isExclude = false;
        if (group[0] && group[0].startsWith('-')) {
            isExclude = true;
            group[0] = group[0].substring(1);
            if (!group[0]) {
                group.shift();
            }
        }

        const unescapedGroup = group.map(token => token.replace(/\\(.)/g, '$1'));

        const orConditions = unescapedGroup
            .map(createConditionFromToken)
            .filter(c => c && !(c.type === 'phrase' && c.value === ''));

        if (orConditions.length === 0) continue;

        const targetList = isExclude ? conditions.exclude : conditions.include;

        if (orConditions.length > 1) {
            targetList.push({type: 'or', value: orConditions});
        } else {
            targetList.push(orConditions[0]);
        }
    }
    return conditions;
}

export {parseFilterConditions};