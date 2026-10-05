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

  // URL por defecto para el túnel de ngrok cuando se publica en GitHub Pages
  var NGROK_DEFAULT = "https://noma-doxastic-buzzingly.ngrok-free.dev";

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
    fetch(url, { method: "GET" })
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
    widget.style.cssText = "position:fixed; bottom:16px; right:16px; z-index:9999; display:flex; align-items:center; gap:8px; background:#0b1838; color:#fff; padding:8px 14px; border-radius:999px; box-shadow:0 6px 20px rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); font-size:13px; font-family:system-ui,sans-serif; cursor:pointer;";
    
    var dot = document.createElement("span");
    dot.style.cssText = "width:8px; height:8px; border-radius:50%; background:#f59e0b; display:inline-block;";
    
    var label = document.createElement("span");
    label.textContent = isLocal ? "Localhost (5000)" : "ngrok Backend";

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
        dot.style.boxShadow = "0 0 8px #10b981";
        label.textContent = isLocal ? "Backend Local Activo" : "ngrok Conectado";
      } else {
        dot.style.background = "#ef4444";
        dot.style.boxShadow = "0 0 8px #ef4444";
        label.textContent = isLocal ? "Backend Offline" : "ngrok Desconectado";
      }
    });

    widget.onclick = function() {
      var actual = getApiBase() || "http://localhost:5000";
      var nueva = prompt("🔧 Configuración de conexión Cliente-Servidor:\n\nIngresa la URL pública de tu túnel ngrok (ej: https://xxxx.ngrok-free.dev):", actual);
      if (nueva !== null) {
        setApiBase(nueva);
        alert("URL guardada. Comprobando conexión...");
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
