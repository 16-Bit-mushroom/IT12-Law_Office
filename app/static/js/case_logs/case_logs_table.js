
    document.addEventListener('DOMContentLoaded', () => {
        const table = document.querySelector('.table');
        if (!table) return;

        // Select only headers that have the data-sort-key attribute
        const headers = table.querySelectorAll('th[data-sort-key]');
        const tbody = table.querySelector('tbody');

        // Helper function to get the clean text value from a cell
        const getCellValue = (tr, idx) => {
            // Check if the cell contains a link, if so, use its text
            const link = tr.children[idx].querySelector('a');
            // Check for status tag text if no link is found (e.g., Status column)
            const tag = tr.children[idx].querySelector('.status-tag');

            if (link) {
                return link.textContent.trim();
            } else if (tag) {
                return tag.textContent.trim();
            } else {
                return tr.children[idx].textContent.trim();
            }
        };

        // The core sorting function
        const sorter = (idx, asc) => (a, b) => {
            const valA = getCellValue(asc ? a : b, idx);
            const valB = getCellValue(asc ? b : a, idx);

            // Tries to parse as a number for numerical sorting (e.g., ID, Cases, Documents columns)
            // Use a strict regex to check if it's purely numerical content before attempting float parsing
            // This prevents 'Active' from parsing to NaN and falling through.
            const cleanValA = valA.replace(/[^0-9.]/g, '');
            const cleanValB = valB.replace(/[^0-9.]/g, '');

            const numA = parseFloat(cleanValA);
            const numB = parseFloat(cleanValB);

            // If both cleaned strings successfully parse to finite numbers, perform numeric sort
            const isNumeric = cleanValA !== "" && !isNaN(numA) && isFinite(numA) &&
                cleanValB !== "" && !isNaN(numB) && isFinite(numB);

            if (isNumeric) {
                return numA - numB;
            } else {
                // Otherwise, sort alphabetically/lexicographically using localeCompare for correctness
                return valA.localeCompare(valB);
            }
        };

        // Main event listener loop for all sortable headers
        headers.forEach((header, index) => {
            // Initialize sort order. ID is set to 'asc' by default in HTML for visual indicator.
            if (!header.dataset.order) {
                header.dataset.order = 'desc';
            }

            header.addEventListener('click', () => {
                // Determine the next sort order
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
                    h.dataset.order = 'desc'; // Reset data-order for non-clicked headers
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

            // Trigger an initial sort on the default column (Client ID in this case)
            if (header.classList.contains('sorted')) {
                // Manually trigger the sort function once to ensure the data reflects the initial visual state
                const initialAsc = header.dataset.order === 'asc';
                Array.from(tbody.querySelectorAll('tr'))
                    .sort(sorter(index, initialAsc))
                    .forEach(tr => tbody.appendChild(tr));
            }
        });
    });
