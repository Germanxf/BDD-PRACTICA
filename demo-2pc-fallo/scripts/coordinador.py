import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
import os

class CoordinatorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/venta':
            print("\n--- [COORDINADOR] INICIANDO VENTA DISTRIBUIDA ---", flush=True)
            
            try:
                print("[COORDINADOR] FASE 1: Enviando PREPARE a Inventario...", flush=True)
                urllib.request.urlopen(urllib.request.Request("http://inventario:8001/prepare", method="POST"))
                
                print("[COORDINADOR] FASE 1: Enviando PREPARE a Facturacion...", flush=True)
                urllib.request.urlopen(urllib.request.Request("http://facturacion:8002/prepare", method="POST"))
                
                print("\n[COORDINADOR] OK: Todos los nodos listos (PREPARED).", flush=True)
                
                print("\n[COORDINADOR] SIMULACION: Forzando caida del coordinador...", flush=True)
                print("[COORDINADOR] FATAL ERROR: Sistema apagado antes de enviar COMMIT.", flush=True)
                
                os._exit(1)
                
            except Exception as e:
                print(f"Error: {e}")

    def log_message(self, format, *args):
        pass

print("Iniciando Coordinador en puerto 8000...", flush=True)
server = HTTPServer(('0.0.0.0', 8000), CoordinatorHandler)
server.serve_forever()