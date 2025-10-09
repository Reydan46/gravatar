/**
 Возвращает время в формате DD.MM.YYYY HH:MM:SS.mmm. Можно указать unixtime.

 @param {number} [unixtime] Метка времени в миллисекундах (опционально)
 @return {string} Отформатированная дата и время
 */
function getFormattedTime(unixtime) {
    const date = typeof unixtime === 'number' ? new Date(unixtime) : new Date();
    const pad = (n) => n.toString().padStart(2, '0');
    const day = pad(date.getDate());
    const month = pad(date.getMonth() + 1);
    const year = date.getFullYear();
    const hours = pad(date.getHours());
    const minutes = pad(date.getMinutes());
    const seconds = pad(date.getSeconds());
    const ms = date.getMilliseconds().toString().padStart(3, '0');
    return `${day}.${month}.${year} ${hours}:${minutes}:${seconds}.${ms}`;
}

/**
 Определяет имя функции-вызывателя для публичного логгера

 @return {string} Имя функции-вызывателя
 */
function getCallerFunctionName() {
    const err = new Error();
    const stack = err.stack ? err.stack.split('\n') : [];
    if (stack.length >= 4) {
        const match = stack[3].match(/at ([\w$.<>]+)/);
        if (match && match[1]) {
            return match[1];
        }
    }
    return '';
}

/**
 Логирование сообщений с автоматическим указанием имени вызывающей функции и типа лога

 @param {string} module Название модуля
 @param {string} message Сообщение для лога
 @param {...any} args Дополнительные аргументы или тип лога ('log', 'error', 'warn', 'info', 'debug')
 @return {void}
 */
function log(module, message, ...args) {
    let type = "debug";
    if (
        args.length &&
        typeof args[args.length - 1] === "string" &&
        ["log", "error", "warn", "info", "debug"].includes(args[args.length - 1])
    ) {
        type = args.pop();
    }
    const time = getFormattedTime();
    const functionName = getCallerFunctionName();
    const prefix = functionName
        ? `[${time}] [${module}] [${functionName}] ${message}`
        : `[${time}] [${module}] ${message}`;
    if (console[type]) {
        console[type](prefix, ...args);
    } else {
        console.log(prefix, ...args);
    }
}

export {log, getFormattedTime};