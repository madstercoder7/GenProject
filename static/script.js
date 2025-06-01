function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('active');
}

document.addEventListener('click', function(event) {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.querySelector('.toggle-btn');

    if (window.innerWidth <= 768 && !sidebar.contains(event.target) && !toggleBtn.contains(event.target)) {
        sidebar.classList.remove('active');
    }
});

document.addEventListener('click', function(event) {
    if (event.target.closest('.delete-idea')) {
        const button = event.target.closest('.delete-idea');
        const ideaId = button.getAttribute('data-idea-id');
        
        if (confirm('Are you sure you want to delete this project idea?')) {
            fetch(`/delete_idea/${ideaId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => {
                const toast = new bootstrap.Toast(document.getElementById('deleteToast'));
                const toastBody = document.querySelector('#deleteToast .toast-body');
                if (response.ok) {
                    button.closest('.mb-3').remove();
                    toastBody.textContent = 'Project idea deleted successfully!';
                    toastBody.classList.remove('text-danger');
                    toastBody.classList.add('text-success');
                    toast.show();
                } else {
                    toastBody.textContent = 'Failed to delete project idea.';
                    toastBody.classList.remove('text-success');
                    toastBody.classList.add('text-danger');
                    toast.show();
                }
            })
            .catch(error => {
                const toast = new bootstrap.Toast(document.getElementById('deleteToast'));
                const toastBody = document.querySelector('#deleteToast .toast-body');
                toastBody.textContent = 'An error occurred while deleting the idea.';
                toastBody.classList.add('text-danger');
                toast.show();
                console.error('Error deleting idea:', error);
            });
        }
    }
});