// Четыре одинаковых по размеру кадра; автоматическое переключение раз в 3 секунды.
// БРЕЙКПОИНТ 13: кнопки слайдера и смена изображения каждые 3000 мс.
document.querySelectorAll(".slider").forEach((slider) => {
    const images = [...slider.querySelectorAll("img")];
    let index = 0;
    let paused = false;
    const show = (step) => {
        index = (index + step + images.length) % images.length;
        images.forEach((image, i) => {
            image.hidden = i !== index;
        });
        slider.querySelector("[data-counter]").textContent =
            `${index + 1} / ${images.length}`;
    };
    slider.querySelector("[data-prev]").onclick = () => show(-1);
    slider.querySelector("[data-next]").onclick = () => show(1);
    slider.querySelector("[data-pause]").onclick = (event) => {
        paused = !paused;
        event.currentTarget.textContent = paused ? "Пуск" : "Пауза";
        event.currentTarget.setAttribute(
            "aria-label",
            paused ? "Запустить слайдер" : "Приостановить слайдер",
        );
    };
    setInterval(() => {
        if (!paused && !document.hidden) show(1);
    }, 3000);
});
