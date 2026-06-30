import urllib.request, urllib.error, os, uuid, time
from http.server import BaseHTTPRequestHandler, HTTPServer

MODO_FALLO = os.environ.get("MODO_FALLO", "0") == "1"

INV_BASE = "http://inventario:8001"
FAC_BASE = "http://facturacion:8002"

# Parametros de la venta (pueden venir en el request, pero usamos defaults demo)
VENTA_DEFAULT = {
    "medicamento_id": "1",
    "cantidad":       "5",
    "cliente":        "Juan+Perez",
    "total":          "2.25"
}


def enviar(url, nombre, accion, body=b"", timeout=6):
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = r.read().decode()
        print(f"[COORDINADOR] {nombre} -> {accion}: {resp}", flush=True)
        return True, resp
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        print(f"[COORDINADOR] {nombre} RECHAZO {accion}: {body_err}", flush=True)
        return False, body_err
    except Exception as e:
        print(f"[COORDINADOR] ERROR contactando {nombre}: {e}", flush=True)
        return False, str(e)


class CoordHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/venta":
            self.send_response(404); self.end_headers(); return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length).decode() if length else ""
        params = dict(p.split("=") for p in body.split("&") if "=" in p)

        # Combinar defaults con lo que llego
        p = {**VENTA_DEFAULT, **params}
        tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"

        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"tx_id={tx_id}\n".encode())

        print(f"\n[COORDINADOR] ══ INICIO TRANSACCION {tx_id} ══", flush=True)
        print(f"[COORDINADOR] Venta: med_id={p['medicamento_id']} x{p['cantidad']} | cliente={p['cliente']} | total={p['total']}", flush=True)

        payload_inv = f"tx_id={tx_id}&medicamento_id={p['medicamento_id']}&cantidad={p['cantidad']}".encode()
        payload_fac = f"tx_id={tx_id}&cliente={p['cliente']}&total={p['total']}".encode()

        # ── FASE 1: PREPARE ──────────────────────────────────────
        print(f"\n[COORDINADOR] ── FASE 1: PREPARE ──", flush=True)
        ok_inv, _ = enviar(f"{INV_BASE}/prepare", "Inventario",  "PREPARE", payload_inv)
        ok_fac, _ = enviar(f"{FAC_BASE}/prepare", "Facturacion", "PREPARE", payload_fac)

        todos_ok = ok_inv and ok_fac

        if not todos_ok:
            print(f"\n[COORDINADOR] Voto negativo detectado — iniciando ABORT global", flush=True)
            if ok_inv: enviar(f"{INV_BASE}/rollback",  "Inventario",  "ROLLBACK", f"tx_id={tx_id}".encode())
            if ok_fac: enviar(f"{FAC_BASE}/rollback",  "Facturacion", "ROLLBACK", f"tx_id={tx_id}".encode())
            print(f"[COORDINADOR] Transaccion {tx_id} ABORTADA", flush=True)
            return

        print(f"\n[COORDINADOR] Todos votaron YES. Todos los recursos estan BLOQUEADOS.", flush=True)

        # ── PUNTO CRITICO ────────────────────────────────────────
        if MODO_FALLO:
            print(f"\n[COORDINADOR] *** SIMULACION FALLO: coordinador cae ahora ***", flush=True)
            print(f"[COORDINADOR] Los participantes quedaran en INCERTIDUMBRE...", flush=True)
            os._exit(1)   # caida abrupta — sin enviar COMMIT

        # ── FASE 2: COMMIT ───────────────────────────────────────
        print(f"\n[COORDINADOR] ── FASE 2: COMMIT ──", flush=True)
        time.sleep(0.3)  # pequeña pausa para que se vea en la interfaz
        payload_commit = f"tx_id={tx_id}".encode()
        enviar(f"{INV_BASE}/commit", "Inventario",  "COMMIT", payload_commit)
        enviar(f"{FAC_BASE}/commit", "Facturacion", "COMMIT", payload_commit)
        print(f"\n[COORDINADOR] ══ TRANSACCION {tx_id} COMPLETADA EXITOSAMENTE ══", flush=True)

    def log_message(self, *a): pass


print(f"[COORDINADOR] Puerto 8000 | MODO_FALLO={MODO_FALLO}", flush=True)
server = HTTPServer(("0.0.0.0", 8000), CoordHandler)
server.serve_forever()
