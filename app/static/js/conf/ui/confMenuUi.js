import {log} from '../../share/logger.js';
import {constants} from '../../share/constants.js';
import {downloadBackup, uploadRestore} from '../api.js';
import {setStatusError, setStatusOk} from './statusUi.js';
import {showPromptModal} from './promptModal.js';
import {initializeMenu} from '../../share/menuHandler.js';

/**
 * Проверяет содержимое файла на соответствие формату.
 * @param {File} file - Файл для проверки.
 * @returns {Promise<{isValid: boolean, error?: string}>} - Результат проверки.
 */
function validateFileContent(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();

        reader.onload = (e) => {
            const content = e.target.result;

            // 1. Проверка на бинарность (наличие нулевых байтов)
            if (content.includes('\0')) {
                resolve({
                    isValid: false,
                    error: 'Выбранный файл является бинарным и не может быть обработан.'
                });
                return;
            }

            const trimmedContent = content.trim();

            // 2. Проверка на пустоту
            if (trimmedContent === '') {
                resolve({isValid: false, error: 'Файл конфигурации не может быть пустым.'});
                return;
            }

            // 3. Эвристическая проверка на структуру YAML (key: value)
            // Ищем хотя бы одну строку, которая выглядит как "ключ: значение".
            const yamlStructureRegex = /^\s*[\w-]+:\s*.*$/m;
            if (!yamlStructureRegex.test(trimmedContent)) {
                resolve({
                    isValid: false,
                    error: 'Файл не имеет структуры, похожей на YAML (key: value).'
                });
                return;
            }

            resolve({isValid: true});
        };

        reader.onerror = () => {
            resolve({isValid: false, error: 'Не удалось прочитать файл.'});
        };

        reader.readAsText(file);
    });
}


/**
 * Инициализирует меню действий с конфигурацией (бэкап/восстановление)
 */
function initConfMenu() {
    log('CONF', 'Инициализация меню действий с конфигурацией');
    const menuList = document.getElementById('confMenuList');
    const restoreFileInput = document.getElementById('restoreFileInput');

    if (!menuList || !restoreFileInput) {
        log('CONF', 'Элементы меню действий не найдены', 'warn');
        return;
    }

    const menuItems = [
        {
            label: 'Сохранить конфигурацию',
            icon: '💾',
            onClick: async () => {
                const result = await downloadBackup();
                if (result.success) {
                    setStatusOk('Резервная копия успешно создана и скачана.');
                } else {
                    setStatusError(result.error || 'Не удалось создать резервную копию.');
                }
            }
        },
        {
            label: 'Восстановить конфигурацию',
            icon: '📂',
            onClick: () => {
                restoreFileInput.click();
            }
        }
    ];

    menuList.innerHTML = '';
    menuItems.forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `<span class="nav-menu-icon">${item.icon}</span> ${item.label}`;
        li.onclick = async () => {
            await item.onClick();
            menuList.classList.remove('show');
        };
        menuList.appendChild(li);
    });

    restoreFileInput.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const validationResult = await validateFileContent(file);
        if (!validationResult.isValid) {
            await showPromptModal('Ошибка файла', {
                mode: constants.PROMPT_MODE_ALERT,
                error: validationResult.error
            });
            event.target.value = null;
            return;
        }

        const confirmed = await showPromptModal(
            'Вы уверены, что хотите восстановить конфигурацию из этого файла?',
            {
                mode: constants.PROMPT_MODE_CONFIRM,
                help: 'Текущие настройки будут полностью перезаписаны. Это действие нельзя отменить.',
                okLabel: 'Восстановить',
                cancelLabel: 'Отмена'
            }
        );

        if (confirmed) {
            try {
                const result = await uploadRestore(file);
                if (result.success) {
                    await showPromptModal('Конфигурация успешно восстановлена! Страница будет перезагружена.', {mode: 'alert'});
                    window.location.reload();
                }
            } catch (e) {
                await showPromptModal('Ошибка при восстановлении конфигурации.', {
                    mode: 'alert',
                    error: e.message
                });
            }
        }
        event.target.value = null;
    });

    initializeMenu(
        'confMenuContainer',
        'confMenuBtn',
        'confMenuList',
        constants.OPEN_CONF_MENU_ON_HOVER
    );
}

export {initConfMenu};