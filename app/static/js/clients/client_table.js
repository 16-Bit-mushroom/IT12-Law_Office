// static/js/clients/client_table.js

document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for delete buttons
    document.querySelectorAll('.delete-client').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const clientId = this.getAttribute('data-client-id');
            const clientName = this.getAttribute('data-client-name');
            
            deleteClient(clientId, clientName);
        });
    });

    // Add search functionality
    const searchInput = document.querySelector('.search-bar__input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterClients(this.value.toLowerCase());
        });
    }

    // Add sorting functionality
    document.querySelectorAll('th[data-sort-key]').forEach(th => {
        th.addEventListener('click', function() {
            const sortKey = this.getAttribute('data-sort-key');
            sortTable(sortKey);
        });
    });
});

function deleteClient(clientId, clientName) {
    if (!confirm(`Are you sure you want to move client "${clientName}" to recycle bin? This action can be undone.`)) {
        return;
    }

    showLoading('Moving client to recycle bin...');
    
    fetch(`/clients/${clientId}/delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.error) {
            showToast('Delete failed: ' + data.error, 'error');
        } else {
            showToast(data.message, 'success');
            // Remove the row from the table
            const row = document.querySelector(`.delete-client[data-client-id="${clientId}"]`).closest('tr');
            row.style.opacity = '0.5';
            setTimeout(() => {
                row.remove();
                // Reload the page to update counts and ensure clean state
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }, 500);
        }
    })
    .catch(error => {
        hideLoading();
        showToast('Delete failed: ' + error.message, 'error');
    });
}

function filterClients(searchTerm) {
    const rows = document.querySelectorAll('.client-table tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function sortTable(sortKey) {
    const tbody = document.querySelector('.client-table tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        let aValue, bValue;
        
        switch (sortKey) {
            case 'id':
                aValue = parseInt(a.cells[0].textContent.replace('#', ''));
                bValue = parseInt(b.cells[0].textContent.replace('#', ''));
                return aValue - bValue;
            case 'name':
                aValue = a.cells[1].textContent.toLowerCase();
                bValue = b.cells[1].textContent.toLowerCase();
                break;
            case 'type':
                aValue = a.cells[2].textContent.toLowerCase();
                bValue = b.cells[2].textContent.toLowerCase();
                break;
            case 'email':
                aValue = a.cells[3].textContent.toLowerCase();
                bValue = b.cells[3].textContent.toLowerCase();
                break;
            case 'phone':
                aValue = a.cells[4].textContent.toLowerCase();
                bValue = b.cells[4].textContent.toLowerCase();
                break;
            case 'transactions':
                aValue = parseInt(a.cells[5].textContent);
                bValue = parseInt(b.cells[5].textContent);
                return aValue - bValue;
            default:
                return 0;
        }
        
        return aValue.localeCompare(bValue);
    });
    
    // Clear and re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

// Utility functions
function showLoading(message = 'Loading...') {
    // Implement your loading indicator
    console.log('Loading:', message);
}

function hideLoading() {
    // Implement your loading indicator hide
    console.log('Loading hidden');
}

function showToast(message, type = 'info') {
    // Implement your toast notification
    alert(`${type.toUpperCase()}: ${message}`);
}

function getCSRFToken() {
    // If you use CSRF protection, get the token from meta tag
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}