import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

port = int(sys.argv[1])
name = sys.argv[2]

estado = "IDLE"
tiempo_prepare = 0

# Segundos que el participante espera la decision del coordinador antes de entrar en INCERTIDUMBRE
TIMEOUT = 4

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global estado, tiempo_prepare

        if self.path == "/prepare":
            # Fase 1: el participante bloquea sus recursos y vota YES
            estado = "PREPARED"
            tiempo_prepare = time.time()
            print(f"\n[{name}] PREPARE recibido. ESTADO: PREPARED", flush=True)
            print(f"[{name}] Recursos bloqueados. Esperando decision del coordinador.", flush=True)
            self.send_response(200)
            self.end_headers()

        elif self.path == "/commit":
            # Fase 2 exitosa: se aplican los cambios y se liberan los bloqueos
            estado = "COMMITTED"
            print(f"\n[{name}] COMMIT recibido. ESTADO: COMMITTED", flush=True)
            print(f"[{name}] Cambios aplicados. Recursos liberados.", flush=True)
            self.send_response(200)
            self.end_headers()

        elif self.path == "/rollback":
            # Fase 2 de abort: se deshacen los cambios y se liberan los bloqueos
            estado = "ABORTED"
            print(f"\n[{name}] ROLLBACK recibido. ESTADO: ABORTED", flush=True)
            print(f"[{name}] Cambios revertidos. Recursos liberados.", flush=True)
            self.send_response(200)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def monitor_incertidumbre():
    # Si el coordinador no responde tras el PREPARE, el participante no puede decidir solo:
    # hacer commit o rollback unilateral podria romper la consistencia global del sistema.
    global estado
    while True:
        time.sleep(2)
        if estado == "PREPARED" and (time.time() - tiempo_prepare) > TIMEOUT:
            print(f"\n[{name}] ALERTA: Timeout superado. Coordinador no responde.", flush=True)
            print(f"\n[{name}] ESTADO: INCERTIDUMBRE. Recursos siguen BLOQUEADOS.", flush=True)
            time.sleep(6)

print(f"[{name}] Iniciando en puerto {port}...", flush=True)
threading.Thread(target=monitor_incertidumbre, daemon=True).start()
server = HTTPServer(("0.0.0.0", port), RequestHandler)
server.serve_forever()