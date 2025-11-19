// Global state
let currentResults = [];
let searchHistory = [];
let displayedCount = 0;
const INITIAL_DISPLAY = 8;  // Show 8 in collage, with overlay for more

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadSearchHistory();
    loadStats();
    validateAPIKeys();
    setupDragAndDrop();
});

// Load search history from localStorage
function loadSearchHistory() {
    const stored = localStorage.getItem('searchHistory');
    if (stored) {
        searchHistory = JSON.parse(stored);
        renderSearchHistory();
    }
}

// Save search history to localStorage
function saveSearchHistory() {
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
}

// Render search history in sidebar
function renderSearchHistory() {
    const container = document.getElementById('searchHistory');

    if (searchHistory.length === 0) {
        container.innerHTML = '<p class="empty-state">No searches yet</p>';
        return;
    }

    container.innerHTML = searchHistory.map(item => `
        <div class="history-item" onclick="loadHistoryItem('${item.id}')">
            <div class="history-query">${escapeHtml(item.query)}</div>
            <div class="history-meta">
                <span>${item.count} results</span>
                <span>${formatDate(item.timestamp)}</span>
            </div>
        </div>
    `).join('');
}

// Load a history item
function loadHistoryItem(id) {
    const item = searchHistory.find(h => h.id === id);
    if (item) {
        document.getElementById('searchInput').value = item.query;
        document.getElementById('topK').value = item.k;
        performSearch();
    }
}

// Add search to history
function addToHistory(query, k, results) {
    const id = Date.now().toString();
    const historyItem = {
        id,
        query,
        k,
        count: results.length,
        timestamp: new Date().toISOString(),
        results
    };

    // Add to beginning and limit to 20 items
    searchHistory.unshift(historyItem);
    searchHistory = searchHistory.slice(0, 20);

    saveSearchHistory();
    renderSearchHistory();
}

// Clear search history
function clearSearchHistory() {
    if (searchHistory.length === 0) {
        return;
    }

    if (confirm('Are you sure you want to clear all search history? This cannot be undone.')) {
        searchHistory = [];
        saveSearchHistory();
        renderSearchHistory();
    }
}

// Load stats
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        const statsEl = document.getElementById('statsInfo');
        statsEl.innerHTML = `
            <strong>${data.total_images}</strong> images indexed<br>
            <small>${data.index_name}</small>
        `;
    } catch (error) {
        console.error('Failed to load stats:', error);
        document.getElementById('statsInfo').innerHTML = '<span>Stats unavailable</span>';
    }
}

// Validate API keys on load
async function validateAPIKeys() {
    try {
        const response = await fetch('/api/validate');
        if (!response.ok) {
            const data = await response.json();
            showWarning('API Configuration Error', data.errors);
        }
    } catch (error) {
        console.error('API validation failed:', error);
    }
}

// Show warning modal
function showWarning(title, errors) {
    const modal = document.getElementById('warningModal');
    const messageEl = document.getElementById('warningMessage');
    const errorListEl = document.getElementById('errorList');

    messageEl.textContent = 'The following configuration errors were detected:';
    errorListEl.innerHTML = errors.map(err => `<p>${escapeHtml(err)}</p>`).join('');

    modal.style.display = 'flex';
}

// Close modal
function closeModal() {
    document.getElementById('warningModal').style.display = 'none';
}

// Go to settings
function goToSettings() {
    window.location.href = '/settings';
}

// Clear search
function clearSearch() {
    document.getElementById('searchInput').value = '';
    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = '';
    grid.classList.remove('expanded');
    grid.style.gridTemplateRows = '';
    grid.style.maxHeight = '';
    grid.style.overflowY = '';

    // Remove expanded grid style if it exists
    const expandedStyle = document.getElementById('expanded-grid-style');
    if (expandedStyle) {
        expandedStyle.remove();
    }

    document.getElementById('resultsInfo').style.display = 'none';
    document.getElementById('seeMore').style.display = 'none';
    currentResults = [];
    displayedCount = 0;
}

// Handle search keypress
function handleSearchKeypress(event) {
    if (event.key === 'Enter') {
        performSearch();
    }
}

// Perform search
async function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    const topK = parseInt(document.getElementById('topK').value);

    if (!query) {
        alert('Please enter a search query');
        return;
    }

    // Show processing indicator and reset grid
    document.getElementById('processingIndicator').style.display = 'flex';
    document.getElementById('resultsInfo').style.display = 'none';
    document.getElementById('seeMore').style.display = 'none';

    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = '';
    grid.classList.remove('expanded');
    grid.style.gridTemplateRows = '';
    grid.style.maxHeight = '';
    grid.style.overflowY = '';

    // Remove expanded grid style if it exists
    const expandedStyle = document.getElementById('expanded-grid-style');
    if (expandedStyle) {
        expandedStyle.remove();
    }

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: topK,
                alpha: 0.4,
                enhance: true
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Search failed');
        }

        const data = await response.json();
        currentResults = data.results;
        displayedCount = 0;

        // Hide processing
        document.getElementById('processingIndicator').style.display = 'none';

        if (currentResults.length === 0) {
            document.getElementById('resultsInfo').style.display = 'block';
            document.getElementById('resultsTitle').textContent = 'No Results Found';
            document.getElementById('resultsSubtitle').textContent = 'Try a different search query';
            return;
        }

        // Show results info
        document.getElementById('resultsInfo').style.display = 'block';
        document.getElementById('resultsTitle').textContent = `Found ${currentResults.length} Results`;

        let subtitle = `Query: "${query}"`;
        if (data.enhanced_query && data.enhanced_query !== query) {
            subtitle += `<br><small style="color: var(--text-muted);">Enhanced: "${data.enhanced_query}"</small>`;
        }
        document.getElementById('resultsSubtitle').innerHTML = subtitle;

        // Add to history
        addToHistory(query, topK, currentResults);

        // Display initial results
        displayResults(INITIAL_DISPLAY);

        // Reload stats
        loadStats();

    } catch (error) {
        document.getElementById('processingIndicator').style.display = 'none';
        alert('Search failed: ' + error.message);
    }
}

// Display results
function displayResults(count) {
    const grid = document.getElementById('resultsGrid');

    // Clear grid if starting fresh
    if (displayedCount === 0) {
        grid.innerHTML = '';
    }

    const toDisplay = currentResults.slice(displayedCount, displayedCount + count);
    const hasMore = (displayedCount + count) < currentResults.length;

    toDisplay.forEach((result, index) => {
        const item = document.createElement('div');
        item.className = 'result-item';

        // Get image URL - handle both uploaded and indexed images
        const imageUrl = result.path.startsWith('/')
            ? `/api/image/${encodeURIComponent(result.path)}`
            : `/api/image/${result.path}`;

        item.innerHTML = `
            <img src="${imageUrl}" alt="${escapeHtml(result.caption)}" class="result-image" onerror="handleImageError(this)">
            <div class="result-overlay">
                <span class="result-score">Score: ${result.score.toFixed(3)}</span>
                <p class="result-caption">${escapeHtml(result.caption)}</p>
            </div>
        `;

        grid.appendChild(item);
    });

    displayedCount += toDisplay.length;

    // Add "See More" overlay in the grid if there are more results
    if (hasMore && displayedCount === INITIAL_DISPLAY) {
        const seeMoreOverlay = document.createElement('div');
        seeMoreOverlay.className = 'see-more-overlay';
        seeMoreOverlay.onclick = expandAllResults;

        const remaining = currentResults.length - displayedCount;
        seeMoreOverlay.innerHTML = `
            <div class="see-more-content">
                <div class="see-more-count">+${remaining}</div>
                <div class="see-more-text">See More</div>
            </div>
        `;

        grid.appendChild(seeMoreOverlay);
    }

    // Hide the bottom "See More" button (we use overlay instead)
    document.getElementById('seeMore').style.display = 'none';
}

// Expand to show all results
function expandAllResults() {
    const grid = document.getElementById('resultsGrid');

    // Clear the grid
    grid.innerHTML = '';
    displayedCount = 0;

    // Change grid to scrollable layout for all results
    grid.style.gridTemplateRows = 'repeat(auto-fill, 200px)';
    grid.style.maxHeight = 'none';
    grid.style.overflowY = 'auto';
    grid.style.maxHeight = '80vh';

    // Reset nth-child styling for uniform grid
    const style = document.createElement('style');
    style.id = 'expanded-grid-style';
    style.textContent = `
        .results-grid.expanded .result-item:nth-child(n) {
            grid-column: span 1 !important;
            grid-row: span 1 !important;
            opacity: 1 !important;
        }
    `;
    document.head.appendChild(style);
    grid.classList.add('expanded');

    // Display all results
    currentResults.forEach((result, index) => {
        const item = document.createElement('div');
        item.className = 'result-item';

        const imageUrl = result.path.startsWith('/')
            ? `/api/image/${encodeURIComponent(result.path)}`
            : `/api/image/${result.path}`;

        item.innerHTML = `
            <img src="${imageUrl}" alt="${escapeHtml(result.caption)}" class="result-image" onerror="handleImageError(this)">
            <div class="result-overlay">
                <span class="result-score">Score: ${result.score.toFixed(3)}</span>
                <p class="result-caption">${escapeHtml(result.caption)}</p>
            </div>
        `;

        grid.appendChild(item);
    });

    displayedCount = currentResults.length;
}

// Load more results (legacy function, now redirects to expand)
function loadMoreResults() {
    expandAllResults();
}

// Handle image error
function handleImageError(img) {
    img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect fill="%23334155" width="400" height="300"/><text fill="%2394a3b8" font-family="Arial" font-size="18" x="50%" y="50%" text-anchor="middle">Image not found</text></svg>';
}

// Handle file selection
function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        uploadFiles(files);
    }
}

// Setup drag and drop
function setupDragAndDrop() {
    const uploadSection = document.querySelector('.upload-container');

    uploadSection.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadSection.style.background = 'var(--bg-tertiary)';
    });

    uploadSection.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadSection.style.background = '';
    });

    uploadSection.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadSection.style.background = '';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    });
}

// Upload files
async function uploadFiles(files) {
    const statusEl = document.getElementById('uploadStatus');
    statusEl.textContent = `Uploading ${files.length} file(s)...`;
    statusEl.className = 'upload-status';

    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }

        statusEl.textContent = `Successfully uploaded and indexed ${data.inserted} image(s)!`;
        statusEl.className = 'upload-status success';

        if (data.warnings && data.warnings.length > 0) {
            statusEl.textContent += ' (Some files had warnings)';
        }

        // Clear file input
        document.getElementById('fileInput').value = '';

        // Reload stats
        setTimeout(loadStats, 1000);

        // Clear status after 5 seconds
        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = 'upload-status';
        }, 5000);

    } catch (error) {
        statusEl.textContent = `Upload failed: ${error.message}`;
        statusEl.className = 'upload-status error';
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}
