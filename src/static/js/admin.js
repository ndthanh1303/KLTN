/* Menu trên điện thoại; sidebar máy tính được cố định bằng CSS. */
(function () {
    "use strict";
    const logo = document.getElementById("admin-logo");
    const fallback = document.getElementById("admin-logo-fallback");
    if (logo && fallback) {
        function showLogoFallback() { logo.hidden = true; fallback.hidden = false; }
        logo.addEventListener("error", showLogoFallback);
        if (logo.complete && logo.naturalWidth === 0) showLogoFallback();
    }

    const sidebar = document.getElementById("admin-sidebar");
    const toggle = document.getElementById("admin-menu-toggle");
    const close = document.getElementById("admin-sidebar-close");
    const backdrop = document.getElementById("admin-sidebar-backdrop");
    const workspace = document.getElementById("admin-workspace");
    if (!sidebar || !toggle || !close || !backdrop || !workspace) return;
    const mobile = window.matchMedia("(max-width: 960px)");
    let opened = false;
    let previousFocus = null;
    document.body.classList.add("has-admin-js");
    toggle.hidden = false;
    close.hidden = false;

    function setOpen(value, restoreFocus) {
        opened = Boolean(value && mobile.matches);
        document.body.classList.toggle("admin-sidebar-open", opened);
        toggle.setAttribute("aria-expanded", String(opened));
        backdrop.hidden = !opened;
        sidebar.inert = mobile.matches && !opened;
        workspace.inert = opened;
        if (opened) {
            sidebar.setAttribute("role", "dialog");
            sidebar.setAttribute("aria-modal", "true");
            close.focus();
        } else {
            sidebar.removeAttribute("role");
            sidebar.removeAttribute("aria-modal");
            if (restoreFocus && previousFocus) previousFocus.focus();
        }
    }
    toggle.addEventListener("click", function () {
        previousFocus = document.activeElement;
        setOpen(!opened, true);
    });
    close.addEventListener("click", function () { setOpen(false, true); });
    backdrop.addEventListener("click", function () { setOpen(false, true); });
    sidebar.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () { if (opened) setOpen(false, true); });
    });
    // Giữ bàn phím trong menu đang mở và hỗ trợ phím Escape.
    document.addEventListener("keydown", function (event) {
        if (!opened) return;
        if (event.key === "Escape") { event.preventDefault(); setOpen(false, true); }
        if (event.key !== "Tab") return;
        const focusable = Array.from(sidebar.querySelectorAll('a[href], button:not([disabled])'))
            .filter(function (element) { return !element.hidden && element.getClientRects().length > 0; });
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first) return;
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    mobile.addEventListener("change", function () { setOpen(false, false); });
    setOpen(false, false);
}());
