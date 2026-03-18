document.addEventListener('DOMContentLoaded', function () {
    const navbarToggle = document.querySelector('[data-navbar-toggle]');
    const navbarPanel = document.querySelector('[data-navbar-panel]');
    const navbar = document.querySelector('[data-habita-navbar]');

    if (navbarToggle && navbarPanel) {
        navbarToggle.addEventListener('click', function () {
            navbar.classList.toggle('is-open');
            navbarPanel.classList.toggle('is-open');
        });
    }

    const userMenu = document.querySelector('[data-user-menu]');
    const userTrigger = document.querySelector('[data-user-menu-trigger]');
    const userDropdown = document.querySelector('[data-user-menu-dropdown]');

    if (userMenu && userTrigger && userDropdown) {
        userTrigger.addEventListener('click', function (event) {
            event.stopPropagation();
            userMenu.classList.toggle('is-open');
        });

        document.addEventListener('click', function (event) {
            if (!userMenu.contains(event.target)) {
                userMenu.classList.remove('is-open');
            }
        });
    }

    const filtersToggle = document.querySelector('[data-filters-toggle]');
    const filtersPanel = document.querySelector('[data-filters-panel]');

    if (filtersToggle && filtersPanel) {
        filtersToggle.addEventListener('click', function () {
            filtersPanel.classList.toggle('is-open');
        });
    }

    const viewButtons = document.querySelectorAll('[data-view-mode]');
    const viewInput = document.querySelector('[data-view-input]');
    const propertiesGrid = document.querySelector('[data-properties-grid]');

    if (viewButtons.length && viewInput && propertiesGrid) {
        viewButtons.forEach(function (button) {
            button.addEventListener('click', function () {
                const mode = button.getAttribute('data-view-mode');
                viewInput.value = mode;

                viewButtons.forEach(function (item) {
                    item.classList.remove('is-active');
                });
                button.classList.add('is-active');

                if (mode === 'list') {
                    propertiesGrid.classList.add('properties-grid--list');
                    propertiesGrid.classList.remove('properties-grid--catalog');
                } else {
                    propertiesGrid.classList.remove('properties-grid--list');
                    propertiesGrid.classList.add('properties-grid--catalog');
                }
            });
        });
    }

    const accountOptions = document.querySelectorAll('.account-type-option');
    accountOptions.forEach(function (option) {
        const input = option.querySelector('input[type="radio"]');
        if (!input) return;

        input.addEventListener('change', function () {
            accountOptions.forEach(function (item) {
                item.classList.remove('is-active');
            });
            option.classList.add('is-active');
        });
    });
});
