import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time

port = int(sys.argv[1])
name = sys.argv[2]
estado = "IDLE"
tiempo_prepare = 0

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global estado, tiempo_prepare
        if self.path == '/prepare':
            estado = "PREPARED"
            tiempo_prepare = time.time()
            print(f"\n[{name}] Fase 1: Peticion PREPARE recibida.", flush=True)
            print(f"[{name}] ESTADO: PREPARED. Recursos bloqueados esperando COMMIT.", flush=True)
            self.send_response(200)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def monitor_incertidumbre():
    global estado
    while True:
        time.sleep(2)
        if estado == "PREPARED" and (time.time() - tiempo_prepare) > 4:
            print(f"\n[{name}] ALERTA: Tiempo agotado. Coordinador no responde.", flush=True)
            print(f"[{name}] ESTADO: INCERTIDUMBRE. Sistema bloqueado.", flush=True)
            time.sleep(4)

print(f"Iniciando servicio de {name} en puerto {port}...", flush=True)
threading.Thread(target=monitor_incertidumbre, daemon=True).start()
server = HTTPServer(('0.0.0.0', port), RequestHandler)
server.serve_forever()