
    document.addEventListener('DOMContentLoaded', () => {
        const table = document.querySelector('.table');
        if (!table) return;

        const headers = table.querySelectorAll('th[data-sort-key]');
        const tbody = table.querySelector('tbody');

        // Helper function to get the clean text value from a cell
        const getCellValue = (tr, idx) => {
            // Check if the cell contains a link, if so, use its text
            const link = tr.children[idx].querySelector('a');
            return link ? link.textContent.trim() : tr.children[idx].textContent.trim();
        };

        // The core sorting function
        const sorter = (idx, asc) => (a, b) => {
            const valA = getCellValue(asc ? a : b, idx);
            const valB = getCellValue(asc ? b : a, idx);

            // Tries to parse as a number for numerical sorting (e.g., ID column)
            const numA = parseFloat(valA.replace(/[^0-9.]/g, ''));
            const numB = parseFloat(valB.replace(/[^0-9.]/g, ''));

            const isNumeric = !isNaN(numA) && isFinite(numA) && !isNaN(numB) && isFinite(numB);

            if (isNumeric) {
                return numA - numB;
            } else {
                // Otherwise, sort alphabetically/lexicographically
                return valA.localeCompare(valB);
            }
        };

        // Main event listener loop for all sortable headers
        headers.forEach((header, index) => {
            // Initialize sort order. ID is set to 'desc' by default in HTML for visual indicator.
            if (!header.dataset.order) {
                header.dataset.order = 'desc';
            }

            header.addEventListener('click', () => {
                const currentOrder = header.dataset.order === 'desc' ? 'asc' : 'desc';
                const asc = currentOrder === 'asc';

                // 1. Sort the rows
                Array.from(tbody.querySelectorAll('tr'))
                    .sort(sorter(index, asc))
                    .forEach(tr => tbody.appendChild(tr));

                // 2. Update visual indicators (CSS classes)

                // Remove 'sorted' class from all headers and reset icons
                headers.forEach(h => {
                    h.classList.remove('sorted');
                    const icon = h.querySelector('.sort-icon');
                    if (icon) {
                        icon.classList.remove('asc', 'desc');
                    }
                });

                // Add 'sorted' class to the clicked header
                header.classList.add('sorted');
                header.dataset.order = currentOrder;

                // Update the sort icon for the current header
                const icon = header.querySelector('.sort-icon');
                if (icon) {
                    icon.classList.add(currentOrder);
                }
            });
        });
    });
