/**
 * UI-статус настроек конфигурации (success/warn/error)
 */

import {log} from '../../share/logger.js';
import {constants} from "../../share/constants.js";

function setStatusOk() {
    const el = document.getElementById('confStatus')
    if (!el) return
    el.className = 'conf-status ok'
    el.innerHTML = `<span class="icon">🟢</span> ${constants.MSG_CONF_SAVED}`
    log('CONF', 'Статус: OK')
}

function setStatusEdit() {
    const el = document.getElementById('confStatus')
    if (!el) return
    el.className = 'conf-status warn'
    el.innerHTML = `<span class="icon">✏️</span> ${constants.MSG_CONF_EDITED}`
    log('CONF', 'Статус: EDIT')
}

function setStatusError(message) {
    const el = document.getElementById('confStatus')
    if (!el) return
    el.className = 'conf-status error'
    el.innerHTML = `<span class="icon">🔴</span> <span class="err-text">${message || constants.MSG_CONF_DEFAULT_ERROR}</span>`
    log('CONF', message, 'error')
}


export {setStatusOk, setStatusEdit, setStatusError}