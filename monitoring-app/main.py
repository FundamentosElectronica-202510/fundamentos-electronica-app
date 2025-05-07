import os
import platform
import subprocess
import sys

import serial
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# ----------------------------- Serial settings ----------------------------- #
PORT = '/dev/tty.usbserial-2110'  # <- Update to match your Arduino port
BAUD = 9600

# ------------------------------ Thresholds --------------------------------- #
POSTURE_THRESHOLD = 220  # flex sensor raw value – > choose empirically
PULSE_MIN = 50  # bpm lower bound for a resting adult
PULSE_MAX = 110  # bpm upper bound for a resting adult
SWEAT_THRESHOLD = 600  # larger raw value ⇒ more sweat (set experimentally)

# A simple mapping from “how many sensors are currently in warning” to a
# Spanish‑language stress level. Adjust to your project needs.
STRESS_LEVELS = {
    0: "Bajo",
    1: "Medio",
    2: "Alto",
    3: "Alto"
}


# --------------------------------------------------------------------------- #

def is_macos_dark_mode() -> bool:
    """Return True if macOS is in dark mode (used only for label colours)."""
    if platform.system() != "Darwin":
        return False
    try:
        p = subprocess.Popen(
            "defaults read -g AppleInterfaceStyle",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        stdout, _ = p.communicate()
        return stdout.decode().strip() == "Dark"
    except Exception:
        return False


class FlexMonitorGUI:
    """Tkinter GUI that shows live data coming from several Arduino sensors."""

    # ──────────────────────────── Init / Layout ──────────────────────────── #

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Monitor de sensores – Fundamentos de Electrónica")
        self.root.attributes("-topmost", True)

        self.text_colour = "white" if is_macos_dark_mode() else "black"

        # Window dimensions and centering
        w, h = 520, 480
        self.root.minsize(w, h)
        _sx, _sy = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{_sx // 2 - w // 2}+{_sy // 2 - h // 2}")

        # ---------------------------------------------------- Notebook layout #
        notebook = ttk.Notebook(root)
        notebook.pack(expand=True, fill="both")

        self.frames = {}
        for name in ("Postura", "Pulso", "Sudor", "BMI", "Nivel de estrés"):
            f = ttk.Frame(notebook)
            notebook.add(f, text=name)
            self.frames[name] = f

        # ------------- Widgets for each tab ------------- #
        self._build_posture_tab()
        self._build_pulse_tab()
        self._build_sweat_tab()
        self._build_bmi_tab()
        self._build_stress_tab()

        # ------------------------------------------------- State variables #
        self.height_cm: float | None = None  # captured once from HEIGHT sensor
        self.weight_kg: float | None = None

        self.warnings: dict[str, bool] = {
            "POSTURE": False,
            "PULSE": False,
            "SWEAT": False
        }

        # Thread management
        self.serial_threads: list[threading.Thread] = []
        self._start_serial_threads()

    # ─────────────────────── Build individual tabs ──────────────────────── #

    def _lbl(self, parent, text, **kwargs):
        return tk.Label(parent, text=text, fg=self.text_colour, **kwargs)

    def _build_posture_tab(self):
        f = self.frames["Postura"]
        self.posture_val_lbl = self._lbl(f, "Valor flex: --", font=("Helvetica", 18))
        self.posture_val_lbl.pack(pady=10)
        self.posture_status_lbl = self._lbl(f, "Estado: --", font=("Helvetica", 16))
        self.posture_status_lbl.pack()

    def _build_pulse_tab(self):
        f = self.frames["Pulso"]
        self.pulse_val_lbl = self._lbl(f, "Pulso: -- bpm", font=("Helvetica", 18))
        self.pulse_status_lbl = self._lbl(f, "Estado: --", font=("Helvetica", 16))
        self.pulse_val_lbl.pack(pady=10)
        self.pulse_status_lbl.pack()

    def _build_sweat_tab(self):
        f = self.frames["Sudor"]
        self.sweat_val_lbl = self._lbl(f, "Humedad: --", font=("Helvetica", 18))
        self.sweat_status_lbl = self._lbl(f, "Estado: --", font=("Helvetica", 16))
        self.sweat_val_lbl.pack(pady=10)
        self.sweat_status_lbl.pack()

    def _build_bmi_tab(self):
        f = self.frames["BMI"]

        self.bmi_height_lbl = self._lbl(f, "Altura: -- cm (sensor)", font=("Helvetica", 14))
        self.bmi_height_lbl.pack(pady=(15, 5))

        weight_frame = ttk.Frame(f)
        weight_frame.pack(pady=5)
        ttk.Label(weight_frame, text="Peso (kg):").pack(side="left", padx=(0, 6))
        self.weight_entry = ttk.Entry(weight_frame, width=8)
        self.weight_entry.pack(side="left")
        ttk.Button(weight_frame, text="Calcular BMI", command=self._calculate_bmi).pack(side="left", padx=6)

        self.bmi_result_lbl = self._lbl(f, "BMI: --", font=("Helvetica", 16))
        self.bmi_result_lbl.pack(pady=10)

    def _build_stress_tab(self):
        f = self.frames["Nivel de estrés"]
        self.stress_lbl = self._lbl(f, "Nivel de estrés: --", font=("Helvetica", 20))
        self.stress_lbl.pack(expand=True)

    # ─────────────────────────── Serial threads ─────────────────────────── #

    def _start_serial_threads(self):
        for target in (self._read_posture, self._read_pulse, self._read_height,
                       self._read_sweat):
            t = threading.Thread(target=target, daemon=True)
            t.start()
            self.serial_threads.append(t)

    # Individual reader loops ------------------------------------------------ #

    def _read_posture(self):
        try:
            with serial.Serial(PORT, BAUD, timeout=1) as ser:
                while True:
                    line = ser.readline().decode(errors="ignore").strip()
                    if line.startswith("flex value"):
                        try:
                            value = int(line.split(";")[1])
                            self.root.after(0, self._update_posture, value)
                        except (IndexError, ValueError):
                            continue
        except serial.SerialException as e:
            self._show_error(e)

    def _read_pulse(self):
        try:
            with serial.Serial(PORT, BAUD, timeout=1) as ser:
                while True:
                    line = ser.readline().decode(errors="ignore").strip()
                    if line.startswith("pulse value"):
                        try:
                            value = int(line.split(";")[1])
                            self.root.after(0, self._update_pulse, value)
                        except (IndexError, ValueError):
                            continue
        except serial.SerialException as e:
            self._show_error(e)

    def _read_height(self):
        """Height is captured *once* – ignore further messages afterward."""
        try:
            with serial.Serial(PORT, BAUD, timeout=1) as ser:
                while self.height_cm is None:
                    line = ser.readline().decode(errors="ignore").strip()
                    if line.startswith("height value"):
                        try:
                            value = int(line.split(";")[1])
                            self.root.after(0, self._update_height_once, value)
                        except (IndexError, ValueError):
                            continue
        except serial.SerialException as e:
            self._show_error(e)

    def _read_sweat(self):
        try:
            with serial.Serial(PORT, BAUD, timeout=1) as ser:
                while True:
                    line = ser.readline().decode(errors="ignore").strip()
                    if line.startswith("sweat value"):
                        try:
                            value = int(line.split(";")[1])
                            self.root.after(0, self._update_sweat, value)
                        except (IndexError, ValueError):
                            continue
        except serial.SerialException as e:
            self._show_error(e)

    # ───────────────────────────── GUI updates ───────────────────────────── #

    def _update_posture(self, value: int):
        self.posture_val_lbl.config(text=f"Valor flex: {value}")
        correct = value >= POSTURE_THRESHOLD
        self.posture_status_lbl.config(
            text="Correcto" if correct else "Incorrecto",
            fg="green" if correct else "red"
        )
        self.warnings["POSTURE"] = not correct
        self._update_stress_level()

    def _update_pulse(self, bpm: int):
        self.pulse_val_lbl.config(text=f"Pulso: {bpm} bpm")
        correct = PULSE_MIN <= bpm <= PULSE_MAX
        self.pulse_status_lbl.config(
            text="Normal" if correct else "Fuera de rango",
            fg="green" if correct else "red"
        )
        self.warnings["PULSE"] = not correct
        self._update_stress_level()

    def _update_height_once(self, value: int):
        # value expected in centimetres from ultrasonic sensor
        self.height_cm = value
        self.bmi_height_lbl.config(text=f"Altura: {value} cm (sensor)")
        # Trigger a BMI recalculation if weight already entered
        self._calculate_bmi()

    def _update_sweat(self, value: int):
        self.sweat_val_lbl.config(text=f"Humedad: {value}")
        correct = value < SWEAT_THRESHOLD
        self.sweat_status_lbl.config(
            text="Normal" if correct else "Alta",
            fg="green" if correct else "red"
        )
        self.warnings["SWEAT"] = not correct
        self._update_stress_level()

    # BMI – invoked by button or when height arrives ------------------------ #

    def _calculate_bmi(self):
        if self.height_cm is None:
            return  # Wait until height sensor delivers a value
        try:
            weight_txt = self.weight_entry.get().strip()
            self.weight_kg = float(weight_txt) if weight_txt else None
        except ValueError:
            messagebox.showerror("Entrada incorrecta", "Ingrese un valor válido para el peso.")
            return

        if self.weight_kg is None:
            return

        h_m = self.height_cm / 100.0
        bmi = self.weight_kg / (h_m ** 2)
        self.bmi_result_lbl.config(text=f"BMI: {bmi:.1f}")

    # Stress level ---------------------------------------------------------- #

    def _update_stress_level(self):
        n_warn = sum(self.warnings.values())
        level = STRESS_LEVELS.get(n_warn, "Alto")
        colour = "green" if level == "Bajo" else ("orange" if level == "Medio" else "red")
        self.stress_lbl.config(text=f"Nivel de estrés: {level}", fg=colour)

    # ───────────────────────────── Error view ────────────────────────────── #

    def _show_error(self, exc: Exception):
        # Called from a thread; use after() to show in main loop
        self.root.after(0, self._render_error, str(exc))

    def _render_error(self, msg: str):
        for w in self.root.winfo_children():
            w.destroy()
        self._lbl(self.root, "No se detectó el dispositivo.\nVerifica la conexión.",
                  font=("Helvetica", 16)).pack(expand=True)
        ttk.Button(self.root, text="Reintentar", command=self._restart).pack(pady=12)

    def _restart(self):
        # Completely restart the program (quick and dirty)
        python = sys.executable
        os.execl(python, python, *sys.argv)


# ──────────────────────────────── Main ───────────────────────────────────── #

if __name__ == "__main__":
    root = tk.Tk()
    FlexMonitorGUI(root)
    root.mainloop()
