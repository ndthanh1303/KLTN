/* JavaScript hỗ trợ thao tác; backend luôn kiểm tra lại dữ liệu và tính tiền. */
(function () {
    "use strict";

    document.querySelectorAll("[data-quantity-control]").forEach(function (control) {
        const input = control.querySelector('input[name="so_luong"]');
        if (!input) return;
        const buttons = Array.from(control.querySelectorAll("[data-quantity-step]"));
        const min = Number(input.min) || 1;
        const max = Number(input.max) || 2147483647;
        function sync() {
            const current = Number(input.value);
            buttons.forEach(function (button) {
                const step = Number(button.dataset.quantityStep);
                button.disabled = input.disabled || (step < 0 ? current <= min : current >= max);
            });
        }
        buttons.forEach(function (button) {
            button.addEventListener("click", function () {
                const value = Number(input.value);
                const current = Number.isInteger(value) ? value : min;
                input.value = String(Math.max(min, Math.min(max, current + Number(button.dataset.quantityStep))));
                sync();
            });
        });
        input.addEventListener("input", sync);
        sync();
    });

    const items = Array.from(document.querySelectorAll(".cart-item-check"));
    const selectAll = document.getElementById("cart-select-all");
    const totalText = document.getElementById("cart-selected-total");
    const quantityText = document.getElementById("cart-selected-quantity");
    const checkoutButton = document.getElementById("cart-checkout-button");
    const formatter = new Intl.NumberFormat("vi-VN");
    function cents(text) {
        if (!/^-?\d+(\.\d{1,2})?$/.test(text)) return 0n;
        const negative = text.startsWith("-");
        const parts = text.replace(/^-/, "").split(".");
        const result = BigInt(parts[0]) * 100n + BigInt((parts[1] || "").padEnd(2, "0"));
        return negative ? -result : result;
    }
    function updateSelection() {
        const available = items.filter(function (item) { return !item.disabled; });
        const selected = available.filter(function (item) { return item.checked; });
        let total = 0n;
        let quantity = 0n;
        selected.forEach(function (item) {
            total += cents(item.dataset.lineTotal);
            quantity += BigInt(item.dataset.quantity);
        });
        let vnd = total / 100n;
        const remainder = total % 100n;
        // Cùng cách làm tròn nửa về số chẵn với macro tiền trong Jinja/Python.
        if (remainder > 50n || (remainder === 50n && vnd % 2n !== 0n)) vnd += 1n;
        if (totalText) totalText.textContent = formatter.format(vnd) + " đ";
        if (quantityText) quantityText.textContent = formatter.format(quantity);
        if (checkoutButton) checkoutButton.disabled = selected.length === 0;
        if (selectAll) {
            selectAll.disabled = available.length === 0;
            selectAll.checked = available.length > 0 && selected.length === available.length;
            selectAll.indeterminate = selected.length > 0 && selected.length < available.length;
        }
    }
    items.forEach(function (item) { item.addEventListener("change", updateSelection); });
    if (selectAll) selectAll.addEventListener("change", function () {
        items.forEach(function (item) { if (!item.disabled) item.checked = selectAll.checked; });
        updateSelection();
    });
    if (items.length) updateSelection();

    const cartMessages = Array.from(document.querySelectorAll(".shop-message.cart_success"));
    if (cartMessages.length) {
        const stack = document.createElement("div");
        stack.className = "cart-toast-stack";
        stack.setAttribute("role", "region");
        stack.setAttribute("aria-label", "Thông báo giỏ hàng");
        document.body.appendChild(stack);
        cartMessages.forEach(function (message) {
            const text = document.createElement("span");
            text.textContent = message.textContent;
            const close = document.createElement("button");
            close.type = "button";
            close.className = "cart-toast-close";
            close.textContent = "×";
            close.setAttribute("aria-label", "Đóng thông báo");
            message.replaceChildren(text, close);
            stack.appendChild(message);
            const timer = window.setTimeout(function () { message.remove(); }, 6000);
            close.addEventListener("click", function () {
                window.clearTimeout(timer);
                message.remove();
            });
        });
    }

    document.querySelectorAll("[data-order-form]").forEach(function (form) {
        const button = form.querySelector("[data-order-submit]");
        if (!button) return;
        const original = button.textContent;
        form.addEventListener("submit", function () {
            button.disabled = true;
            button.textContent = "Đang đặt hàng…";
        });
        window.addEventListener("pageshow", function () {
            button.disabled = false;
            button.textContent = original;
        });
    });
}());
