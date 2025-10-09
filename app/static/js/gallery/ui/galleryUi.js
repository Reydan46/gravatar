import {fetchGalleryData} from '../api.js';
import {renderPagination, updatePaginationState} from './paginationUi.js';
import {debounce} from '../../share/debounce.js';
import {log} from '../../share/logger.js';
import {constants} from "../../share/constants.js";

// === State Variables ===
let currentPage = 1;
let pageSize = localStorage.getItem('galleryPageSize') || String(constants.DEFAULT_PAGE_SIZE);
const validPageSizes = [...constants.PAGE_SIZE_OPTIONS.map(String), 'infinite', 'all'];
if (!validPageSizes.includes(pageSize)) {
    pageSize = String(constants.DEFAULT_PAGE_SIZE);
}
let currentFilters = {
    email: '',
    size: '',
    file_size: '',
    md5: '',
    sha256: ''
};
let currentSort = {
    field: 'email',
    direction: 'asc'
};
let isLoading = false;
let hasMorePages = true;
let totalItemsCount = 0;
let lazyLoadObserver;

// === DOM Elements ===
const galleryListEl = document.getElementById('galleryList');
const galleryInfoEl = document.getElementById('galleryInfo');
const loadingOverlay = document.getElementById('loadingOverlay');
const imageModal = document.getElementById('imageModal');
const modalImage = document.getElementById('modalImage');
const modalInfoEl = document.getElementById('modalInfo');
const paginationControlsEl = document.getElementById('paginationControls');
const scrollUpBtn = document.getElementById('scrollUpBtn');
const scrollDownBtn = document.getElementById('scrollDownBtn');
const bottomLoadingIndicator = document.getElementById('bottomLoadingIndicator');

/**
 * Toggles the main loading overlay (for initial load/filter).
 * @param {boolean} show - Whether to show the overlay.
 */
function toggleMainLoading(show) {
    isLoading = show;
    loadingOverlay.classList.toggle('hidden', !show);
}

/**
 * Toggles the bottom loading indicator (for infinite scroll).
 * @param {boolean} show - Whether to show the indicator.
 */
function toggleBottomLoading(show) {
    bottomLoadingIndicator.classList.toggle('visible', show);
}

/**
 * Resets the gallery state for new filters or page size changes.
 * @param {boolean} clearContent - Whether to clear the displayed list.
 */
function resetGallery(clearContent = true) {
    currentPage = 1;
    hasMorePages = true;
    if (clearContent) {
        galleryListEl.innerHTML = '';
        galleryListEl.scrollTop = 0;
    }
}

/**
 * Fetches and renders gallery data.
 */
async function loadAndRenderGallery() {
    if (isLoading) return;

    const isInitialLoad = currentPage === 1;
    if (isInitialLoad) {
        toggleMainLoading(true);
    } else {
        toggleBottomLoading(true);
    }
    isLoading = true;

    try {
        let effectivePageSize;
        if (pageSize === 'infinite') {
            effectivePageSize = constants.INFINITE_SCROLL_PAGE_SIZE;
        } else if (pageSize === 'all') {
            effectivePageSize = 0; // 0 для загрузки всех элементов
        } else {
            effectivePageSize = parseInt(pageSize, 10);
        }

        const data = await fetchGalleryData({
            page: currentPage,
            pageSize: effectivePageSize,
            filters: currentFilters,
            sortBy: currentSort.field,
            sortDir: currentSort.direction
        });

        if (currentPage === 1) {
            totalItemsCount = data.total_items;
        }

        const isAppendMode = pageSize === 'infinite' && currentPage > 1;
        renderGalleryItems(data.items, !isAppendMode);

        updateGalleryInfo();

        if (pageSize === 'infinite') {
            hasMorePages = data.current_page < data.total_pages;
            currentPage++;
        } else {
            // Для 'all' и обычной пагинации больше не загружаем
            hasMorePages = false;
            updatePaginationState(data.current_page, data.total_pages);
        }
    } catch (error) {
        galleryListEl.innerHTML = `<div class="gallery-cell error-message">${error.message}</div>`;
        totalItemsCount = 0;
        updateGalleryInfo();
        hasMorePages = false;
        if (pageSize !== 'infinite' && pageSize !== 'all') {
            updatePaginationState(1, 1);
        }
    } finally {
        isLoading = false;
        if (isInitialLoad) {
            toggleMainLoading(false);
        } else {
            toggleBottomLoading(false);
        }
        updateScrollButtons();
    }
}


/**
 * Formats file size in bytes into a human-readable string (KB, MB, etc.).
 * @param {number} bytes - The file size in bytes.
 * @returns {string} - The formatted file size.
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Renders gallery items using requestAnimationFrame for smoother appending.
 * @param {Array<object>} items - Array of avatar data.
 * @param {boolean} shouldClear - Whether to clear the list before appending.
 */
function renderGalleryItems(items, shouldClear) {
    if (items.length === 0 && shouldClear) {
        galleryListEl.innerHTML = '<div class="gallery-cell">Ничего не найдено.</div>';
        return;
    }

    const fragment = document.createDocumentFragment();
    items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'gallery-row';
        const formattedSize = formatFileSize(item.file_size);
        row.innerHTML = `
            <div class="gallery-cell cell-photo">
                <img data-src="/avatar/${item.md5}?s=${constants.GALLERY_AVATAR_PREVIEW_SIZE}" alt="Аватар ${item.email}" class="avatar-image" data-item='${JSON.stringify(item)}'>
            </div>
            <div class="gallery-cell cell-email" title="${item.email}">${item.email}</div>
            <div class="gallery-cell cell-size" title="${item.size}">${item.size}</div>
            <div class="gallery-cell cell-file-size" title="${item.file_size} bytes">${formattedSize}</div>
            <div class="gallery-cell cell-md5" title="${item.md5}">${item.md5}</div>
            <div class="gallery-cell cell-sha256" title="${item.sha256}">${item.sha256}</div>
        `;
        fragment.appendChild(row);
    });

    if (shouldClear) {
        galleryListEl.innerHTML = '';
    }
    galleryListEl.appendChild(fragment);

    const images = galleryListEl.querySelectorAll('img[data-src]');
    images.forEach(img => lazyLoadObserver.observe(img));
}


/**
 * Updates the gallery information text.
 */
function updateGalleryInfo() {
    const itemsOnPage = galleryListEl.children.length;
    galleryInfoEl.textContent = `Показано ${itemsOnPage} из ${totalItemsCount}`;
}

/**
 * Handles page changes from pagination controls.
 * @param {number} newPage - The new page number.
 */
function onPageChange(newPage) {
    if (newPage !== currentPage) {
        currentPage = newPage;
        galleryListEl.scrollTop = 0;
        void loadAndRenderGallery();
    }
}

/**
 * Initializes all gallery controls, filters, pagination, and interactions.
 */
function initGalleryControls() {
    renderPagination(onPageChange);
    setupLazyLoader();
    setupInfiniteScroll();
    setupScrollButtons();
    setupSorting();
    setupFilterControls();

    galleryListEl.addEventListener('click', (e) => {
        if (e.target.classList.contains('avatar-image')) {
            const itemData = JSON.parse(e.target.dataset.item);
            modalImage.src = `/avatar/${itemData.md5}?o=y`;
            modalInfoEl.innerHTML = `
                <div class="info-row"><span class="info-label">Email:</span> <span class="info-value">${itemData.email}</span></div>
                <div class="info-row"><span class="info-label">Размер:</span> <span class="info-value">${itemData.size}</span></div>
                <div class="info-row"><span class="info-label">Файл:</span> <span class="info-value">${formatFileSize(itemData.file_size)} (${itemData.file_size} bytes)</span></div>
                <div class="info-row"><span class="info-label">MD5:</span> <span class="info-value"><a href="/avatar/${itemData.md5}" target="_blank">${itemData.md5}</a></span></div>
                <div class="info-row"><span class="info-label">SHA256:</span> <span class="info-value"><a href="/avatar/${itemData.sha256}" target="_blank">${itemData.sha256}</a></span></div>
            `;
            imageModal.classList.remove('hidden');
        }
    });

    imageModal.addEventListener('click', (e) => {
        if (e.target === imageModal) {
            imageModal.classList.add('hidden');
        }
    });

    const pageSizeSelector = document.getElementById('pageSizeSelector');
    const options = [
        ...constants.PAGE_SIZE_OPTIONS,
        {value: 'infinite', text: 'Бесконечно'},
        {value: 'all', text: 'Показать все'}
    ].map(opt => typeof opt === 'object'
        ? `<option value="${opt.value}">${opt.text}</option>`
        : `<option value="${opt}">${opt}</option>`
    ).join('');

    pageSizeSelector.innerHTML = `<span>На странице:</span><select id="pageSizeSelect">${options}</select>`;

    const pageSizeSelect = document.getElementById('pageSizeSelect');
    pageSizeSelect.value = pageSize;
    pageSizeSelect.addEventListener('change', (e) => {
        pageSize = e.target.value;
        localStorage.setItem('galleryPageSize', pageSize);
        const isPaginated = pageSize !== 'infinite' && pageSize !== 'all';
        paginationControlsEl.style.display = isPaginated ? 'flex' : 'none';
        toggleBottomLoading(false);
        resetGallery();
        void loadAndRenderGallery();
    });

    const isPaginated = pageSize !== 'infinite' && pageSize !== 'all';
    paginationControlsEl.style.display = isPaginated ? 'flex' : 'none';

    void loadAndRenderGallery();
}

/**
 * Sets up the IntersectionObserver for lazy loading images.
 */
function setupLazyLoader() {
    lazyLoadObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    }, {root: galleryListEl, rootMargin: '0px 0px 300px 0px'});
}

/**
 * Sets up the scroll listener for infinite scrolling.
 */
function setupInfiniteScroll() {
    const handleScroll = debounce(async () => {
        if (pageSize !== 'infinite' || isLoading || !hasMorePages) {
            return;
        }

        const {scrollTop, scrollHeight, clientHeight} = galleryListEl;
        if (scrollHeight - scrollTop - clientHeight < clientHeight) {
            log('GALLERY_UI', 'Достигнут порог прокрутки, запуск загрузки следующей страницы...');
            await loadAndRenderGallery();
        }
    }, 100);

    galleryListEl.addEventListener('scroll', handleScroll);
}

/**
 * Updates scroll-to-top/bottom buttons visibility.
 */
function updateScrollButtons() {
    const {scrollTop, scrollHeight, clientHeight} = galleryListEl;
    const threshold = 100;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - threshold;

    scrollUpBtn.classList.toggle('visible', scrollTop > threshold);
    if (pageSize === 'infinite') {
        scrollDownBtn.classList.toggle('visible', hasMorePages || !isAtBottom);
    } else {
        scrollDownBtn.classList.toggle('visible', !isAtBottom);
    }
}


/**
 * Sets up scroll-to-top/bottom buttons.
 */
function setupScrollButtons() {
    galleryListEl.addEventListener('scroll', updateScrollButtons);

    scrollUpBtn.addEventListener('click', () => {
        galleryListEl.scrollTo({top: 0, behavior: 'smooth'});
    });

    scrollDownBtn.addEventListener('click', () => {
        galleryListEl.scrollTo({top: galleryListEl.scrollHeight, behavior: 'smooth'});
    });
}

/**
 * Sets up sorting controls on table headers.
 */
function setupSorting() {
    document.querySelectorAll('.gallery-header .sortable').forEach(header => {
        header.addEventListener('click', () => {
            const field = header.dataset.sort;
            if (currentSort.field === field) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.direction = 'asc';
            }
            updateSortHeaders();
            resetGallery();
            void loadAndRenderGallery();
        });
    });
    updateSortHeaders(); // initial state
}

/**
 * Updates the visual indicators on sortable headers.
 */
function updateSortHeaders() {
    document.querySelectorAll('.gallery-header .sortable').forEach(header => {
        const field = header.dataset.sort;
        header.classList.remove('asc', 'desc');
        if (currentSort.field === field) {
            header.classList.add(currentSort.direction);
        }
    });
}

/**
 * Sets up filter input controls, including clear buttons.
 */
function setupFilterControls() {
    const debouncedLoad = debounce(() => {
        resetGallery();
        void loadAndRenderGallery();
    }, 300);

    document.querySelectorAll('.filter-input-wrapper').forEach(wrapper => {
        const input = wrapper.querySelector('input');
        const clearBtn = wrapper.querySelector('.clear-filter-btn');

        input.addEventListener('input', () => {
            currentFilters[input.dataset.filter] = input.value;
            clearBtn.classList.toggle('hidden', !input.value);
            debouncedLoad();
        });

        clearBtn.addEventListener('click', () => {
            input.value = '';
            currentFilters[input.dataset.filter] = '';
            clearBtn.classList.add('hidden');
            input.focus();
            debouncedLoad();
        });
    });
}


export {initGalleryControls, loadAndRenderGallery};