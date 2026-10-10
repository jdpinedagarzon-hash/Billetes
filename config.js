/**
 * config.js - Configuración del Backend y Túnel ngrok Automático para VisionCash / BilletIA.
 * 
 * Funcionalidad 100% Automática:
 * - Detecta el túnel activo de ngrok consultando GitHub Raw y la API de GitHub en tiempo real.
 * - Auto-descarta URLs caducadas guardadas en localStorage.
 * - Intercepta window.fetch para redirigir peticiones obsoletas al túnel activo y añadir ngrok-skip-browser-warning.
 * - Widget flotante con indicador visual en tiempo real (Amarillo: detectando, Verde: conectado, Rojo: offline).
 */

var CONFIG = (function() {
  "use strict";

  var GITHUB_RAW_URL = "https://raw.githubusercontent.com/jdpinedagarzon-hash/Billetes/main/ngrok_url.txt";
  var GITHUB_API_URL = "https://api.github.com/repos/jdpinedagarzon-hash/Billetes/contents/ngrok_url.txt";

  var isLocal = (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
  );

  // URL fallback sincronizada con app.py
  var NGROK_DEFAULT = "https://08ed-181-53-12-63.ngrok-free.app";

  var activeApiBase = "";
  var resolucionEnProgreso = false;
  var listeners = [];

  function normalizarUrl(url) {
    if (!url || typeof url !== "string") return "";
    var limpia = url.trim().replace(/\/+$/, "");
    if (!limpia) return "";
    if (!/^https?:\/\//i.test(limpia)) {
      limpia = "https://" + limpia;
    }
    return limpia;
  }

  function getApiBase() {
    if (activeApiBase) return activeApiBase;
    var stored = localStorage.getItem("visioncash_api_url");
    if (stored) {
      activeApiBase = normalizarUrl(stored);
      return activeApiBase;
    }
    if (isLocal) {
      activeApiBase = "";
      return "";
    }
    activeApiBase = normalizarUrl(NGROK_DEFAULT);
    return activeApiBase;
  }

  function setApiBase(url) {
    var normalizada = normalizarUrl(url);
    activeApiBase = normalizada;
    if (normalizada) {
      localStorage.setItem("visioncash_api_url", normalizada);
    } else {
      localStorage.removeItem("visioncash_api_url");
    }
    notificarCambio(normalizada);
  }

  function apiUrl(path) {
    var base = getApiBase();
    var p = path.startsWith("/") ? path : "/" + path;
    return base ? (base + p) : p;
  }

  function notificarCambio(url) {
    try {
      window.dispatchEvent(new CustomEvent("visioncash_backend_ready", { detail: { url: url } }));
    } catch (_) {}
    listeners.forEach(function(fn) {
      try { fn(url); } catch (_) {}
    });
  }

  // Interceptar window.fetch para:
  // 1. Redirigir URLs que contengan un ngrok viejo hacia el túnel activo actual.
  // 2. Si estamos en GitHub Pages y llaman a /api/..., anteponer el túnel ngrok.
  // 3. Añadir la cabecera ngrok-skip-browser-warning automáticamente.
  var originalFetch = window.fetch;
  window.fetch = function(input, init) {
    init = init || {};
    init.headers = init.headers || {};

    // 1. Normalización de cabeceras
    if (init.headers instanceof Headers) {
      if (!init.headers.has("ngrok-skip-browser-warning")) {
        init.headers.set("ngrok-skip-browser-warning", "true");
      }
    } else if (Array.isArray(init.headers)) {
      init.headers.push(["ngrok-skip-browser-warning", "true"]);
    } else {
      init.headers["ngrok-skip-browser-warning"] = "true";
    }

    // 2. Reescritura inteligente de URLs obsoletas
    if (typeof input === "string") {
      var base = getApiBase();
      if (base) {
        if (input.startsWith("/api/")) {
          input = base + input;
        } else if (/https?:\/\/[a-z0-9\-]+\.ngrok-free\.app/i.test(input)) {
          input = input.replace(/https?:\/\/[a-z0-9\-]+\.ngrok-free\.app/i, base);
        }
      }
    }

    return originalFetch.call(this, input, init);
  };

  // Comprobar si una URL de backend específica está respondiendo
  function probarUrl(url, timeoutMs, callback) {
    var controller = (typeof AbortController !== "undefined") ? new AbortController() : null;
    var timer = null;
    if (controller && timeoutMs) {
      timer = setTimeout(function() { controller.abort(); }, timeoutMs);
    }

    var testUrl = normalizarUrl(url) + "/api/status";
    originalFetch(testUrl, {
      method: "GET",
      headers: { "ngrok-skip-browser-warning": "true" },
      signal: controller ? controller.signal : undefined
    })
      .then(function(res) {
        if (timer) clearTimeout(timer);
        if (res.ok) {
          return res.json().catch(function() { return {}; });
        }
        throw new Error("HTTP " + res.status);
      })
      .then(function(data) {
        callback(true, data);
      })
      .catch(function(err) {
        if (timer) clearTimeout(timer);
        callback(false, err);
      });
  }

  // Comprobar estado de conexión actual
  function verificarConexion(callback) {
    var base = getApiBase();
    if (isLocal && !base) {
      probarUrl(window.location.origin, 3000, function(ok, data) {
        if (!ok) {
          probarUrl("http://localhost:5000", 3000, function(okLocal, dataLocal) {
            if (callback) callback(okLocal, dataLocal);
          });
        } else {
          if (callback) callback(ok, data);
        }
      });
      return;
    }

    probarUrl(base, 3500, function(ok, data) {
      if (callback) callback(ok, data);
    });
  }

  // Auto-resolución en tiempo real desde GitHub (sin pedirle nada al usuario)
  function autoDetectarNgrok(onListo) {
    if (isLocal) {
      actualizarWidgetEstado("conectado", "Backend Local Activo");
      if (onListo) onListo(true, "http://localhost:5000");
      return;
    }

    if (resolucionEnProgreso) return;
    resolucionEnProgreso = true;

    actualizarWidgetEstado("buscando", "Detectando túnel ngrok...");

    // 1. Probar primero si el actual guardado aún sirve
    var actual = localStorage.getItem("visioncash_api_url") || NGROK_DEFAULT;
    if (actual) {
      probarUrl(actual, 2500, function(ok, data) {
        if (ok) {
          resolucionEnProgreso = false;
          setApiBase(actual);
          actualizarWidgetEstado("conectado", "ngrok Conectado");
          if (onListo) onListo(true, actual);
          return;
        }

        // Si falló, borrar el localStorage viejo y consultar GitHub
        localStorage.removeItem("visioncash_api_url");
        consultarGitHubParaNgrok(onListo);
      });
    } else {
      consultarGitHubParaNgrok(onListo);
    }
  }

  function consultarGitHubParaNgrok(onListo) {
    var rawUrl = GITHUB_RAW_URL + "?nocache=" + Date.now();

    // Intentar GitHub Raw con bypass de caché
    originalFetch(rawUrl, {
      headers: { "Cache-Control": "no-cache" }
    })
      .then(function(res) {
        if (!res.ok) throw new Error("GitHub Raw " + res.status);
        return res.text();
      })
      .then(function(texto) {
        var candidata = (texto || "").trim();
        if (candidata.startsWith("http")) {
          probarYCerrar(candidata, onListo);
        } else {
          throw new Error("Contenido inválido en raw");
        }
      })
      .catch(function() {
        // Fallback a GitHub REST API (libre de CDN Fastly)
        originalFetch(GITHUB_API_URL, {
          headers: { "Accept": "application/vnd.github.v3+json" }
        })
          .then(function(res) { return res.json(); })
          .then(function(data) {
            if (data && data.content) {
              var dec = atob(data.content.replace(/\s+/g, "")).trim();
              if (dec.startsWith("http")) {
                probarYCerrar(dec, onListo);
                return;
              }
            }
            throw new Error("No URL en GitHub API");
          })
          .catch(function() {
            resolucionEnProgreso = false;
            actualizarWidgetEstado("desconectado", "ngrok Desconectado (Reintentando...)");
            // Reintentar automáticamente cada 3.5 segundos
            setTimeout(function() { autoDetectarNgrok(onListo); }, 3500);
          });
      });
  }

  function probarYCerrar(candidata, onListo) {
    probarUrl(candidata, 3500, function(ok) {
      resolucionEnProgreso = false;
      if (ok) {
        setApiBase(candidata);
        actualizarWidgetEstado("conectado", "ngrok Conectado");
        if (onListo) onListo(true, candidata);
      } else {
        actualizarWidgetEstado("desconectado", "ngrok Desconectado (Reintentando...)");
        setTimeout(function() { autoDetectarNgrok(onListo); }, 3500);
      }
    });
  }

  function actualizarWidgetEstado(estado, texto) {
    var dot = document.getElementById("ngrok-status-dot");
    var label = document.getElementById("ngrok-status-label");
    if (!dot || !label) return;

    if (estado === "conectado") {
      dot.style.background = "#10b981";
      dot.style.boxShadow = "0 0 10px #10b981";
      label.textContent = isLocal ? "Backend Local Activo" : "ngrok Conectado";
    } else if (estado === "buscando") {
      dot.style.background = "#f59e0b";
      dot.style.boxShadow = "0 0 10px #f59e0b";
      label.textContent = texto || "Conectando...";
    } else {
      dot.style.background = "#ef4444";
      dot.style.boxShadow = "0 0 10px #ef4444";
      label.textContent = texto || (isLocal ? "Backend Offline" : "ngrok Desconectado");
    }
  }

  // Interfaz visual flotante inteligente
  function inyectarBotonServidor() {
    if (document.getElementById("ngrok-status-widget")) return;

    var widget = document.createElement("div");
    widget.id = "ngrok-status-widget";
    widget.style.cssText = "position:fixed; bottom:16px; right:16px; z-index:9999; display:flex; align-items:center; gap:8px; background:#0b1838; color:#fff; padding:9px 16px; border-radius:999px; box-shadow:0 6px 22px rgba(0,0,0,0.35); border:1px solid rgba(255,255,255,0.2); font-size:13.5px; font-family:system-ui,-apple-system,sans-serif; cursor:pointer; user-select:none; transition:all 0.2s ease;";
    
    var dot = document.createElement("span");
    dot.id = "ngrok-status-dot";
    dot.style.cssText = "width:10px; height:10px; border-radius:50%; background:#f59e0b; display:inline-block; transition:all 0.3s ease;";
    
    var label = document.createElement("span");
    label.id = "ngrok-status-label";
    label.style.fontWeight = "600";
    label.textContent = isLocal ? "Localhost (5000)" : "Sincronizando ngrok...";

    var btnConfig = document.createElement("span");
    btnConfig.textContent = "⚙️";
    btnConfig.title = "Configuración manual o reconexión";

    widget.appendChild(dot);
    widget.appendChild(label);
    widget.appendChild(btnConfig);
    document.body.appendChild(widget);

    // Iniciar auto-detección instantánea
    autoDetectarNgrok(function(ok, url) {
      if (ok) {
        console.log("[CONFIG] Conectado exitosamente al backend:", url);
      }
    });

    widget.onclick = function() {
      var actual = getApiBase() || NGROK_DEFAULT;
      var nueva = prompt("🔧 Configuración de conexión Cliente-Servidor:\n\nIngresa la URL pública de tu túnel ngrok (o déjalo en blanco para auto-detectar desde GitHub):", actual);
      if (nueva !== null) {
        if (!nueva.trim()) {
          localStorage.removeItem("visioncash_api_url");
          autoDetectarNgrok();
        } else {
          setApiBase(nueva);
          alert("¡URL guardada! Reconectando...");
          window.location.reload();
        }
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
    verificarConexion: verificarConexion,
    autoDetectarNgrok: autoDetectarNgrok,
    onReady: function(fn) {
      if (typeof fn === "function") listeners.push(fn);
    }
  };
})();
