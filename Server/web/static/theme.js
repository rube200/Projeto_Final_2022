(function () {
    "use strict"; // Start of use strict

    const sidebar = document.querySelector('.sidebar');
    const sidebarToggles = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
    let userToggle = false;
    if (sidebar) {
        for (const toggle of sidebarToggles) {
            // Toggle the side navigation
            toggle.addEventListener('click', () => {
                document.body.classList.toggle('sidebar-toggled');
                sidebar.classList.toggle('toggled');
                userToggle = sidebar.classList.contains('toggled');
            });
        }

        window.addEventListener('resize', () => {
            if (window.innerWidth < 629) {
                if (!userToggle) {
                    document.body.classList.add('sidebar-toggled');
                    sidebar.classList.add('toggled');
                }
                return;
            }

            if (userToggle) {
                document.body.classList.add('sidebar-toggled');
                sidebar.classList.add('toggled');

            }
            else {
                document.body.classList.remove('sidebar-toggled');
                sidebar.classList.remove('toggled');
            }
        });
    }

    const scrollToTop = document.querySelector('.scroll-to-top');
    if (scrollToTop) {
        window.addEventListener('scroll', () => {
            const scrollDistance = window.scrollY;
            if (scrollDistance > 100) {
                scrollToTop.style.display = 'block';
            } else {
                scrollToTop.style.display = 'none';
            }
        });
    }

})(); // End of use strict
