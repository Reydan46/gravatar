import {scrollToBottom} from './ui.js'
import {constants} from '../../share/constants.js';

let lastVisible = false

/**
 * Обновление UI-кнопки прокрутки к низу
 */
function updateScrollToBottomButton() {
    const logsContainer = document.querySelector('.logs-container')
    if (!logsContainer) return;

    const atBottom = logsContainer.scrollHeight - logsContainer.clientHeight <= logsContainer.scrollTop +
        constants.SCROLL_THRESHOLD
    if (!atBottom) {
        showScrollBtn()
    } else {
        hideScrollBtn()
    }
}

/**
 * Инициализация UI-кнопки прокрутки к низу
 */
function initScrollToBottomButton() {
    const logsContainer = document.querySelector('.logs-container')
    if (!logsContainer) return

    let btn = document.getElementById('scrollToBottomBtn')
    if (!btn) {
        btn = document.createElement('button')
        btn.id = 'scrollToBottomBtn'
        btn.type = 'button'
        btn.innerHTML = `<svg width="32" height="32" viewBox="0 0 32 32">
          <circle cx="16" cy="16" r="15" fill="#7575756b" />
          <path d="M10 13l6 7 6-7" stroke="#ffffffa8" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>`
        btn.className = 'scroll-to-bottom-btn'
        btn.style.display = 'none'
        document.body.appendChild(btn)
    }

    btn.onclick = () => {
        scrollToBottom()
        setTimeout(() => hideScrollBtn(), constants.SCROLL_BTN_HIDE_DELAY_MS)
    }

    let scrollTimeout;
    logsContainer.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            updateScrollToBottomButton()
        }, constants.SCROLL_UPDATE_DEBOUNCE_MS)
    })
}

function showScrollBtn() {
    if (!lastVisible) {
        let btn = document.getElementById('scrollToBottomBtn')
        if (!btn) return;
        btn.style.display = 'block'
        requestAnimationFrame(() => {
            btn.classList.add('visible')
        })
        lastVisible = true
    }
}

function hideScrollBtn() {
    if (lastVisible) {
        let btn = document.getElementById('scrollToBottomBtn')
        if (!btn) return;
        btn.classList.remove('visible')
        lastVisible = false
    }
}

export {initScrollToBottomButton, updateScrollToBottomButton, hideScrollBtn}