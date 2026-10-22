// Находим каждый слайдер на странице и отдельно настраиваем его управление.
document.querySelectorAll('.slider').forEach((slider) => {
    const images = [...slider.querySelectorAll('img')];
    let index = 0;

    // step = 1 — следующий кадр, step = -1 — предыдущий.
    function show(step) {
        // Остаток от деления обеспечивает переход с последнего кадра на первый и обратно.
        index = (index + step + images.length) % images.length;
        // Показываем только текущую фотографию и обновляем счётчик под ней.
        images.forEach((image, current) => {
            image.hidden = current !== index;
        });
        slider.querySelector('[data-counter]').textContent = `${index + 1} / ${images.length}`;
    }

    // Назначаем действия кнопкам назад и вперёд.
    slider.querySelector('[data-prev]').onclick = () => show(-1);
    slider.querySelector('[data-next]').onclick = () => show(1);
    // Каждые 3000 мс переключаем кадр; в скрытой вкладке переключение пропускается.
    setInterval(() => {
        if (!document.hidden) show(1);
    }, 3000);
});
