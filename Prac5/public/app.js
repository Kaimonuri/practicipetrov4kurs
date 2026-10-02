//19. Клиентская проверка полей регистрации в реальном времени
const rules = {
  username: [/^[A-Za-z0-9]{6,}$/, "Латиница и цифры, минимум 6 символов"],
  full_name: [/^[А-Яа-яЁё]+(?: [А-Яа-яЁё]+)+$/u, "Введите ФИО кириллицей"],
  phone: [/^8\(\d{3}\)\d{3}-\d{2}-\d{2}$/, "Формат: 8(XXX)XXX-XX-XX"],
  email: [/^[^\s@]+@[^\s@]+\.[^\s@]+$/, "Введите корректную почту"],
  password: [/^.{8,}$/, "Минимум 8 символов"],
};

async function validateInput(input) {
  const value = input.value.trim();
  const [pattern, errorMessage] = rules[input.dataset.validate];
  let message = pattern.test(value) ? "" : errorMessage;

  if (!message && input.name === "username") {
    const response = await fetch(`/api/validate-username?username=${encodeURIComponent(value)}`);
    if (!(await response.json()).valid) message = "Логин уже занят";
  }

  input.classList.toggle("invalid", Boolean(message));

  let hint = input.nextElementSibling;
  if (!hint || !hint.classList.contains("field-error")) {
    hint = document.createElement("span");
    hint.className = "field-error";
    input.after(hint);
  }
  hint.textContent = message;
}

for (const input of document.querySelectorAll("[data-validate]")) {
  input.addEventListener("input", () => validateInput(input));
  input.addEventListener("blur", () => validateInput(input));
}

for (const form of document.querySelectorAll('form[action^="/cart/add/"]')) {
  form.addEventListener("submit", () => {
    const button = form.querySelector("button");
    if (!button) return;

    button.style.transform = "scale(.93)";
    setTimeout(() => (button.style.transform = ""), 200);
  });
}
