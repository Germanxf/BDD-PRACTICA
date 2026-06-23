import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

# MODO_FALLO=1 simula la caida del coordinador tras la Fase 1
MODO_FALLO = os.environ.get("MODO_FALLO", "0") == "1"

PARTICIPANTES = [
    ("Inventario",  "http://inventario:8001/prepare",  "http://inventario:8001/commit"),
    ("Facturacion", "http://facturacion:8002/prepare", "http://facturacion:8002/commit"),
]

def enviar(url, nombre, accion):
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="POST"), timeout=5)
        print(f"[COORDINADOR] {nombre} acepto {accion}.", flush=True)
        return True
    except urllib.error.URLError as e:
        print(f"[COORDINADOR] ERROR: {nombre} no respondio a {accion}: {e.reason}", flush=True)
        return False

def fase1_prepare():
    print("\n[COORDINADOR] FASE 1 - Enviando PREPARE a todos los participantes...", flush=True)
    for nombre, url_prepare, _ in PARTICIPANTES:
        if not enviar(url_prepare, nombre, "PREPARE"):
            print("[COORDINADOR] Voto negativo. Iniciando ABORT global.", flush=True)
            return False
    print("[COORDINADOR] Todos los participantes respondieron YES.", flush=True)
    return True

def fase2_commit():
    print("\n[COORDINADOR] FASE 2 - Enviando COMMIT a todos los participantes...", flush=True)
    for nombre, _, url_commit in PARTICIPANTES:
        enviar(url_commit, nombre, "COMMIT")
    print("[COORDINADOR] Transaccion completada exitosamente.", flush=True)

def fase2_abort():
    print("\n[COORDINADOR] ABORT - Enviando ROLLBACK a todos los participantes.", flush=True)
    for nombre, _, url_commit in PARTICIPANTES:
        abort_url = url_commit.replace("/commit", "/rollback")
        try:
            urllib.request.urlopen(urllib.request.Request(abort_url, method="POST"), timeout=5)
        except Exception:
            pass
    print("[COORDINADOR] Transaccion abortada.", flush=True)

class CoordinatorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/venta":
            self.send_response(200)
            self.end_headers()
            print("\n[COORDINADOR] --- INICIO DE TRANSACCION DISTRIBUIDA ---", flush=True)

            if not fase1_prepare():
                fase2_abort()
                return

            if MODO_FALLO:
                # Punto critico del 2PC: el coordinador cae antes de enviar COMMIT.
                # Los participantes quedan en PREPARED sin saber que hacer: INCERTIDUMBRE.
                print("\n[COORDINADOR] SIMULACION: Coordinador cae antes de enviar COMMIT.", flush=True)
                print("[COORDINADOR] FATAL ERROR: os._exit(1)", flush=True)
                os._exit(1)
            else:
                fase2_commit()

    def log_message(self, format, *args):
        pass

print(f"[COORDINADOR] Iniciando en puerto 8000 | MODO_FALLO={MODO_FALLO}", flush=True)
server = HTTPServer(("0.0.0.0", 8000), CoordinatorHandler)
server.serve_forever()