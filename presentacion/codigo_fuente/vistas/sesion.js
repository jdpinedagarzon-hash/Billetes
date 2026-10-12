/**
 * sesion.js - Control centralizado de sesión y navegación para VisionCash / BilletIA.
 * 
 * Reglas de sesión solicitadas:
 * 1. La sesión se inicia al autenticarse en Menu_principal_2.html o verificar_2fa.html.
 * 2. La sesión SE MANTIENE al navegar entre páginas (Menu_principal, Soporte, Acerca de nosotros, Contacto, etc.).
 * 3. La sesión ÚNICAMENTE se cierra:
 *    a) Al pulsar el botón "Cerrar sesión".
 *    b) Al actualizar / recargar la página (F5 o botón de recargar del navegador).
 */

(function() {
  "use strict";

  // Inyectar estilos para el navbar autenticado (botón de logout y badge)
  function inyectarEstilos() {
    if (document.getElementById("sesion-styles")) return;
    var st = document.createElement("style");
    st.id = "sesion-styles";
    st.textContent = 
      ".nav .logout-btn { color: #fca5a5 !important; cursor: pointer; font-size: 16px; font-weight: 600; text-decoration: none; transition: color 0.2s ease; }" +
      ".nav .logout-btn:hover { color: #ef4444 !important; text-decoration: underline; }" +
      ".nav-user-chip { display: inline-flex; align-items: center; gap: 8px; padding: 7px 16px; background: rgba(255, 255, 255, 0.1); border-radius: 999px; border: 1px solid rgba(255, 255, 255, 0.2); font-size: 14.5px; color: #fff; font-weight: 600; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }";
    document.head.appendChild(st);
  }

  // Detectar si la página fue recargada / actualizada (F5 o botón de recargar)
  function detectarRecarga() {
    try {
      var navEntries = performance.getEntriesByType && performance.getEntriesByType("navigation");
      if (navEntries && navEntries.length > 0) {
        return navEntries[0].type === "reload";
      }
      if (window.performance && window.performance.navigation) {
        return window.performance.navigation.type === 1; // 1 = TYPE_RELOAD
      }
    } catch (e) {
      console.warn("[Sesión] No se pudo leer performance.navigation:", e);
    }
    return false;
  }

  var rutaActual = (window.location.pathname.split("/").pop() || "index.html").toLowerCase();
  var esPaginaProtegida = (
    rutaActual === "menu_principal.html" || 
    rutaActual === "soporte.html"
  );
  var esPaginaLogin = (
    rutaActual === "menu_principal_2.html" || 
    rutaActual === "menu_principal_3.html" || 
    rutaActual === "verificar_2fa.html"
  );

  var haRecargado = detectarRecarga();

  if (haRecargado && !esPaginaLogin) {
    // Si el usuario recargó/actualizó la página, se deslogea inmediatamente
    console.info("[Sesión] Página actualizada / recargada (F5). Cerrando sesión según especificación.");
    sessionStorage.removeItem("gv_auth_user");
    sessionStorage.removeItem("gv_auth_expiry");

    if (esPaginaProtegida) {
      window.location.replace("Menu_principal_2.html");
      return;
    }
  }

  // Obtener usuario autenticado en la sesión
  var usuarioAutenticado = sessionStorage.getItem("gv_auth_user");

  // Si es una página protegida y no hay usuario autenticado, redirigir al login
  if (esPaginaProtegida && !usuarioAutenticado) {
    console.info("[Sesión] Página protegida sin sesión activa. Redirigiendo a login.");
    window.location.replace("Menu_principal_2.html");
    return;
  }

  // Función para cerrar sesión manualmente
  function cerrarSesion() {
    sessionStorage.removeItem("gv_auth_user");
    sessionStorage.removeItem("gv_auth_expiry");
    window.location.href = "Menu_principal_2.html";
  }

  window.cerrarSesion = cerrarSesion;
  window.usuarioAutenticado = usuarioAutenticado;

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Actualizar componentes visuales de la interfaz
  function actualizarInterfaz() {
    inyectarEstilos();

    // Actualizar nombres de usuario en páginas que tienen los elementos
    var userGreeting = document.getElementById("userGreeting");
    if (userGreeting && usuarioAutenticado) userGreeting.textContent = usuarioAutenticado;

    var badgeUsername = document.getElementById("badgeUsername");
    if (badgeUsername && usuarioAutenticado) badgeUsername.textContent = usuarioAutenticado;

    var loggedUserSpan = document.getElementById("loggedUser");
    if (loggedUserSpan && usuarioAutenticado) loggedUserSpan.textContent = usuarioAutenticado;

    // Vincular todos los botones de logout
    var logoutBtns = document.querySelectorAll("#logoutBtn, .logout-btn");
    logoutBtns.forEach(function(btn) {
      btn.onclick = function(e) {
        e.preventDefault();
        cerrarSesion();
      };
    });

    // Enlace del logo a Menu_principal si está logeado, o index.html si es invitado
    var brandLink = document.querySelector(".site-header .brand");
    if (brandLink) {
      brandLink.href = usuarioAutenticado ? "Menu_principal.html" : "index.html";
    }

    // Actualizar barra de navegación principal
    var nav = document.querySelector(".site-header .nav");
    if (!nav) return;

    // Si ya estamos en una página protegida, el menú ya tiene los links internos
    if (esPaginaProtegida) {
      return;
    }

    if (usuarioAutenticado) {
      // Estado AUTENTICADO: mantiene la sesión en Acerca de nosotros, Contacto, etc.
      var esAcerca = (rutaActual === "acerca_nosotros.html");
      var esContacto = (rutaActual === "contacto.html");

      nav.innerHTML = 
        '<a href="Menu_principal.html">Inicio</a>' +
        '<a href="Soporte.html">Soporte</a>' +
        '<a href="acerca_nosotros.html"' + (esAcerca ? ' class="pill"' : '') + '>Acerca de nosotros</a>' +
        '<a href="Contacto.html"' + (esContacto ? ' class="pill"' : '') + '>Contacto</a>' +
        '<div class="nav-user-chip">' +
          '<span>👤</span> ' + escapeHtml(usuarioAutenticado) +
        '</div>' +
        '<a href="javascript:void(0)" id="logoutBtn" class="logout-btn">Cerrar sesión</a>';

      var newLogout = document.getElementById("logoutBtn");
      if (newLogout) {
        newLogout.onclick = function(e) {
          e.preventDefault();
          cerrarSesion();
        };
      }
    } else {
      // Estado INVITADO (no logeado)
      var esIndex = (rutaActual === "index.html" || rutaActual === "");
      var esAcercaGuest = (rutaActual === "acerca_nosotros.html");
      var esContactoGuest = (rutaActual === "contacto.html");

      nav.innerHTML = 
        '<a href="index.html"' + (esIndex ? ' class="pill"' : '') + '>Inicio</a>' +
        '<a href="acerca_nosotros.html"' + (esAcercaGuest ? ' class="pill"' : '') + '>Acerca de nosotros</a>' +
        '<a href="Contacto.html"' + (esContactoGuest ? ' class="pill"' : '') + '>Contacto</a>' +
        '<a href="Menu_principal_2.html">Iniciar sesión</a>' +
        '<a href="Menu_principal_3.html">Registrarse</a>';
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", actualizarInterfaz);
  } else {
    actualizarInterfaz();
  }
})();
