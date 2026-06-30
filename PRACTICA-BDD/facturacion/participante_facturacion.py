import sys, time, threading, psycopg2, os, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT     = int(os.environ.get("PORT", 8002))
NAME     = os.environ.get("NAME", "Facturacion")
DB_HOST  = os.environ.get("DB_HOST", "localhost")
DB_NAME  = os.environ.get("DB_NAME", "facturacion_db")
DB_USER  = os.environ.get("DB_USER", "postgres")
DB_PASS  = os.environ.get("DB_PASS", "postgres")

TIMEOUT  = 8

estado         = "IDLE"
tiempo_prepare = 0
conn_preparada = None
cur_preparada  = None
num_factura_tmp = None


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
        global estado, tiempo_prepare, conn_preparada, cur_preparada, num_factura_tmp

        length  = int(self.headers.get("Content-Length", 0))
        body    = self.rfile.read(length).decode() if length else ""
        params  = dict(p.split("=") for p in body.split("&") if "=" in p)
        tx_id   = params.get("tx_id", "TX-?")
        cliente = params.get("cliente", "Cliente Generico").replace("+", " ")
        total   = float(params.get("total", "10.00"))

        if self.path == "/prepare":
            print(f"\n[{NAME}] PREPARE recibido (tx={tx_id})", flush=True)
            try:
                conn_preparada = get_conn()
                conn_preparada.autocommit = False
                cur_preparada  = conn_preparada.cursor()

                # Generar numero de factura
                num_factura_tmp = f"FAC-{tx_id[-6:]}"
                subtotal = round(total / 1.12, 2)
                iva      = round(total - subtotal, 2)

                # INSERT en estado PENDIENTE — fila bloqueada con FOR UPDATE
                cur_preparada.execute(
                    """INSERT INTO facturas (numero_factura, cliente, subtotal, iva, total, estado)
                       VALUES (%s, %s, %s, %s, %s, 'PENDIENTE')
                       RETURNING id""",
                    (num_factura_tmp, cliente, subtotal, iva, total)
                )
                fac_id = cur_preparada.fetchone()[0]

                # Bloquear la fila recien insertada
                cur_preparada.execute("SELECT id FROM facturas WHERE id=%s FOR UPDATE", (fac_id,))

                log_bd(tx_id, "PREPARE", "PREPARED",
                       f"Factura {num_factura_tmp} creada PENDIENTE | total={total} | fila bloqueada")

                estado = "PREPARED"
                tiempo_prepare = time.time()
                print(f"[{NAME}] VOTE_COMMIT — factura {num_factura_tmp} insertada (sin commit)", flush=True)

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

        elif self.path == "/commit":
            print(f"\n[{NAME}] COMMIT recibido (tx={tx_id})", flush=True)
            try:
                # Actualizar estado a EMITIDA antes de confirmar
                cur_preparada.execute(
                    "UPDATE facturas SET estado='EMITIDA' WHERE numero_factura=%s",
                    (num_factura_tmp,)
                )
                conn_preparada.commit()
                conn_preparada.close()
                conn_preparada = None
                estado = "COMMITTED"
                log_bd(tx_id, "COMMIT", "COMMITTED", f"Factura {num_factura_tmp} EMITIDA y persistida")
                print(f"[{NAME}] COMMITTED — factura {num_factura_tmp} EMITIDA en disco", flush=True)
                self.send_response(200); self.end_headers()
                self.wfile.write(b"ACK_COMMIT")
            except Exception as e:
                print(f"[{NAME}] ERROR commit: {e}", flush=True)
                self.send_response(500); self.end_headers()

        elif self.path == "/rollback":
            print(f"\n[{NAME}] ROLLBACK recibido (tx={tx_id})", flush=True)
            try:
                if conn_preparada:
                    conn_preparada.rollback()
                    conn_preparada.close()
                    conn_preparada = None
                estado = "ABORTED"
                log_bd(tx_id, "ROLLBACK", "ABORTED", f"Factura {num_factura_tmp} descartada — rollback")
                print(f"[{NAME}] ABORTED — rollback completado", flush=True)
                self.send_response(200); self.end_headers()
                self.wfile.write(b"ACK_ROLLBACK")
            except Exception as e:
                print(f"[{NAME}] ERROR rollback: {e}", flush=True)
                self.send_response(500); self.end_headers()

    def log_message(self, *a): pass


def monitor_timeout():
    global estado
    while True:
        time.sleep(2)
        if estado == "PREPARED" and (time.time() - tiempo_prepare) > TIMEOUT:
            print(f"\n[{NAME}] ⚠ TIMEOUT — coordinador no responde.", flush=True)
            print(f"[{NAME}] ESTADO: INCERTIDUMBRE — factura {num_factura_tmp} BLOQUEADA", flush=True)
            time.sleep(10)


print(f"[{NAME}] Iniciando en puerto {PORT} | BD={DB_NAME}@{DB_HOST}", flush=True)
threading.Thread(target=monitor_timeout, daemon=True).start()
server = HTTPServer(("0.0.0.0", PORT), Handler)
server.serve_forever()
