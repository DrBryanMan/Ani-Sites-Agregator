// Налаштування пагінації
const ITEMS_PER_PAGE = 6;

// Об'єкт для зберігання завантажених даних
const animeData = {};
let noincludeData = [];
let filteredData = {};

// Змінна для відстеження поточного режиму перегляду
let viewMode = 'grid'; // 'grid' або 'list'

// Об'єкт для збереження стану пагінації для кожної вкладки
const paginationState = {};

// Функція для завантаження даних з JSON-файлу
async function loadDataFromJson(filename) {
    try {
        const response = await fetch(`data/${filename}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Помилка завантаження даних з ${filename}:`, error);
        return [];
    }
}

// Функція для видалення аніме з каталогу
async function deleteAnimeItem(sectionId, animeIndex, jsonFilename) {
    try {
        const currentData = animeData[sectionId];
        if (!currentData || !currentData[animeIndex]) {
            console.error('Елемент для видалення не знайдено');
            return false;
        }

        const deletedItem = currentData.splice(animeIndex, 1)[0];

        const response = await fetch('/update_json', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: jsonFilename, data: currentData })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const result = await response.json();
        if (result.success) {
            const currentPage = paginationState[sectionId]?.currentPage || 1;
            const searchTerm = paginationState[sectionId]?.searchTerm || '';
            const filteredList = searchTerm 
                ? currentData.filter(anime => anime.title.toLowerCase().includes(searchTerm.toLowerCase()))
                : currentData;
            const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
            const pageToRender = currentPage > totalPages ? totalPages || 1 : currentPage;
            renderAnimeCards(sectionId, jsonFilename, pageToRender, searchTerm);
            return true;
        } else {
            throw new Error(result.message || 'Помилка оновлення даних');
        }
    } catch (error) {
        console.error('Помилка видалення елементу:', error);
        alert(`Помилка видалення: ${error.message}`);
        return false;
    }
}

function copyLinkToClipboard(link) {
    // Перевіряємо підтримку нового API
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(link)
            .then(() => {
                showToast('Посилання скопійовано');
            })
            .catch(err => {
                console.error('Помилка при копіюванні в буфер: ', err);
                fallbackCopy(link);
            });
    } else {
        fallbackCopy(link);
    }
}

function fallbackCopy(text) {
    // Створюємо тимчасовий елемент input
    const textArea = document.createElement('textarea');
    textArea.value = text;
    
    // Робимо елемент невидимим
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    
    // Фокусуємось на елементі і вибираємо текст
    textArea.focus();
    textArea.select();
    
    let successful = false;
    try {
        // Виконуємо команду копіювання
        successful = document.execCommand('copy');
    } catch (err) {
        console.error('Помилка при використанні execCommand: ', err);
    }
    
    // Видаляємо тимчасовий елемент
    document.body.removeChild(textArea);
    
    if (successful) {
        showToast('Посилання скопійовано');
    } else {
        showToast('Не вдалося скопіювати посилання. Спробуйте вручну.', 'error');
    }
}

// Функція для показу повідомлення користувачу
function showToast(message, type = 'success') {
    // Перевіряємо, чи існує контейнер для повідомлень
    let toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.position = 'fixed';
        toastContainer.style.bottom = '20px';
        toastContainer.style.right = '20px';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Створюємо нове повідомлення
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = message;
    
    // Стилі для повідомлення
    toast.style.padding = '10px 15px';
    toast.style.margin = '5px 0';
    toast.style.borderRadius = '4px';
    toast.style.backgroundColor = type === 'success' ? '#4CAF50' : '#F44336';
    toast.style.color = 'white';
    toast.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
    toast.style.transition = 'opacity 0.3s ease-in-out';
    toast.style.opacity = '0';
    
    // Додаємо до контейнера
    toastContainer.appendChild(toast);
    
    // Показуємо повідомлення з анімацією
    setTimeout(() => {
        toast.style.opacity = '1';
    }, 10);
    
    // Видаляємо повідомлення через певний час
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    }, 3000);
}

function createSearchBar() {
    const searchContainer = document.createElement('div');
    searchContainer.className = 'search-container';
    searchContainer.innerHTML = `
        <div class="search-wrapper">
            <input type="text" class="form-control search-input" placeholder="Пошук аніме за назвою..." aria-label="Пошук аніме">
            <button class="clear-search-btn" type="button" aria-label="Очистити поле пошуку">
                <i class="bi bi-x-lg"></i>
            </button>
        </div>
    `;
    return searchContainer;
}

async function renderAnimeCards(sectionId, jsonFilename, page = 1, searchTerm = '') {
    const sectionElement = document.getElementById(sectionId);
    const catalogElement = document.getElementById(`${sectionId}-catalog`);

    catalogElement.innerHTML = '<div class="loading">Завантаження...</div>';

    // Ініціалізація стану пагінації для секції, якщо його ще немає
    if (!paginationState[sectionId]) {
        paginationState[sectionId] = { 
            currentPage: 1,    // Загальна сторінка без пошуку
            searchTerm: '',    // Поточний пошуковий термін
            searchPage: 1      // Сторінка для результатів пошуку
        };
    }

    // Якщо пошуковий запит змінився
    if (paginationState[sectionId].searchTerm !== searchTerm) {
        if (searchTerm === '') {
            // Якщо пошук очищено - відновлюємо загальну сторінку
            page = paginationState[sectionId].currentPage;
        } else if (paginationState[sectionId].searchTerm === '') {
            // Якщо ввели новий пошуковий запит - зберігаємо поточну загальну сторінку
            paginationState[sectionId].currentPage = page;
            // Скидаємо сторінку пошуку до 1 при новому пошуку
            page = 1;
        }
        // Оновлюємо пошуковий термін у стані
        paginationState[sectionId].searchTerm = searchTerm;
    }

    // Оновлюємо відповідну сторінку в залежності від наявності пошукового запиту
    if (searchTerm === '') {
        paginationState[sectionId].currentPage = page;
    } else {
        paginationState[sectionId].searchPage = page;
    }

    // Збереження стану в localStorage
    localStorage.setItem(`pagination_${sectionId}`, JSON.stringify(paginationState[sectionId]));

    let toolbarContainer = sectionElement.querySelector('.toolbar-container');

    if (!toolbarContainer) {
        toolbarContainer = document.createElement('div');
        toolbarContainer.className = 'toolbar-container';

        const searchBar = createSearchBar();
        toolbarContainer.appendChild(searchBar);

        const viewToggleContainer = document.createElement('div');
        viewToggleContainer.className = 'view-toggle-container';
        viewToggleContainer.innerHTML = `
            <button class="view-toggle ${viewMode === 'grid' ? 'active' : ''}" data-view="grid">
                <i class="bi bi-grid"></i>
            </button>
            <button class="view-toggle ${viewMode === 'list' ? 'active' : ''}" data-view="list">
                <i class="bi bi-list-ul"></i>
            </button>
        `;
        toolbarContainer.appendChild(viewToggleContainer);

        viewToggleContainer.querySelectorAll('.view-toggle').forEach(button => {
            button.addEventListener('click', function () {
                viewMode = this.dataset.view;
                viewToggleContainer.querySelectorAll('.view-toggle').forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                const searchInput = toolbarContainer.querySelector('.search-input');
                const currentPage = searchInput.value.trim() !== '' ? 
                    paginationState[sectionId]?.searchPage || 1 : 
                    paginationState[sectionId]?.currentPage || 1;
                
                renderAnimeCards(sectionId, jsonFilename, currentPage, searchInput.value);
            });
        });

        const searchInput = searchBar.querySelector('.search-input');
        const clearBtn = searchBar.querySelector('.clear-search-btn');

        searchInput.addEventListener('input', () => {
            const term = searchInput.value.toLowerCase();
            // При введенні пошуку починаємо з першої сторінки результатів або використовуємо збережену
            const pageToUse = term !== '' && paginationState[sectionId].searchTerm === '' ? 
                1 : // Якщо це перший пошук - починаємо з першої сторінки
                term !== '' ? 
                    paginationState[sectionId]?.searchPage || 1 : // Якщо продовжуємо пошук - збережена сторінка пошуку
                    paginationState[sectionId]?.currentPage || 1;  // Якщо очистили пошук - основна сторінка
            
            renderAnimeCards(sectionId, jsonFilename, pageToUse, term);
        });

        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            searchInput.focus();
            // При очищенні пошуку відновлюємо загальну сторінку
            const currentPage = paginationState[sectionId]?.currentPage || 1;
            renderAnimeCards(sectionId, jsonFilename, currentPage, '');
        });

        sectionElement.insertBefore(toolbarContainer, catalogElement);
    } else {
        const searchInput = toolbarContainer.querySelector('.search-input');
        if (searchInput && searchInput.value !== searchTerm) {
            searchInput.value = searchTerm;
        }
    }

    if (!animeData[sectionId]) {
        animeData[sectionId] = await loadDataFromJson(jsonFilename);
    }

    const animeList = animeData[sectionId];
    if (!animeList || animeList.length === 0) {
        catalogElement.innerHTML = '<div class="no-results">Немає даних для відображення</div>';
        return;
    }

    let filteredList = animeList;
    if (searchTerm) {
        filteredList = filteredList.filter(anime => anime.title.toLowerCase().includes(searchTerm.toLowerCase()));
    }
    filteredData[sectionId] = filteredList;

    if (filteredList.length === 0) {
        catalogElement.innerHTML = '<div class="no-results">За вашим запитом нічого не знайдено</div>';
        const paginationElement = document.getElementById(`${sectionId}-pagination`);
        if (paginationElement) paginationElement.innerHTML = '';
        return;
    }

    const totalPages = Math.ceil(filteredList.length / ITEMS_PER_PAGE);
    if (page > totalPages) {
        page = totalPages;
    }

    // Оновлюємо відповідну сторінку в залежності від наявності пошукового запиту
    if (searchTerm === '') {
        paginationState[sectionId].currentPage = page;
    } else {
        paginationState[sectionId].searchPage = page;
    }

    // Оновлюємо в localStorage після перевірки totalPages
    localStorage.setItem(`pagination_${sectionId}`, JSON.stringify(paginationState[sectionId]));

    const startIndex = (page - 1) * ITEMS_PER_PAGE;
    const paginatedItems = filteredList.slice(startIndex, startIndex + ITEMS_PER_PAGE);

    catalogElement.className = `catalog ${viewMode === 'list' ? 'list-view' : 'grid-view'}`;
    catalogElement.innerHTML = '';

    paginatedItems.forEach((anime, index) => {
        const animeIndex = animeList.indexOf(anime);
        const card = document.createElement('div');

        if (viewMode === 'grid') {
            card.className = 'anime-card';
            card.innerHTML = `
                <img src="${anime.poster}" alt="${anime.title}" class="anime-poster" referrerpolicy="no-referrer">
                <div class="anime-info">
                    <h3 class="anime-title" title="${anime.title}">${anime.title}</h3>
                    <div class="anime-actions">
                        <a href="${anime.link}" class="anime-action-btn view-btn" target="_blank" title="Переглянути">
                            <i class="bi bi-play-fill"></i>
                        </a>
                        <button class="anime-action-btn copy-btn" title="Копіювати посилання">
                            <i class="bi bi-clipboard"></i>
                        </button>
                    </div>
                </div>
            `;
        } else {
            card.className = 'anime-list-item';
            card.innerHTML = `
                <div class="anime-list-content">
                    <img src="${anime.poster}" alt="${anime.title}" class="anime-list-poster" referrerpolicy="no-referrer">
                    <h3 class="anime-list-title" title="${anime.title}">${anime.title}</h3>
                </div>
                <div class="anime-list-actions">
                    <a href="${anime.link}" class="anime-action-btn view-btn" target="_blank" title="Переглянути">
                        <i class="bi bi-play-fill"></i>
                    </a>
                    <button class="anime-action-btn copy-btn" title="Копіювати посилання">
                        <i class="bi bi-clipboard"></i>
                    </button>
                </div>
            `;
        }

        card.querySelector('.copy-btn').addEventListener('click', () => copyLinkToClipboard(anime.link));

        catalogElement.appendChild(card);
    });

    renderPagination(sectionId, page, totalPages, searchTerm);
}

function renderPagination(sectionId, currentPage, totalPages, searchTerm = '') {
    const paginationElement = document.getElementById(`${sectionId}-pagination`);
    paginationElement.innerHTML = '';

    if (totalPages <= 1) return;

    if (currentPage > 1) {
        paginationElement.appendChild(createPaginationButton(sectionId, 1, '<i class="bi bi-chevron-double-left"></i>', false, searchTerm));
        paginationElement.appendChild(createPaginationButton(sectionId, currentPage - 1, '<i class="bi bi-chevron-left"></i>', false, searchTerm));
    }

    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        paginationElement.appendChild(createPaginationButton(sectionId, i, i.toString(), i === currentPage, searchTerm));
    }

    if (currentPage < totalPages) {
        paginationElement.appendChild(createPaginationButton(sectionId, currentPage + 1, '<i class="bi bi-chevron-right"></i>', false, searchTerm));
        paginationElement.appendChild(createPaginationButton(sectionId, totalPages, '<i class="bi bi-chevron-double-right"></i>', false, searchTerm));
    }
}

function createPaginationButton(sectionId, page, text, isActive = false, searchTerm = '') {
    const li = document.createElement('li');
    li.className = 'page-item';

    const a = document.createElement('a');
    a.href = '#';
    a.className = `page-link ${isActive ? 'active' : ''}`;
    a.innerHTML = text;
    a.addEventListener('click', function(e) {
        e.preventDefault();
        const activeNavLink = document.querySelector(`.nav-link[data-section="${sectionId}"]`);
        const jsonFilename = activeNavLink.dataset.json;
        renderAnimeCards(sectionId, jsonFilename, page, searchTerm);
    });

    li.appendChild(a);
    return li;
}

document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const sectionId = this.dataset.section;
        const jsonFilename = this.dataset.json;

        localStorage.setItem('lastSection', sectionId);

        document.querySelectorAll('.nav-link').forEach(navLink => navLink.classList.remove('active'));
        this.classList.add('active');

        document.querySelectorAll('.section').forEach(section => section.classList.remove('active'));
        document.getElementById(sectionId).classList.add('active');

        const localState = localStorage.getItem(`pagination_${sectionId}`);
        const savedState = localState ? JSON.parse(localState) : { currentPage: 1, searchTerm: '' };
        paginationState[sectionId] = savedState;

        renderAnimeCards(sectionId, jsonFilename, savedState.currentPage, savedState.searchTerm);
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const lastSection = localStorage.getItem('lastSection');
    const firstNavLink = lastSection
        ? document.querySelector(`.nav-link[data-section="${lastSection}"]`)
        : document.querySelector('.nav-link');

    const sectionId = firstNavLink.dataset.section;
    const jsonFilename = firstNavLink.dataset.json;

    const localState = localStorage.getItem(`pagination_${sectionId}`);
    paginationState[sectionId] = localState ? JSON.parse(localState) : { 
        currentPage: 1, 
        searchTerm: '',
        searchPage: 1
    };

    document.querySelectorAll('.nav-link').forEach(navLink => navLink.classList.remove('active'));
    document.querySelectorAll('.section').forEach(section => section.classList.remove('active'));

    firstNavLink.classList.add('active');
    document.getElementById(sectionId).classList.add('active');

    // Визначаємо, яку сторінку використовувати в залежності від стану пошуку
    const pageToUse = paginationState[sectionId].searchTerm ? 
                      paginationState[sectionId].searchPage : 
                      paginationState[sectionId].currentPage;
    
    renderAnimeCards(sectionId, jsonFilename, pageToUse, paginationState[sectionId].searchTerm);
        
    // Встановлюємо збережений пошуковий запит в поле вводу
    setTimeout(() => {
        const searchInput = document.querySelector(`#${sectionId} .search-input`);
        if (searchInput && paginationState[sectionId].searchTerm) {
            searchInput.value = paginationState[sectionId].searchTerm;
        }
    }, 100);
});
