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