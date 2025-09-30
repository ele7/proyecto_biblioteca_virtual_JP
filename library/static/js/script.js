document.addEventListener("DOMContentLoaded", function () {
  // Inicializar Swiper
  const swiper = new Swiper(".mySwiper", {
    loop: true,
    navigation: {
      nextEl: ".swiper-button-next",
      prevEl: ".swiper-button-prev",
    },
    pagination: {
      el: ".swiper-pagination",
      clickable: true,
    },
    autoplay: {
      delay: 5000,
    },
  });

  // Ocultar banner si no estamos en dashboard
  if (!window.location.pathname.includes('dashboard')) {
    const banner = document.getElementById('mainBanner');
    if (banner) banner.style.display = 'none';
  }
});

