/**
 * Возвращает SVG-код для иконки "глаз".
 * @param {boolean} [crossed=false] - Если true, возвращает перечеркнутую иконку.
 * @returns {string} - SVG-разметка в виде строки.
 */
function getEyeIconSVG(crossed = false) {
    const strokeColor = "#898989";
    const strokeWidth = "2";
    if (crossed) {
        return `
            <path d="M1 1l22 22" stroke="${strokeColor}" stroke-width="${strokeWidth}"/>
            <path d="M12 5C6.5 5 2.7 9.11 2 12c.7 2.89 4.5 7 10 7s9.3-4.11 10-7c-.7-2.89-4.5-7-10-7z" fill="none" stroke="${strokeColor}" stroke-width="${strokeWidth}"/>
            <circle cx="12" cy="12" r="4" fill="none" stroke="${strokeColor}" stroke-width="${strokeWidth}"/>
        `;
    } else {
        return `
            <path d="M12 5C6.5 5 2.7 9.11 2 12c.7 2.89 4.5 7 10 7s9.3-4.11 10-7c-.7-2.89-4.5-7-10-7z" fill="none" stroke="${strokeColor}" stroke-width="${strokeWidth}"/>
            <circle cx="12" cy="12" r="4" fill="none" stroke="${strokeColor}" stroke-width="${strokeWidth}"/>
        `;
    }
}

export {getEyeIconSVG};