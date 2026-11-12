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

/* Xem trước ảnh tại trình duyệt; gửi tệp cùng biểu mẫu khi lưu. */
(function () {
    "use strict";
    const widget = document.getElementById("admin-image-upload");
    if (!widget) return;
    const input = document.getElementById("admin-image-files");
    const drop = document.getElementById("admin-image-drop");
    const cover = document.getElementById("admin-image-cover");
    const empty = document.getElementById("admin-image-empty");
    const items = document.getElementById("admin-image-items");
    const status = document.getElementById("admin-image-status");
    const indexField = document.getElementById("admin-image-new-cover");
    const urlField = widget.querySelector('[name="hinh_anh"]');
    const form = input.form;
    const maxFiles = Number(widget.dataset.maxFiles);
    const maxFileSize = Number(widget.dataset.maxFileSize);
    const maxTotalSize = Number(widget.dataset.maxTotalSize);
    const multiple = input.multiple;
    let files = [];
    let coverFile = null;
    const previews = new Map();
    let canSyncFiles = false;
    try {
        input.files = new DataTransfer().files;
        canSyncFiles = true;
    } catch (_) { /* Nút chọn tệp gốc vẫn dùng được. */ }

    function setStatus(message, error = false) {
        status.textContent = message;
        status.classList.toggle("admin-upload-error", error);
    }

    function urls() {
        return (multiple ? urlField.value.split(/\r?\n/) : [urlField.value]).map(url => url.trim()).filter(Boolean);
    }

    function previewable(url) {
        if (url.startsWith("/static/") && !url.includes("\\") && !url.split("/").includes("..")) return true;
        try {
            const parsed = new URL(url);
            return parsed.protocol === "https:" && !parsed.username && !parsed.password;
        } catch (_) { return false; }
    }

    function syncFileInput() {
        if (!canSyncFiles) return;
        const selection = new DataTransfer();
        files.forEach(file => selection.items.add(file));
        input.files = selection.files;
    }

    function imageEntries() {
        const saved = urls().map((src, index) => ({src, index})).filter(entry => previewable(entry.src));
        const added = files.map(file => {
            if (!previews.has(file)) previews.set(file, URL.createObjectURL(file));
            return {src: previews.get(file), file};
        });
        return !multiple && added.length ? added : saved.concat(added);
    }

    function action(label, description, onClick, danger = false) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "admin-action-link" + (danger ? " admin-danger-link" : "");
        button.textContent = label;
        button.setAttribute("aria-label", description);
        button.addEventListener("click", onClick);
        return button;
    }

    function render() {
        for (const [file, url] of previews) {
            if (!files.includes(file)) {
                URL.revokeObjectURL(url);
                previews.delete(file);
            }
        }
        const entries = imageEntries();
        const main = entries.find(entry => entry.file && entry.file === coverFile) || entries[0];
        const coverIndex = files.indexOf(coverFile);
        indexField.value = multiple && coverIndex >= 0 ? String(coverIndex) : "";
        cover.hidden = !main;
        empty.hidden = Boolean(main);
        if (main) cover.src = main.src;
        else cover.removeAttribute("src");
        items.replaceChildren();
        entries.forEach((entry, i) => {
            const item = document.createElement("div");
            item.className = "admin-upload-item";
            const thumb = document.createElement("img");
            thumb.src = entry.src;
            thumb.alt = "";
            thumb.loading = "lazy";
            thumb.referrerPolicy = "no-referrer";
            const meta = document.createElement("div");
            const label = document.createElement("strong");
            label.textContent = entry.file ? entry.file.name : `Ảnh đã lưu ${i + 1}`;
            const note = document.createElement("small");
            note.textContent = [entry === main ? "Ảnh đại diện" : "", entry.file ? "Chờ tải lên" : ""].filter(Boolean).join(" · ");
            const actions = document.createElement("div");
            actions.className = "admin-upload-actions";
            if (multiple && entry !== main) {
                actions.append(action("Đặt đại diện", `Đặt ảnh ${i + 1} làm đại diện`, () => {
                    coverFile = entry.file || null;
                    if (!entry.file) {
                        const saved = urls();
                        saved.unshift(saved.splice(entry.index, 1)[0]);
                        urlField.value = saved.join("\n");
                    }
                    render();
                    setStatus(`Đã chọn ảnh ${i + 1} làm đại diện.`);
                    input.focus({preventScroll: true});
                }));
            }
            actions.append(action("Gỡ ảnh", `Gỡ ảnh ${i + 1}`, () => {
                if (entry.file) {
                    if (canSyncFiles) files = files.filter(file => file !== entry.file);
                    else { input.value = ""; files = []; }
                    if (!files.includes(coverFile)) coverFile = null;
                    syncFileInput();
                } else {
                    urlField.value = urls().filter((_, index) => index !== entry.index).join("\n");
                }
                render();
                setStatus("Đã gỡ ảnh khỏi biểu mẫu. Bấm Lưu để cập nhật.");
                input.focus({preventScroll: true});
            }, true));
            meta.append(label, note, actions);
            item.append(thumb, meta);
            items.append(item);
        });
    }

    function addFiles(incoming, fromPicker) {
        if (!incoming.length) return;
        if (!canSyncFiles && !fromPicker) {
            setStatus("Hãy dùng nút Chọn hình trên trình duyệt này.", true);
            return;
        }
        const next = multiple && canSyncFiles ? files.slice() : [];
        for (const file of incoming) {
            if (!next.some(old => old.name === file.name && old.size === file.size && old.lastModified === file.lastModified)) next.push(file);
        }
        let error = "";
        if (next.length > maxFiles) error = `Mỗi lần lưu chỉ chọn tối đa ${maxFiles} ảnh mới.`;
        else if (next.some(file => !/\.(jpe?g|png|webp|gif)$/i.test(file.name) && !/^image\/(jpeg|png|webp|gif)$/.test(file.type))) error = "Chỉ chọn ảnh JPG, PNG, WEBP hoặc GIF.";
        else if (next.some(file => file.size <= 0 || file.size > maxFileSize)) error = "Mỗi ảnh phải có dữ liệu và không vượt 5 MB.";
        else if (next.reduce((sum, file) => sum + file.size, 0) > maxTotalSize) error = "Tổng kích thước ảnh mới không được vượt 20 MB.";
        if (error) {
            if (!canSyncFiles) { input.value = ""; files = []; coverFile = null; }
            syncFileInput();
            render();
            setStatus(error, true);
            return;
        }
        files = next;
        if (!files.includes(coverFile)) coverFile = null;
        syncFileInput();
        render();
        setStatus(`Đã chọn ${files.length} ảnh mới. Bấm Lưu để tải lên.`);
    }

    input.addEventListener("change", () => addFiles(Array.from(input.files), true));
    urlField.addEventListener("input", () => { coverFile = null; render(); });
    drop.addEventListener("dragover", event => {
        event.preventDefault();
        drop.classList.add("is-dragging");
    });
    drop.addEventListener("dragleave", event => {
        if (!drop.contains(event.relatedTarget)) drop.classList.remove("is-dragging");
    });
    drop.addEventListener("drop", event => {
        event.preventDefault();
        drop.classList.remove("is-dragging");
        addFiles(Array.from(event.dataTransfer.files), false);
    });
    const save = form.querySelector('button[type="submit"]');
    const originalLabel = save.textContent;
    let submitting = false;
    form.addEventListener("submit", event => {
        if (submitting) { event.preventDefault(); return; }
        if (files.length) {
            submitting = true;
            save.disabled = true;
            save.textContent = "Đang tải ảnh và lưu…";
            setStatus("Đang tải ảnh lên Cloudinary. Vui lòng chờ.");
        }
    });
    window.addEventListener("pageshow", () => {
        if (!submitting) return;
        submitting = false;
        save.disabled = false;
        save.textContent = originalLabel;
    });
    render();
}());
