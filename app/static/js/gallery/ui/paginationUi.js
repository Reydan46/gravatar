let onPageChangeCallback;

/**
 * Отрисовывает элементы управления пагинацией.
 * @param {function(number): void} onPageChange - Callback-функция при смене страницы.
 */
function renderPagination(onPageChange) {
    onPageChangeCallback = onPageChange;
    const controlsEl = document.getElementById('paginationControls');
    controlsEl.innerHTML = `
        <button id="firstPageBtn" class="pagination-btn" title="Первая страница">«</button>
        <button id="prevPageBtn" class="pagination-btn" title="Предыдущая страница">‹</button>
        <input type="number" id="pageInput" class="pagination-page-input" min="1" title="Номер страницы">
        <button id="nextPageBtn" class="pagination-btn" title="Следующая страница">›</button>
        <button id="lastPageBtn" class="pagination-btn" title="Последняя страница">»</button>
    `;

    document.getElementById('firstPageBtn').addEventListener('click', () => onPageChangeCallback(1));
    document.getElementById('prevPageBtn').addEventListener('click', () => {
        const currentPage = parseInt(document.getElementById('pageInput').value, 10);
        if (currentPage > 1) onPageChangeCallback(currentPage - 1);
    });
    document.getElementById('nextPageBtn').addEventListener('click', () => {
        const pageInput = document.getElementById('pageInput');
        const currentPage = parseInt(pageInput.value, 10);
        const maxPage = parseInt(pageInput.max, 10);
        if (currentPage < maxPage) onPageChangeCallback(currentPage + 1);
    });
    document.getElementById('lastPageBtn').addEventListener('click', () => {
        const maxPage = parseInt(document.getElementById('pageInput').max, 10);
        onPageChangeCallback(maxPage);
    });

    const pageInput = document.getElementById('pageInput');
    pageInput.addEventListener('change', (e) => {
        let newPage = parseInt(e.target.value, 10);
        const maxPage = parseInt(e.target.max, 10);
        if (isNaN(newPage) || newPage < 1) newPage = 1;
        if (newPage > maxPage) newPage = maxPage;
        e.target.value = newPage;
        onPageChangeCallback(newPage);
    });
}

/**
 * Обновляет состояние элементов пагинации.
 * @param {number} currentPage - Текущая страница.
 * @param {number} totalPages - Общее количество страниц.
 */
function updatePaginationState(currentPage, totalPages) {
    const pageInput = document.getElementById('pageInput');
    pageInput.value = currentPage;
    pageInput.max = totalPages;

    document.getElementById('firstPageBtn').disabled = currentPage <= 1;
    document.getElementById('prevPageBtn').disabled = currentPage <= 1;
    document.getElementById('nextPageBtn').disabled = currentPage >= totalPages;
    document.getElementById('lastPageBtn').disabled = currentPage >= totalPages;
}

export {renderPagination, updatePaginationState};