/**
 * Global Search Functionality with Debouncing and Keyboard Navigation
 */
class GlobalSearch {
    constructor() {
        this.searchInput = document.getElementById('globalSearchInput');
        this.searchContainer = document.getElementById('searchContainer');
        this.suggestionsContainer = document.getElementById('searchSuggestions');
        this.searchForm = document.querySelector('.search-form');
        
        this.debounceTimeout = null;
        this.selectedSuggestionIndex = -1;
        this.suggestions = [];
        
        this.init();
    }
    
    init() {
        if (!this.searchInput) return;
        
        // Event Listeners
        this.searchInput.addEventListener('input', (e) => this.handleInput(e));
        this.searchInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.searchInput.addEventListener('focus', () => {
            const query = this.searchInput.value.trim();
            if (query.length >= 2) {
                this.showSuggestions();
            }
        });
        
        this.searchInput.addEventListener('blur', () => {
            setTimeout(() => this.hideSuggestions(), 200);
        });
        
        // Handle form submit
        this.searchForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Close suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.searchContainer.contains(e.target) && 
                !this.suggestionsContainer.contains(e.target)) {
                this.hideSuggestions();
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', () => this.adjustSuggestionsPosition());
    }
    
    adjustSuggestionsPosition() {
        if (!this.suggestionsContainer.classList.contains('show')) return;
        
        // Ensure suggestions stay within viewport
        const sidebarRect = document.querySelector('.sidebar').getBoundingClientRect();
        const suggestionsRect = this.suggestionsContainer.getBoundingClientRect();
        
        if (suggestionsRect.bottom > window.innerHeight) {
            this.suggestionsContainer.style.maxHeight = `${window.innerHeight - sidebarRect.top - 100}px`;
        }
    }
    
    handleInput(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }
        
        // Hide suggestions if query is too short
        if (query.length < 2) {
            this.hideSuggestions();
            return;
        }
        
        // Debounce the search (300ms delay)
        this.debounceTimeout = setTimeout(() => {
            this.fetchSuggestions(query);
        }, 300);
    }
    
    async fetchSuggestions(query) {
        try {
            const response = await fetch(`/search/api/suggestions?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            this.suggestions = data.suggestions || [];
            this.renderSuggestions();
            
        } catch (error) {
            console.error('Error fetching suggestions:', error);
            this.suggestions = [];
            this.renderSuggestions();
        }
    }
    
    renderSuggestions() {
        if (!this.suggestionsContainer) return;
        
        if (this.suggestions.length === 0) {
            const query = this.searchInput.value.trim();
            if (query.length < 2) {
                this.hideSuggestions();
                return;
            }
            
            this.suggestionsContainer.innerHTML = `
                <div class="suggestion-empty">
                    No results found for "${query}"
                </div>
                <div class="view-all-results">
                    <a href="/search?q=${encodeURIComponent(query)}">View all results</a>
                </div>
            `;
            this.showSuggestions();
            return;
        }
        
        let html = '';
        this.suggestions.forEach((suggestion, index) => {
            const highlightedTitle = this.highlightText(suggestion.text, this.searchInput.value.trim());
            const highlightedDesc = this.highlightText(suggestion.description, this.searchInput.value.trim());
            
            html += `
                <div class="suggestion-item ${index === this.selectedSuggestionIndex ? 'selected' : ''}"
                     data-index="${index}"
                     data-url="${suggestion.url}"
                     onmousedown="event.preventDefault(); window.location.href='${suggestion.url}'">
                    <div class="suggestion-title">
                        <span class="suggestion-type">${suggestion.type}</span>
                        <span>${highlightedTitle}</span>
                    </div>
                    <div class="suggestion-description">
                        ${highlightedDesc}
                    </div>
                </div>
            `;
        });
        
        // Add "View all results" link
        const query = this.searchInput.value.trim();
        html += `
            <div class="view-all-results">
                <a href="/search?q=${encodeURIComponent(query)}">View all results for "${query}"</a>
            </div>
        `;
        
        this.suggestionsContainer.innerHTML = html;
        this.showSuggestions();
        this.adjustSuggestionsPosition();
    }
    
    highlightText(text, query) {
        if (!query || !text) return text;
        
        try {
            // Escape special regex characters
            const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${escapedQuery})`, 'gi');
            return text.replace(regex, '<span class="highlight">$1</span>');
        } catch (e) {
            console.error('Highlight error:', e);
            return text;
        }
    }
    
    handleKeyDown(e) {
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navigateSuggestions(1);
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.navigateSuggestions(-1);
                break;
                
            case 'Enter':
                if (this.selectedSuggestionIndex >= 0) {
                    e.preventDefault();
                    this.selectSuggestion();
                }
                break;
                
            case 'Escape':
                this.hideSuggestions();
                this.searchInput.blur();
                break;
                
            case 'Tab':
                this.hideSuggestions();
                break;
        }
    }
    
    navigateSuggestions(direction) {
        if (!this.suggestions.length) return;
        
        this.selectedSuggestionIndex += direction;
        
        // Wrap around
        if (this.selectedSuggestionIndex < 0) {
            this.selectedSuggestionIndex = this.suggestions.length - 1;
        } else if (this.selectedSuggestionIndex >= this.suggestions.length) {
            this.selectedSuggestionIndex = 0;
        }
        
        this.renderSuggestions();
        
        // Scroll into view
        const selectedElement = this.suggestionsContainer.querySelector(`[data-index="${this.selectedSuggestionIndex}"]`);
        if (selectedElement) {
            selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    }
    
    selectSuggestion() {
        if (this.selectedSuggestionIndex >= 0 && this.suggestions[this.selectedSuggestionIndex]) {
            const suggestion = this.suggestions[this.selectedSuggestionIndex];
            window.location.href = suggestion.url;
        }
    }
    
    handleSubmit(e) {
        // If we have a selected suggestion, prevent default form submit
        if (this.selectedSuggestionIndex >= 0) {
            e.preventDefault();
            this.selectSuggestion();
            return;
        }
        
        const query = this.searchInput.value.trim();
        if (query.length < 2) {
            e.preventDefault();
            this.searchInput.focus();
            return;
        }
        
        // Let form submit normally to /search?q=...
        // Ensure the action URL is correct
        this.searchForm.action = `/search?q=${encodeURIComponent(query)}`;
    }
    
    showSuggestions() {
        if (this.suggestionsContainer && this.searchInput.value.trim().length >= 2) {
            this.suggestionsContainer.classList.add('show');
            this.adjustSuggestionsPosition();
        }
    }
    
    hideSuggestions() {
        if (this.suggestionsContainer) {
            this.suggestionsContainer.classList.remove('show');
            this.selectedSuggestionIndex = -1;
        }
    }
}

// Initialize search when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const search = new GlobalSearch();
    
    // If there's a search query in the input, fetch suggestions on page load
    const searchInput = document.getElementById('globalSearchInput');
    if (searchInput && searchInput.value.trim().length >= 2) {
        search.fetchSuggestions(searchInput.value.trim());
    }
});