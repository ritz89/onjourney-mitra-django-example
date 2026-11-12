document.querySelectorAll("form[data-prevent-double-submit]").forEach((form) => {
  form.addEventListener("submit", () => {
    if (!form.checkValidity()) return;
    const button = form.querySelector('button[type="submit"]');
    if (!button) return;
    button.disabled = true;
    button.textContent = "Memproses…";
  });
});
