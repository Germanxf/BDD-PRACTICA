import sys, time, threading, psycopg2, os
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT     = int(os.environ.get("PORT", 8001))
NAME     = os.environ.get("NAME", "Inventario")
DB_HOST  = os.environ.get("DB_HOST", "localhost")
DB_NAME  = os.environ.get("DB_NAME", "inventario_db")
DB_USER  = os.environ.get("DB_USER", "postgres")
DB_PASS  = os.environ.get("DB_PASS", "postgres")

TIMEOUT  = 8   # segundos esperando decision del coordinador

estado          = "IDLE"
tiempo_prepare  = 0
conn_preparada  = None   # conexion con tx abierta (bloqueando recursos)
cur_preparada   = None


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

def log_bd(tx_id, fase, est, detalle):
    try:
        c = get_conn()
        cur = c.cursor()
        cur.execute(
            "INSERT INTO transacciones_log (transaccion_id,fase,estado,detalle) VALUES (%s,%s,%s,%s)",
            (tx_id, fase, est, detalle)
        )
        c.commit(); c.close()
    except Exception as e:
        print(f"[{NAME}] LOG-ERROR: {e}", flush=True)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        global estado, tiempo_prepare, conn_preparada, cur_preparada

        length   = int(self.headers.get("Content-Length", 0))
        body     = self.rfile.read(length).decode() if length else ""
        # Parsear tx_id y parametros del body  (formato: tx_id=X&medicamento_id=Y&cantidad=Z)
        params   = dict(p.split("=") for p in body.split("&") if "=" in p)
        tx_id    = params.get("tx_id", "TX-?")
        med_id   = int(params.get("medicamento_id", 1))
        cantidad = int(params.get("cantidad", 1))

        # ── PREPARE ──────────────────────────────────────────────
        if self.path == "/prepare":
            print(f"\n[{NAME}] PREPARE recibido (tx={tx_id})", flush=True)
            try:
                conn_preparada = get_conn()
                conn_preparada.autocommit = False
                cur_preparada  = conn_preparada.cursor()

                # Bloquear la fila con SELECT FOR UPDATE (bloqueo real en PG)
                cur_preparada.execute(
                    "SELECT id, nombre, stock FROM medicamentos WHERE id=%s FOR UPDATE",
                    (med_id,)
                )
                row = cur_preparada.fetchone()
                if not row:
                    raise Exception(f"Medicamento id={med_id} no existe")

                _, nombre, stock_actual = row
                if stock_actual < cantidad:
                    raise Exception(f"Stock insuficiente: tiene {stock_actual}, necesita {cantidad}")

                # Ejecutar el UPDATE (no commit aun — recursos bloqueados)
                cur_preparada.execute(
                    "UPDATE medicamentos SET stock = stock - %s WHERE id = %s",
                    (cantidad, med_id)
                )
                log_bd(tx_id, "PREPARE", "PREPARED",
                       f"Fila bloqueada: {nombre} | stock {stock_actual} -> {stock_actual-cantidad}")

                estado = "PREPARED"
                tiempo_prepare = time.time()
                print(f"[{NAME}] VOTE_COMMIT — fila '{nombre}' bloqueada en PG (sin commit)", flush=True)

                self.send_response(200); self.end_headers()
                self.wfile.write(b"VOTE_COMMIT")

            except Exception as e:
                print(f"[{NAME}] VOTE_ABORT — {e}", flush=True)
                if conn_preparada:
                    try: conn_preparada.rollback(); conn_preparada.close()
                    except: pass
                conn_preparada = None
                estado = "IDLE"
                self.send_response(500); self.end_headers()
                self.wfile.write(f"VOTE_ABORT:{e}".encode())

        # ── COMMIT ───────────────────────────────────────────────
        elif self.path == "/commit":
            print(f"\n[{NAME}] COMMIT recibido (tx={tx_id})", flush=True)
            try:
                conn_preparada.commit()
                conn_preparada.close()
                conn_preparada = None
                estado = "COMMITTED"
                log_bd(tx_id, "COMMIT", "COMMITTED", "Stock descontado y persistido en disco")
                print(f"[{NAME}] COMMITTED — cambios en PG confirmados", flush=True)
                self.send_response(200); self.end_headers()
                self.wfile.write(b"ACK_COMMIT")
            except Exception as e:
                print(f"[{NAME}] ERROR en commit: {e}", flush=True)
                self.send_response(500); self.end_headers()

        # ── ROLLBACK ─────────────────────────────────────────────
        elif self.path == "/rollback":
            print(f"\n[{NAME}] ROLLBACK recibido (tx={tx_id})", flush=True)
            try:
                if conn_preparada:
                    conn_preparada.rollback()
                    conn_preparada.close()
                    conn_preparada = None
                estado = "ABORTED"
                log_bd(tx_id, "ROLLBACK", "ABORTED", "Bloqueo liberado — stock sin modificar")
                print(f"[{NAME}] ABORTED — rollback completado, bloqueo liberado", flush=True)
                self.send_response(200); self.end_headers()
                self.wfile.write(b"ACK_ROLLBACK")
            except Exception as e:
                print(f"[{NAME}] ERROR en rollback: {e}", flush=True)
                self.send_response(500); self.end_headers()

    def log_message(self, *a): pass


def monitor_timeout():
    global estado
    while True:
        time.sleep(2)
        if estado == "PREPARED" and (time.time() - tiempo_prepare) > TIMEOUT:
            print(f"\n[{NAME}] ⚠ TIMEOUT — coordinador no responde.", flush=True)
            print(f"[{NAME}] ESTADO: INCERTIDUMBRE — recursos BLOQUEADOS en PG", flush=True)
            # En 2PC puro NO podemos hacer nada sin saber la decision del coordinador
            time.sleep(10)


print(f"[{NAME}] Iniciando en puerto {PORT} | BD={DB_NAME}@{DB_HOST}", flush=True)
threading.Thread(target=monitor_timeout, daemon=True).start()
server = HTTPServer(("0.0.0.0", PORT), Handler)
server.serve_forever()
