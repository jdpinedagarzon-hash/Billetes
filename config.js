/**
 * config.js - Configuración del Backend y túnel ngrok para VisionCash / BilletIA.
 * 
 * Permite que el frontend alojado en GitHub Pages se comunique directamente
 * con el backend PyTorch y la base de datos MySQL a través de ngrok.
 */

var CONFIG = (function() {
  "use strict";

  var isLocal = (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.protocol === "file:"
  );

  // URL activa de tu túnel ngrok actual
  var NGROK_DEFAULT = "https://b7f1-181-53-12-63.ngrok-free.app";

  // Interceptar window.fetch para inyectar automáticamente la cabecera ngrok-skip-browser-warning
  var originalFetch = window.fetch;
  window.fetch = function(input, init) {
    init = init || {};
    init.headers = init.headers || {};

    if (init.headers instanceof Headers) {
      if (!init.headers.has("ngrok-skip-browser-warning")) {
        init.headers.set("ngrok-skip-browser-warning", "true");
      }
    } else if (Array.isArray(init.headers)) {
      init.headers.push(["ngrok-skip-browser-warning", "true"]);
    } else {
      init.headers["ngrok-skip-browser-warning"] = "true";
    }

    return originalFetch.call(this, input, init);
  };

  function getApiBase() {
    var stored = localStorage.getItem("visioncash_api_url");
    if (stored) return stored.replace(/\/+$/, "");
    return isLocal ? "" : NGROK_DEFAULT;
  }

  function setApiBase(url) {
    if (!url || !url.trim()) {
      localStorage.removeItem("visioncash_api_url");
    } else {
      url = url.trim().replace(/\/+$/, "");
      if (!/^https?:\/\//i.test(url)) {
        url = "https://" + url;
      }
      localStorage.setItem("visioncash_api_url", url);
    }
  }

  function apiUrl(path) {
    var base = getApiBase();
    var p = path.startsWith("/") ? path : "/" + path;
    return base + p;
  }

  // Comprobar estado de conexión con el backend
  function verificarConexion(callback) {
    var url = apiUrl("/api/status");
    fetch(url, { 
      method: "GET",
      headers: { "ngrok-skip-browser-warning": "true" }
    })
      .then(function(res) { return res.json(); })
      .then(function(data) {
        if (callback) callback(true, data);
      })
      .catch(function(err) {
        if (callback) callback(false, err);
      });
  }

  // Interfaz visual flotante para configurar ngrok en GitHub Pages
  function inyectarBotonServidor() {
    if (document.getElementById("ngrok-status-widget")) return;

    var widget = document.createElement("div");
    widget.id = "ngrok-status-widget";
    widget.style.cssText = "position:fixed; bottom:16px; right:16px; z-index:9999; display:flex; align-items:center; gap:8px; background:#0b1838; color:#fff; padding:9px 16px; border-radius:999px; box-shadow:0 6px 22px rgba(0,0,0,0.35); border:1px solid rgba(255,255,255,0.2); font-size:13.5px; font-family:system-ui,-apple-system,sans-serif; cursor:pointer; user-select:none; transition:all 0.2s ease;";
    
    var dot = document.createElement("span");
    dot.style.cssText = "width:10px; height:10px; border-radius:50%; background:#f59e0b; display:inline-block; transition:all 0.3s ease;";
    
    var label = document.createElement("span");
    label.style.fontWeight = "600";
    label.textContent = isLocal ? "Localhost (5000)" : "Comprobando ngrok...";

    var btnConfig = document.createElement("span");
    btnConfig.textContent = "⚙️";
    btnConfig.title = "Configurar URL de ngrok";

    widget.appendChild(dot);
    widget.appendChild(label);
    widget.appendChild(btnConfig);
    document.body.appendChild(widget);

    // Verificar salud inicial
    verificarConexion(function(ok, res) {
      if (ok) {
        dot.style.background = "#10b981";
        dot.style.boxShadow = "0 0 10px #10b981";
        label.textContent = isLocal ? "Backend Local Activo" : "ngrok Conectado";
      } else {
        dot.style.background = "#ef4444";
        dot.style.boxShadow = "0 0 10px #ef4444";
        label.textContent = isLocal ? "Backend Offline" : "ngrok Desconectado (Clic aquí)";
      }
    });

    widget.onclick = function() {
      var actual = getApiBase() || NGROK_DEFAULT;
      var nueva = prompt("🔧 Configuración de conexión Cliente-Servidor:\n\nIngresa la URL pública de tu túnel ngrok activo:", actual);
      if (nueva !== null && nueva.trim()) {
        setApiBase(nueva);
        alert("¡URL guardada! Reconectando con el backend...");
        window.location.reload();
      }
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", inyectarBotonServidor);
  } else {
    inyectarBotonServidor();
  }

  return {
    isLocal: isLocal,
    getApiBase: getApiBase,
    setApiBase: setApiBase,
    apiUrl: apiUrl,
    verificarConexion: verificarConexion
  };
})();
