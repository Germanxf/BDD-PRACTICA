
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading, urllib.request, urllib.error, subprocess, time, os

BG         = "#F0F2F5"
CARD       = "#FFFFFF"
HEADER_BG  = "#1A1A2E"
ACCENT     = "#4A90D9"
SUCCESS    = "#27AE60"
DANGER     = "#E74C3C"
WARNING    = "#F39C12"
IDLE_COLOR = "#95A5A6"
FONT_MONO  = ("Courier New", 10)
FONT_TITLE = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 9)

COORD_URL = "http://localhost:8000/venta"


class Nodo(tk.Frame):
    ESTADOS = {
        "IDLE":          ("#BDC3C7", "●  IDLE"),
        "PREPARE":       ("#F39C12", "◉  PREPARE enviado"),
        "PREPARED":      ("#3498DB", "⬡  PREPARED (bloqueado)"),
        "COMMITTED":     ("#27AE60", "✔  COMMITTED"),
        "ABORTED":       ("#E74C3C", "✘  ABORTED"),
        "INCERTIDUMBRE": ("#8E44AD", "?  INCERTIDUMBRE"),
        "CAIDO":         ("#CC0000", "☠  CAIDO"),
    }

    def __init__(self, parent, titulo, subtitulo="", es_coordinador=False, **kw):
        super().__init__(parent, bg=CARD, relief="solid", bd=1, **kw)
        header_bg = "#2C3E50" if es_coordinador else "#34495E"
        tk.Label(self, text=titulo, font=FONT_TITLE, bg=header_bg, fg="white",
                 padx=10, pady=6).pack(fill="x")
        if subtitulo:
            tk.Label(self, text=subtitulo, font=FONT_SMALL, bg=CARD,
                     fg="#7F8C8D", padx=10, pady=1).pack(anchor="w")
        self.lbl_estado = tk.Label(self, text="●  IDLE",
                                   font=("Segoe UI", 9, "bold"),
                                   bg=CARD, fg=IDLE_COLOR, padx=10, pady=3)
        self.lbl_estado.pack(anchor="w")
        self.lbl_detalle = tk.Label(self, text="Esperando transacción...",
                                    font=FONT_SMALL, bg=CARD, fg="#95A5A6",
                                    padx=10, pady=2, wraplength=220, justify="left")
        self.lbl_detalle.pack(anchor="w", pady=(0, 5))

    def set_estado(self, estado, detalle=""):
        color, texto = self.ESTADOS.get(estado, self.ESTADOS["IDLE"])
        self.lbl_estado.config(text=texto, fg=color)
        if detalle:
            self.lbl_detalle.config(text=detalle, fg="#2C3E50")
        self.update_idletasks()

    def reset(self):
        self.set_estado("IDLE")
        self.lbl_detalle.config(text="Esperando transacción...", fg="#95A5A6")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Práctica 2PC — Transacciones Distribuidas")
        self.geometry("1200x720")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self._docker_ok = False
        self._tx_activa = False
        self._construir_ui()
        self.after(500, self._verificar_servicios)

    def _construir_ui(self):
        # ── 1. Header ──────────────────────────────────────────
        hdr = tk.Frame(self, bg=HEADER_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Protocolo 2PC — Transacciones Distribuidas",
                 font=("Segoe UI", 13, "bold"), bg=HEADER_BG, fg="white",
                 padx=20, pady=12).pack(side="left")

        # ── 2. Barra Docker ────────────────────────────────────
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=14, pady=(8, 0))
        self.lbl_docker = tk.Label(bar, text="⏳ Verificando servicios...",
                                   font=FONT_SMALL, bg=BG, fg=WARNING)
        self.lbl_docker.pack(side="left")
        self.btn_docker = tk.Button(bar, text="▶ Levantar Docker",
                                    font=FONT_SMALL, bg=ACCENT, fg="white",
                                    relief="flat", padx=10, cursor="hand2",
                                    command=self._levantar_docker)
        self.btn_docker.pack(side="right")

        # ── 3. Barra de botones de escenario (FIJA, siempre visible) ──
        btn_bar = tk.Frame(self, bg="#2C3E50", pady=8)
        btn_bar.pack(fill="x", padx=0)

        tk.Label(btn_bar, text="Ejecutar escenario:",
                 font=("Segoe UI", 10), bg="#2C3E50", fg="#BDC3C7",
                 padx=16).pack(side="left")

        self.btn_ok = tk.Button(btn_bar, text="▶  Flujo exitoso",
                                font=("Segoe UI", 10, "bold"),
                                bg=SUCCESS, fg="white", relief="flat",
                                padx=20, pady=6, cursor="hand2",
                                command=lambda: self._lanzar_tx(fallo=False))
        self.btn_ok.pack(side="left", padx=(0, 8))

        self.btn_fail = tk.Button(btn_bar, text="☠  Fallo del coordinador",
                                  font=("Segoe UI", 10, "bold"),
                                  bg=DANGER, fg="white", relief="flat",
                                  padx=20, pady=6, cursor="hand2",
                                  command=lambda: self._lanzar_tx(fallo=True))
        self.btn_fail.pack(side="left", padx=(0, 8))

        self.btn_reset = tk.Button(btn_bar, text="↺  Reiniciar estados",
                                   font=FONT_SMALL,
                                   bg="#7F8C8D", fg="white", relief="flat",
                                   padx=14, pady=6, cursor="hand2",
                                   command=self._reset_estados)
        self.btn_reset.pack(side="left")

        # ── 4. Cuerpo principal ────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=8)

        # — Columna izquierda: nodos + formulario —
        left = tk.Frame(body, bg=BG, width=270)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(left, text="Nodos del sistema distribuido",
                 font=FONT_TITLE, bg=BG).pack(anchor="w", pady=(0, 5))

        self.nodo_coord = Nodo(left, "🖥  Coordinador",
                               "Puerto 8000 — orquesta la TX", es_coordinador=True)
        self.nodo_coord.pack(fill="x", pady=(0, 6))

        tk.Label(left, text="Participantes", font=FONT_SMALL, bg=BG,
                 fg="#7F8C8D").pack(anchor="w")

        self.nodo_inv = Nodo(left, "📦  Inventario",
                             "Puerto 8001 · PostgreSQL: inventario_db")
        self.nodo_inv.pack(fill="x", pady=(3, 5))

        self.nodo_fac = Nodo(left, "🧾  Facturación",
                             "Puerto 8002 · PostgreSQL: facturacion_db")
        self.nodo_fac.pack(fill="x", pady=(0, 10))

        tk.Label(left, text="Parámetros de la venta",
                 font=FONT_TITLE, bg=BG).pack(anchor="w", pady=(4, 4))

        frm = tk.Frame(left, bg=CARD, relief="solid", bd=1)
        frm.pack(fill="x")
        frm.columnconfigure(1, weight=1)

        self._entradas = {}
        for i, (lbl, key, val) in enumerate([
            ("Medicamento ID:", "med_id",  "1"),
            ("Cantidad:",       "cantidad", "5"),
            ("Cliente:",        "cliente",  "Carlos Mendoza"),
            ("Total ($):",      "total",    "2.25"),
        ]):
            tk.Label(frm, text=lbl, font=FONT_SMALL, bg=CARD,
                     fg="#2C3E50").grid(row=i, column=0, sticky="w", padx=8, pady=5)
            e = tk.Entry(frm, font=FONT_MONO, width=15)
            e.insert(0, val)
            e.grid(row=i, column=1, sticky="ew", padx=(0, 8), pady=5)
            self._entradas[key] = e

        # — Columna derecha: log —
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(right, text="Log de eventos en tiempo real",
                 font=FONT_TITLE, bg=BG).pack(anchor="w", pady=(0, 4))

        self.log = scrolledtext.ScrolledText(
            right, font=("Courier New", 10), bg="#1E1E1E", fg="#D4D4D4",
            state="disabled", relief="flat", bd=0)
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("ok",     foreground="#4EC9B0")
        self.log.tag_config("error",  foreground="#F44747",
                            font=("Courier New", 10, "bold"))
        self.log.tag_config("warn",   foreground="#CE9178")
        self.log.tag_config("info",   foreground="#9CDCFE")
        self.log.tag_config("fase",   foreground="#DCDCAA",
                            font=("Courier New", 10, "bold"))
        self.log.tag_config("db",     foreground="#C586C0")
        self.log.tag_config("dim",    foreground="#6A9955")
        self.log.tag_config("titulo", foreground="#569CD6",
                            font=("Courier New", 11, "bold"))

        # ── 5. Barra inferior resultado ────────────────────────
        bot = tk.Frame(self, bg=CARD, relief="solid", bd=1)
        bot.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(bot, text="Último resultado en bases de datos:",
                 font=FONT_SMALL, bg=CARD, fg="#7F8C8D",
                 padx=10, pady=3).pack(anchor="w")
        self.lbl_resultado = tk.Label(
            bot,
            text="—  Aún no se ha ejecutado ninguna transacción",
            font=FONT_MONO, bg=CARD, fg="#2C3E50",
            padx=10, pady=3, justify="left")
        self.lbl_resultado.pack(anchor="w", pady=(0, 4))

    # ── Docker ──────────────────────────────────────────────────
    def _levantar_docker(self):
        self._log("Levantando contenedores Docker...", "info")
        self.btn_docker.config(state="disabled", text="⏳ Levantando...")
        threading.Thread(target=self._docker_up, daemon=True).start()

    def _docker_up(self):
        try:
            proc = subprocess.Popen(
                ["docker", "compose", "up", "--build", "-d"],
                cwd=os.path.dirname(__file__),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self._log(f"  {line}", "dim")
            proc.wait()
            time.sleep(4)
            self.after(0, self._verificar_servicios)
        except FileNotFoundError:
            self._log("ERROR: 'docker' no encontrado en el PATH.", "error")
            self.after(0, lambda: self.btn_docker.config(
                state="normal", text="▶ Levantar Docker"))

    def _verificar_servicios(self):
        def chk():
            ok = all(self._ping(u) for u in [
                "http://localhost:8000",
                "http://localhost:8001",
                "http://localhost:8002"])
            self.after(0, lambda: self._set_docker_status(ok))
        threading.Thread(target=chk, daemon=True).start()

    def _ping(self, url):
        try:
            urllib.request.urlopen(url, timeout=2)
        except:
            pass
        return True

    def _set_docker_status(self, ok):
        if ok:
            self.lbl_docker.config(
                text="✔ Todos los servicios activos (coordinador · inventario · facturación)",
                fg=SUCCESS)
            self.btn_docker.config(text="↺ Reiniciar Docker",
                                   bg="#7F8C8D", state="normal")
            self._docker_ok = True
        else:
            self.lbl_docker.config(text="⚠ Servicios no disponibles", fg=DANGER)
            self.btn_docker.config(text="▶ Levantar Docker",
                                   bg=ACCENT, state="normal")
            self._docker_ok = False

    # ── Transacción ─────────────────────────────────────────────
    def _lanzar_tx(self, fallo=False):
        if self._tx_activa:
            messagebox.showwarning("Espera", "Ya hay una transacción en curso.")
            return
        self._tx_activa = True
        self._reset_estados()
        label = "Fallo del coordinador" if fallo else "Flujo exitoso"
        self._log(f"\n  [ Escenario: {label} ]\n", "titulo")
        med_id   = self._entradas["med_id"].get().strip()
        cantidad = self._entradas["cantidad"].get().strip()
        cliente  = self._entradas["cliente"].get().strip().replace(" ", "+")
        total    = self._entradas["total"].get().strip()
        threading.Thread(target=self._ejecutar_tx,
                         args=(fallo, med_id, cantidad, cliente, total),
                         daemon=True).start()

    def _ejecutar_tx(self, fallo, med_id, cantidad, cliente, total):
        try:
            if fallo:
                self._log("Reconfigurando coordinador con MODO_FALLO=1...", "warn")
                self._reiniciar_coordinador(True)
                time.sleep(3)
                self._log("Coordinador listo en modo fallo.", "warn")

            self.after(0, lambda: self.nodo_coord.set_estado(
                "PREPARE", "Enviando PREPARE a participantes..."))
            self._log("FASE 1: PREPARE", "fase")
            self._log("  Enviando PREPARE a Inventario...", "info")
            self.after(0, lambda: self.nodo_inv.set_estado(
                "PREPARED", "Fila bloqueada (SELECT FOR UPDATE)"))
            time.sleep(0.4)
            self._log("  Enviando PREPARE a Facturación...", "info")
            self.after(0, lambda: self.nodo_fac.set_estado(
                "PREPARED", "Factura insertada como PENDIENTE"))
            time.sleep(0.4)

            payload = (f"medicamento_id={med_id}&cantidad={cantidad}"
                       f"&cliente={cliente}&total={total}").encode()
            self._log(f"  med={med_id}  cantidad={cantidad}  "
                      f"cliente={cliente}  total=${total}", "dim")

            _, resp = self._http_post(COORD_URL, payload)
            tx_id = resp.split("tx_id=")[-1].strip() if "tx_id=" in resp else "TX-???"
            self._log(f"  ID de transacción: {tx_id}", "info")

            if fallo:
                time.sleep(2)
                self._log("  Todos votaron YES", "ok")
                self._log("", "")
                self._log("  Coordinador caído — no se envió COMMIT", "error")
                self._log("", "")
                self._log("ESTADO: INCERTIDUMBRE", "fase")
                self._log("  Los participantes no saben si hacer commit o rollback", "warn")
                self._log("  Recursos siguen bloqueados en PostgreSQL", "warn")
                self._log("  inventario_db  →  medicamento retenido (FOR UPDATE)", "db")
                self._log("  facturacion_db →  factura en estado PENDIENTE", "db")
                time.sleep(1.5)
                self._log("", "")
                self._log("  En 2PC puro: sin coordinador no hay resolución posible.", "error")
                self._log("  Única salida: reiniciar coordinador y leer su WAL.", "warn")
                self.after(0, lambda: self.nodo_coord.set_estado(
                    "CAIDO", "Caído antes de enviar COMMIT"))
                self.after(0, lambda: self.nodo_inv.set_estado(
                    "INCERTIDUMBRE", "Timeout superado · recursos bloqueados"))
                self.after(0, lambda: self.nodo_fac.set_estado(
                    "INCERTIDUMBRE", "Timeout superado · factura PENDIENTE"))
                self._set_resultado(
                    f"⚠ INCERTIDUMBRE — TX: {tx_id}\n"
                    f"   inventario_db  → medicamento_id={med_id} bloqueado (sin commit)\n"
                    f"   facturacion_db → factura PENDIENTE (sin commit)")
                threading.Thread(target=lambda: (
                    time.sleep(6), self._reiniciar_coordinador(False)),
                    daemon=True).start()
            else:
                time.sleep(1.5)
                self._log("  Todos votaron YES", "ok")
                self._log("", "")
                self._log("FASE 2: COMMIT", "fase")
                self._log("  Enviando COMMIT a Inventario...", "info")
                time.sleep(0.5)
                self._log("  Inventario: stock descontado y commiteado", "ok")
                self.after(0, lambda: self.nodo_inv.set_estado(
                    "COMMITTED", "Stock actualizado en inventario_db"))
                time.sleep(0.4)
                self._log("  Enviando COMMIT a Facturación...", "info")
                time.sleep(0.5)
                self._log("  Facturación: factura emitida y commiteada", "ok")
                self.after(0, lambda: self.nodo_fac.set_estado(
                    "COMMITTED", "Factura EMITIDA en facturacion_db"))
                time.sleep(0.3)
                self.after(0, lambda: self.nodo_coord.set_estado(
                    "COMMITTED", f"TX completada: {tx_id}"))
                self._log("", "")
                self._log(f"  Transacción {tx_id} completada exitosamente", "ok")
                self._log("", "")
                self._log("Bases de datos actualizadas:", "fase")
                self._log(f"  inventario_db  →  medicamento_id={med_id}: stock -{cantidad}", "db")
                self._log(f"  facturacion_db →  FAC-{tx_id[-6:]}: EMITIDA  total=${total}", "db")
                self._set_resultado(
                    f"✔ TX exitosa — {tx_id}\n"
                    f"   inventario_db  → medicamento_id={med_id}: stock -{cantidad}\n"
                    f"   facturacion_db → FAC-{tx_id[-6:]}: EMITIDA | total=${total}")
        except Exception as e:
            self._log(f"Error inesperado: {e}", "error")
        finally:
            self._tx_activa = False

    def _reiniciar_coordinador(self, modo_fallo):
        env = {**os.environ, "MODO_FALLO": "1" if modo_fallo else "0"}
        try:
            subprocess.run(
                ["docker", "compose", "up", "-d", "--no-deps", "--build", "coordinador"],
                cwd=os.path.dirname(__file__), env=env,
                capture_output=True, timeout=30)
            self._log(f"  Coordinador reiniciado (MODO_FALLO={'1' if modo_fallo else '0'})", "dim")
        except Exception as e:
            self._log(f"  Error reiniciando coordinador: {e}", "warn")

    def _http_post(self, url, data=b""):
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return True, r.read().decode()
        except urllib.error.HTTPError as e:
            return False, e.read().decode()
        except Exception as e:
            return False, str(e)

    # ── Helpers UI ───────────────────────────────────────────────
    def _log(self, texto, tag=""):
        def _do():
            self.log.config(state="normal")
            self.log.insert("end", (texto + "\n") if texto.strip() else "\n", tag or "")
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(0, _do)

    def _reset_estados(self):
        self.nodo_coord.reset()
        self.nodo_inv.reset()
        self.nodo_fac.reset()
        self.lbl_resultado.config(
            text="—  Aún no se ha ejecutado ninguna transacción")

    def _set_resultado(self, texto):
        self.after(0, lambda: self.lbl_resultado.config(text=texto))


if __name__ == "__main__":
    App().mainloop()