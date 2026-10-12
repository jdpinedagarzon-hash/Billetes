/**
 * Componentes de Presentación - Cámara en Tiempo Real & HUD Accesible
 * Control de vista previa de video, guías hápticas y lectores de pantalla (ARIA).
 */

class CamaraHUDAccesible {
    constructor(videoElement, hudElement) {
        this.video = videoElement;
        this.hud = hudElement;
        this.stream = null;
        this.activo = false;
    }

    async iniciar() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
            });
            if (this.video) {
                this.video.srcObject = this.stream;
                this.video.play();
                this.activo = true;
            }
            return true;
        } catch (err) {
            console.error("Error al acceder a la cámara:", err);
            return false;
        }
    }

    detener() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.activo = false;
    }

    anunciarLectorPantalla(texto) {
        const liveRegion = document.getElementById("aria-live-status") || this._crearLiveRegion();
        liveRegion.textContent = texto;
    }

    _crearLiveRegion() {
        const div = document.createElement("div");
        div.id = "aria-live-status";
        div.setAttribute("aria-live", "polite");
        div.setAttribute("aria-atomic", "true");
        div.style.cssText = "position:absolute; width:1px; height:1px; margin:-1px; padding:0; overflow:hidden; clip:rect(0,0,0,0); border:0;";
        document.body.appendChild(div);
        return div;
    }
}
window.CamaraHUDAccesible = CamaraHUDAccesible;
