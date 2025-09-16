document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("loginForm");
    const mensaje = document.getElementById("mensaje");
  
    if (form) {
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
  
        const formData = new FormData(form);
  
        try {
          const response = await fetch(form.action, {
            method: "POST",
            headers: {
              "X-CSRFToken": formData.get("csrfmiddlewaretoken"),
            },
            body: formData,
          });
  
          const data = await response.json();
  
          if (data.success) {
            window.location.href = data.redirect;
          } else {
            mensaje.innerText = data.error || "Error al iniciar sesión";
          }
        } catch (error) {
          mensaje.innerText = "Error de conexión con el servidor";
        }
      });
    }
  });