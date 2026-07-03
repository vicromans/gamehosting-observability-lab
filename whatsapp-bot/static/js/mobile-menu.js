document.addEventListener("DOMContentLoaded", function () {
    const button = document.getElementById("mobileMenuToggle");
    const sidebar = document.querySelector(".sidebar");

    if (!button || !sidebar) {
        return;
    }

    button.addEventListener("click", function () {
        sidebar.classList.toggle("mobile-open");
    });

    document.querySelectorAll(".menu a").forEach(function (link) {
        link.addEventListener("click", function () {
            sidebar.classList.remove("mobile-open");
        });
    });
});
