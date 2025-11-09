
    document.getElementById('clientForm').addEventListener('submit', function (e) {
        e.preventDefault(); // Prevent default form submission
        const formData = new FormData(this);

        // Example: AJAX POST to Flask route
        fetch('/clients/add', {
            method: 'POST',
            body: formData
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // Close modal
                    const modalEl = document.getElementById('clientFormModal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    modal.hide();

                    // Optionally, refresh the table or show a toast
                    alert('Client added successfully!');
                } else {
                    alert('Error: ' + data.error);
                }
            });
    });
