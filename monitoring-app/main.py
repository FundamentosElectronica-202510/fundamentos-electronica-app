import glob
import os
import platform
import subprocess
import sys
import serial
import threading
import time
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox

# ────────────────────────────── Config ──────────────────────────────── #

import serial.tools.list_ports


def _find_esp32_bt_port() -> str | None:
    """
    Try to locate the virtual COM port that the ESP32 exposes over
    classic-Bluetooth SPP.  Strategy (in order):

    1. macOS/Linux  : look for known USB-UART nodes (/dev/ttyUSB*,
                      /dev/cu.SLAB_USBtoUART*, etc.).
    2. Windows      : choose the first port whose description mentions
                      'Bluetooth' or the Microsoft BTHENUM driver.
    3. Fallback     : first enumerated serial port (least reliable).
    """
    # 1) macOS / Linux
    patterns = (
        "/dev/ttyUSB*", "/dev/ttyACM*",  # Linux
        "/dev/cu.SLAB_USBtoUART*", "/dev/cu.usbserial*"  # macOS CP210x/FTDI
    )
    for pat in patterns:
        devs = glob.glob(pat)
        if devs:
            return devs[0]

    # 2) Windows or generic listing
    for p in serial.tools.list_ports.comports():
        if ("Bluetooth" in p.description or
                "Standard Serial over Bluetooth" in p.description or
                "BTHENUM" in p.hwid):
            return p.device

    # 3) last resort: first enumerated port
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return ports[0] if ports else None


PORT = _find_esp32_bt_port() or "COM10"  # personalise fallback if needed
BAUD = 9600  # 9600 matches the ESP32 sketch

POSTURE_THRESHOLD = 3500

PULSE_MIN, PULSE_MAX = 50, 110

# Seconds of history used to compute BPM from individual pulse events
PULSE_WINDOW = 15  # seconds
STRESS_LEVELS = {0: "Bajo", 1: "Medio", 2: "Alto", 3: "Alto"}


# ────────────────────────── Helpers / Themes ────────────────────────── #

def _is_macos_dark() -> bool:
    if platform.system() != "Darwin":
        return False
    try:
        out, _ = subprocess.Popen(
            "defaults read -g AppleInterfaceStyle",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        ).communicate()
        return out.decode().strip() == "Dark"
    except Exception:
        return False


# ────────────────────────────── GUI Class ───────────────────────────── #

class FlexMonitorGUI:
    """Tk GUI that visualises Arduino sensor data in five tabs."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Monitor de sensores – Fundamentos de Electrónica")
        self.text_colour = "white" if _is_macos_dark() else "black"

        # window size / center
        w, h = 540, 300
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{sw // 2 - w // 2}+{sh // 2 - h // 2}")
        root.minsize(w, h)
        root.attributes("-topmost", True)

        self._build_notebook()

        # sensor‑state bookkeeping
        self.height_cm: float | None = None
        self.weight_kg: float | None = None
        self.warnings = {"POSTURE": False, "PULSE": False, "SWEAT": False}
        # store timestamps of recent pulse events for BPM calculation
        self.pulse_times = deque()

        # serial thread control
        self.running = True  # pauses callbacks when False
        self.serial_thread: threading.Thread | None = None
        self._start_serial_reader()

    # ─────────────────────── Notebook / Tabs ──────────────────────── #

    def _lbl(self, parent, text, **kw):
        return tk.Label(parent, text=text, fg=self.text_colour, **kw)

    def _build_notebook(self):
        self.main_frame = tk.Frame(self.root)
        self.error_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill="both")

        nb = ttk.Notebook(self.main_frame)
        nb.pack(expand=True, fill="both")

        # create tabs
        self.frames = {}
        for name in ("Postura", "Pulso", "Sudor", "BMI", "Nivel de estrés"):
            f = ttk.Frame(nb)
            nb.add(f, text=name)
            self.frames[name] = f

        # widgets per tab
        self.posture_val_lbl = self._lbl(self.frames["Postura"], "Valor flex: --", font=("Helvetica", 18))
        self.posture_status_lbl = self._lbl(self.frames["Postura"], "Estado: --", font=("Helvetica", 16))
        self.posture_val_lbl.pack(pady=10);
        self.posture_status_lbl.pack()

        self.pulse_val_lbl = self._lbl(self.frames["Pulso"], "Pulso: -- bpm", font=("Helvetica", 18))
        self.pulse_status_lbl = self._lbl(self.frames["Pulso"], "Estado: --", font=("Helvetica", 16))
        self.pulse_val_lbl.pack(pady=10);
        self.pulse_status_lbl.pack()

        self.sweat_val_lbl = self._lbl(self.frames["Sudor"], "Humedad: --", font=("Helvetica", 18))
        self.sweat_status_lbl = self._lbl(self.frames["Sudor"], "Estado: --", font=("Helvetica", 16))
        self.sweat_val_lbl.pack(pady=10);
        self.sweat_status_lbl.pack()

        bmi_f = self.frames["BMI"]
        self.bmi_height_lbl = self._lbl(bmi_f, "Altura: -- cm (sensor)", font=("Helvetica", 14))
        self.bmi_height_lbl.pack(pady=(15, 5))
        w_frame = ttk.Frame(bmi_f);
        w_frame.pack()
        ttk.Label(w_frame, text="Peso (kg):").pack(side="left", padx=(0, 5))
        self.weight_entry = ttk.Entry(w_frame, width=8);
        self.weight_entry.pack(side="left")
        ttk.Button(w_frame, text="Calcular BMI", command=self._calc_bmi).pack(side="left", padx=6)
        self.bmi_result_lbl = self._lbl(bmi_f, "BMI: --", font=("Helvetica", 16))
        self.bmi_result_lbl.pack(pady=10)

        self.stress_lbl = self._lbl(self.frames["Nivel de estrés"], "Nivel de estrés: --", font=("Helvetica", 20))
        self.stress_lbl.pack(expand=True)

    # ────────────────────── Serial Reader (single) ─────────────────────── #

    def _start_serial_reader(self):
        self.serial_thread = threading.Thread(target=self._serial_loop, daemon=True)
        self.serial_thread.start()

    # Helper to extract int safely
    @staticmethod
    def _extract_int(line: str) -> int | None:
        try:
            val_part = line.split(";", 1)[1]
            digits = ''.join(ch for ch in val_part if ch.isdigit())
            return int(digits) if digits else None
        except (IndexError, ValueError):
            return None

    def _serial_loop(self):
        """Read the serial port once and dispatch complete lines.
        Handles concatenated lines like '742\rflex value;...' by
        keeping only the digits before non‑digit chars."""
        try:
            with serial.Serial(PORT, BAUD, timeout=1) as ser:
                while True:
                    if not self.running:
                        time.sleep(0.2);
                        continue
                    raw = ser.readline()
                    if not raw:
                        continue
                    # We may receive several lines if CRLF boundaries are odd
                    for line in raw.decode(errors="ignore").split("\n"):
                        line = line.strip()
                        if not line:
                            continue             
                        value = self._extract_int(line)
                        if value is None:
                            continue
                        if line.startswith("pulse value;"):
                            self._dispatch(self._update_pulse, value)
                        elif line.startswith("flex value;"):
                            self._dispatch(self._update_posture, value)
                        elif line.startswith("height value;") and self.height_cm is None:
                            self._dispatch(self._update_height_once, value)
                        elif line.startswith("sweat value;"):
                            self._dispatch(self._update_sweat, value)
        except serial.SerialException as e:
            self._dispatch(self._show_error, str(e))

    # helper to schedule on main loop
    def _dispatch(self, func, *args):
        if self.running and None not in args:
            self.root.after(0, func, *args)

    # ───────────────────────── GUI updaters ──────────────────────────── #

    def _update_posture(self, v: int):
        self.posture_val_lbl.config(text=f"Valor flex: {v}")
        ok = v <= POSTURE_THRESHOLD
        self.posture_status_lbl.config(text="Correcto" if ok else "Incorrecto", fg="green" if ok else "red")
        self.warnings["POSTURE"] = not ok;
        self._update_stress()

    def _update_pulse(self, bpm: int):
        """Show BPM sent by the ESP32 (“bpm value;NN”)."""
        self.pulse_val_lbl.config(text=f"Pulso: {bpm} bpm")

        ok = PULSE_MIN <= bpm <= PULSE_MAX
        self.pulse_status_lbl.config(
            text="Normal" if ok else "Fuera de rango",
            fg="green" if ok else "red"
        )
        self.warnings["PULSE"] = not ok
        self._update_stress()

    def _update_height_once(self, cm: float):
        self.height_cm = cm
        if self.bmi_height_lbl.winfo_exists():
            self.bmi_height_lbl.config(text=f"Altura: {cm} cm (sensor)")
        self._calc_bmi()

    def _update_sweat(self, v: int):
        # 0 = sweat, 1 = no sweat
        ok = v == 1
        self.sweat_val_lbl.config(text=f"Humedad: {v}... {'No se detecta sudor' if ok else 'Sudor detectado'}")
        self.sweat_status_lbl.config(text="Normal" if ok else "Alta", fg="green" if ok else "red")
        self.warnings["SWEAT"] = not ok
        self._update_stress()

    def _calc_bmi(self):
        if self.height_cm is None:
            return
        try:
            txt = self.weight_entry.get().strip()
            self.weight_kg = float(txt) if txt else None
        except ValueError:
            messagebox.showerror("Entrada incorrecta", "Ingrese un número válido para el peso.")
            return
        if self.weight_kg is None:
            return
        h_m = self.height_cm / 100.0
        bmi = self.weight_kg / (h_m ** 2)
        self.bmi_result_lbl.config(text=f"BMI: {bmi:.1f}")

    def _update_stress(self):
        n = sum(self.warnings.values())
        level = STRESS_LEVELS.get(n, "Alto")
        colour = "green" if level == "Bajo" else ("orange" if level == "Medio" else "red")
        self.stress_lbl.config(text=f"Nivel de estrés: {level}", fg=colour)

    # ─────────────────────────── Error View ──────────────────────────── #

    def _show_error(self, msg: str):
        if not self.running:
            return
        self.running = False  # pause callbacks
        self.main_frame.pack_forget()
        for w in self.error_frame.winfo_children():
            w.destroy()
        tk.Label(self.error_frame, text="No se detectó el dispositivo.\nVerifica la conexión.",
                 fg=self.text_colour, font=("Helvetica", 16)).pack(expand=True)
        ttk.Button(self.error_frame, text="Reintentar", command=self._restart).pack(pady=12)
        self.error_frame.pack(expand=True, fill="both")

    def _restart(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)


# ─────────────────────────────── Main ───────────────────────────────── #

if __name__ == "__main__":
    root = tk.Tk()
    FlexMonitorGUI(root)
    root.mainloop()
