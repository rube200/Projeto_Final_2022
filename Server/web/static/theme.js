(function () {
    "use strict"; // Start of use strict

    const sidebar = document.querySelector('.sidebar');
    const sidebarToggles = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
    if (sidebar) {
        for (const toggle of sidebarToggles) {
            // Toggle the side navigation
            toggle.addEventListener('click', function () {
                document.body.classList.toggle('sidebar-toggled');
                sidebar.classList.toggle('toggled');
            });
        }
    }

    const scrollToTop = document.querySelector('.scroll-to-top');
    if (scrollToTop) {
        window.addEventListener('scroll', function () {
            const scrollDistance = window.scrollY;
            if (scrollDistance > 100) {
                scrollToTop.style.display = 'block';
            } else {
                scrollToTop.style.display = 'none';
            }
        });
    }

})(); // End of use strict
