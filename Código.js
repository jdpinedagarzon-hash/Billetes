const DEFAULT_PAGE = "Menu_principal_2";
const DEFAULT_API_BASE = "https://noma-doxastic-buzzingly.ngrok-free.dev";
const BRAND_IMAGES = {
	logo: "1O_OWAxUyl5wlFmPimxlEEtcDesRBQZqZ",
	twitter: "12_VpHwYJu0iQMyMLWC9yoRkhiNUAmNCq",
	instagram: "1jG_3vYvVuZ947123y7Tvs1jC792Jc2Vz",
	youtube: "1BP3aWBoBcIPiNnLsTATtfgKdGfhgOGdz"
};
const ALLOWED_PAGES = new Set([
	"Menu_principal",
	"Menu_principal_2",
	"Menu_principal_3",
	"Soporte",
	"acerca_nosotros",
	"Contacto",
	"Politicas",
	"Terminos",
	"verificar_2fa"
]);

function doGet(e) {
	const requestedPage = (e && e.parameter && e.parameter.page) || DEFAULT_PAGE;
	const page = ALLOWED_PAGES.has(requestedPage) ? requestedPage : DEFAULT_PAGE;
	const template = HtmlService.createTemplateFromFile(page);
	template.appUrl = ScriptApp.getService().getUrl();
	template.apiBase = getApiBase();
	template.brandImages = getBrandImages();

	return template
		.evaluate()
		.setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function include(filename) {
	return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

function getBrandImages() {
	const fallback = {
		logo: "https://drive.google.com/uc?export=view&id=" + BRAND_IMAGES.logo,
		twitter: "https://drive.google.com/uc?export=view&id=" + BRAND_IMAGES.twitter,
		instagram: "https://drive.google.com/uc?export=view&id=" + BRAND_IMAGES.instagram,
		youtube: "https://drive.google.com/uc?export=view&id=" + BRAND_IMAGES.youtube
	};

	const out = Object.assign({}, fallback);
	const cache = CacheService.getScriptCache();

	Object.keys(BRAND_IMAGES).forEach(key => {
		const fileId = BRAND_IMAGES[key];
		const cacheKey = `brand_dataurl_${key}_${fileId}`;
		const cached = cache.get(cacheKey);
		if (cached) {
			out[key] = cached;
			return;
		}

		try {
			const url = `https://drive.google.com/uc?export=view&id=${encodeURIComponent(fileId)}`;
			const response = UrlFetchApp.fetch(url, {
				method: "get",
				muteHttpExceptions: true
			});
			if (response.getResponseCode() >= 200 && response.getResponseCode() < 300) {
				const blob = response.getBlob();
				const mime = blob.getContentType() || "image/png";
				const b64 = Utilities.base64Encode(blob.getBytes());
				const dataUrl = `data:${mime};base64,${b64}`;
				out[key] = dataUrl;
				cache.put(cacheKey, dataUrl, 21600);
			}
		} catch (e) {
			// deja fallback URL si falla fetch/base64
		}
	});

	return out;
}

function getApiBase() {
	const stored = (PropertiesService.getScriptProperties().getProperty("API_BASE") || "").trim().replace(/\/+$/, "");
	if (!stored) {
		return DEFAULT_API_BASE;
	}
	if (!/^https:\/\//i.test(stored)) {
		return DEFAULT_API_BASE;
	}
	if (/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(stored)) {
		return DEFAULT_API_BASE;
	}
	return stored;
}

function setApiBase(url) {
	const normalized = String(url || "").trim().replace(/\/+$/, "");
	if (!normalized) {
		throw new Error("Debes enviar una URL válida.");
	}
	if (!/^https:\/\//i.test(normalized)) {
		throw new Error("API_BASE debe usar HTTPS (ej: https://xxxx.ngrok-free.dev).");
	}
	if (/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(normalized)) {
		throw new Error("No uses localhost/127.0.0.1 en Apps Script. Usa la URL pública de ngrok.");
	}
	PropertiesService.getScriptProperties().setProperty("API_BASE", normalized);
	return normalized;
}

function backendRequest(path, method, payload) {
	const base = getApiBase();
	if (!base) {
		throw new Error("API_BASE no está configurado.");
	}

	const url = `${base}${path}`;
	const options = {
		method: String(method || "get").toLowerCase(),
		muteHttpExceptions: true,
		headers: {
			"Content-Type": "application/json",
			"ngrok-skip-browser-warning": "true"
		}
	};

	if (payload !== undefined && payload !== null) {
		options.payload = JSON.stringify(payload);
	}

	let response;
	try {
		response = UrlFetchApp.fetch(url, options);
	} catch (err) {
		throw new Error(`No se pudo conectar al backend (${base}). ${err}`);
	}

	const status = response.getResponseCode();
	const raw = response.getContentText() || "";
	let json = {};
	try {
		json = raw ? JSON.parse(raw) : {};
	} catch (e) {
		json = { ok: false, message: raw || "Respuesta no JSON del backend." };
	}

	return {
		status,
		ok: status >= 200 && status < 300,
		body: json
	};
}

function apiRegister(payload) {
	return backendRequest("/api/register", "post", payload);
}

function apiLogin(payload) {
	return backendRequest("/api/login", "post", payload);
}

function apiGetQr(username) {
	const safeUser = encodeURIComponent(String(username || "").trim());
	const query = safeUser ? `?username=${safeUser}` : "";
	return backendRequest(`/api/2fa-qr${query}`, "get");
}

function apiGetQrImageDataUrl(username) {
	const safeUser = encodeURIComponent(String(username || "").trim());
	if (!safeUser) {
		throw new Error("Usuario requerido para obtener QR.");
	}

	const base = getApiBase();
	const url = `${base}/api/2fa-qr-image?username=${safeUser}`;
	let response;
	try {
		response = UrlFetchApp.fetch(url, {
			method: "get",
			muteHttpExceptions: true,
			headers: { "ngrok-skip-browser-warning": "true" }
		});
	} catch (err) {
		throw new Error(`No se pudo descargar el QR (${base}). ${err}`);
	}

	const status = response.getResponseCode();
	if (status < 200 || status >= 300) {
		throw new Error(`No se pudo descargar la imagen QR. HTTP ${status}`);
	}

	const contentType = response.getHeaders()["Content-Type"] || "image/png";
	const bytes = response.getContent();
	const b64 = Utilities.base64Encode(bytes);
	return `data:${contentType};base64,${b64}`;
}

function apiConfirm2FA(payload) {
	return backendRequest("/api/confirm-2fa", "post", payload);
}

function _decodeDataUrlImage(dataUrl) {
	const value = String(dataUrl || "").trim();
	const match = value.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,([\s\S]+)$/i);
	if (!match) {
		throw new Error("Imagen inválida. Debe enviarse en formato data URL base64.");
	}
	const mimeType = match[1].toLowerCase();
	const base64 = match[2].replace(/\s+/g, "");
	const bytes = Utilities.base64Decode(base64);
	const extMap = {
		"image/jpeg": "jpg",
		"image/jpg": "jpg",
		"image/png": "png",
		"image/gif": "gif",
		"image/webp": "webp",
		"image/svg+xml": "svg"
	};
	const ext = extMap[mimeType] || "img";
	const blob = Utilities.newBlob(bytes, mimeType, `imagen.${ext}`);
	return { blob, mimeType };
}

function apiClasificar(payload) {
	const base = getApiBase();
	if (!base) {
		throw new Error("API_BASE no está configurado.");
	}

	const dataUrl = payload && payload.imageDataUrl;
	const username = String((payload && payload.username) || "").trim();
	const decoded = _decodeDataUrlImage(dataUrl);
	const query = username ? `?username=${encodeURIComponent(username)}` : "";
	const url = `${base}/api/clasificar${query}`;

	let response;
	try {
		response = UrlFetchApp.fetch(url, {
			method: "post",
			muteHttpExceptions: true,
			headers: { "ngrok-skip-browser-warning": "true" },
			payload: { imagen: decoded.blob }
		});
	} catch (err) {
		throw new Error(`No se pudo conectar al backend (${base}). ${err}`);
	}

	const status = response.getResponseCode();
	const raw = response.getContentText() || "";
	let body = {};
	try {
		body = raw ? JSON.parse(raw) : {};
	} catch (e) {
		body = { ok: false, error: raw || "Respuesta no JSON del backend." };
	}

	return {
		status,
		ok: status >= 200 && status < 300,
		body
	};
}

function apiSupportCreate(payload) {
	return backendRequest("/api/support/tickets", "post", payload);
}

function apiSupportMine(username, limit) {
	const safeUser = encodeURIComponent(String(username || "").trim());
	const safeLimit = Math.max(1, Math.min(Number(limit || 30) || 30, 200));
	const query = safeUser ? `?username=${safeUser}&limit=${safeLimit}` : `?limit=${safeLimit}`;
	return backendRequest(`/api/support/tickets${query}`, "get");
}

function apiSupportDetail(payload) {
	const ticketId = Number(payload && payload.ticketId);
	if (!ticketId) {
		throw new Error("Debes indicar un ticket válido.");
	}
	const safeUser = encodeURIComponent(String((payload && payload.username) || "").trim());
	const query = safeUser ? `?username=${safeUser}` : "";
	return backendRequest(`/api/support/tickets/${ticketId}${query}`, "get");
}

function apiSupportTicketSurvey(payload) {
	const ticketId = Number(payload && payload.ticketId);
	if (!ticketId) {
		throw new Error("Debes indicar un ticket válido.");
	}
	return backendRequest(`/api/support/tickets/${ticketId}/survey`, "post", payload);
}

function apiGeneralSurveyPending(payload) {
	const safeUser = encodeURIComponent(String((payload && payload.username) || "").trim());
	const query = safeUser ? `?username=${safeUser}` : "";
	return backendRequest(`/api/surveys/general/pending${query}`, "get");
}

function apiGeneralSurveySubmit(payload) {
	const surveyId = Number(payload && payload.surveyId);
	if (!surveyId) {
		throw new Error("Debes indicar una encuesta válida.");
	}
	return backendRequest("/api/surveys/general/submit", "post", payload);
}

function pingBackend() {
	return backendRequest("/api/session", "get");
}
