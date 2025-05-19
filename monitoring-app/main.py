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
from numpy import random  # Assuming this is used, though not directly in the provided snippet for port logic

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
    ports_list = [p.device for p in serial.tools.list_ports.comports()]
    return ports_list[0] if ports_list else None


# Initial PORT detection or fallback
PORT = _find_esp32_bt_port() or "/dev/tty.usbserial-57250036131"  # personalise fallback if needed
BAUD = 115200  # 9600 matches the ESP32 sketch

POSTURE_THRESHOLD = 4050
PULSE_MIN, PULSE_MAX = 50, 110
PULSE_WINDOW = 15
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
    """Tk GUI that visualises Arduino sensor data in multiple tabs."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Monitor de sensores – Fundamentos de Electrónica")
        self.text_colour = "white" if _is_macos_dark() else "black"

        self.beep_active = False

        # Stress calculation
        self.I = None # BMI
        self.H = None # Humidity
        self.P = None # Pulse
        self.S = None # Posture

        w, h = 600, 380  # Adjusted size for new widgets
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{sw // 2 - w // 2}+{sh // 2 - h // 2}")
        root.minsize(w, h)
        root.attributes("-topmost", True)

        self.port_value = tk.StringVar(value=PORT)
        self.ser_instance: serial.Serial | None = None
        self.serial_thread: threading.Thread | None = None
        self.running = True

        self._build_ui()

        self.height_cm: float | None = None
        self.weight_kg: float | None = None
        self.warnings = {"POSTURE": False, "PULSE": False, "SWEAT": False}
        self.pulse_times = deque()

        self._start_serial_reader()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        self._stop_serial_thread()
        self.root.destroy()

    def _lbl(self, parent, text, **kw):
        return tk.Label(parent, text=text, fg=self.text_colour, **kw)

    def _build_ui(self):
        self.main_frame = tk.Frame(self.root)
        self.error_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill="both")

        self.nb = ttk.Notebook(self.main_frame)
        self.nb.pack(expand=True, fill="both", padx=5, pady=5)

        self.frames = {}
        for name in ("Postura", "Pulso", "Sudor", "BMI", "Nivel de estrés"):
            f = ttk.Frame(self.nb)
            self.nb.add(f, text=name)
            self.frames[name] = f

        self.frames["Configuración Puerto"] = ttk.Frame(self.nb)
        self.nb.add(self.frames["Configuración Puerto"], text="Configuración Puerto")

        self._populate_tabs()
        self._populate_port_config_tab()  # This will call _build_port_config_widgets

    def _populate_tabs(self):
        # Widgets for Postura tab
        self.posture_val_lbl = self._lbl(self.frames["Postura"], "Valor flex: --", font=("Helvetica", 18))
        self.posture_status_lbl = self._lbl(self.frames["Postura"], "Estado: --", font=("Helvetica", 16))
        self.posture_val_lbl.pack(pady=20, padx=10, expand=True)
        self.posture_status_lbl.pack(pady=10, padx=10, expand=True)

        # Widgets for Pulso tab
        self.pulse_val_lbl = self._lbl(self.frames["Pulso"], "Pulso: -- bpm", font=("Helvetica", 18))
        self.pulse_status_lbl = self._lbl(self.frames["Pulso"], "Estado: --", font=("Helvetica", 16))
        self.pulse_val_lbl.pack(pady=20, padx=10, expand=True)
        self.pulse_status_lbl.pack(pady=10, padx=10, expand=True)

        # Widgets for Sudor tab
        self.sweat_val_lbl = self._lbl(self.frames["Sudor"], "Humedad: --", font=("Helvetica", 18))
        self.sweat_status_lbl = self._lbl(self.frames["Sudor"], "Estado: --", font=("Helvetica", 16))
        self.sweat_val_lbl.pack(pady=20, padx=10, expand=True)
        self.sweat_status_lbl.pack(pady=10, padx=10, expand=True)

        # Widgets for BMI tab
        bmi_f = self.frames["BMI"]
        self.bmi_height_lbl = self._lbl(bmi_f, "Altura: -- cm (sensor)", font=("Helvetica", 14))
        self.bmi_height_lbl.pack(pady=(15, 5))
        w_frame = ttk.Frame(bmi_f)
        w_frame.pack()
        ttk.Label(w_frame, text="Peso (kg):").pack(side="left", padx=(0, 5))
        self.weight_entry = ttk.Entry(w_frame, width=8)
        self.weight_entry.pack(side="left")
        ttk.Button(w_frame, text="Calcular BMI", command=self._calc_bmi).pack(side="left", padx=6)
        self.bmi_result_lbl = self._lbl(bmi_f, "BMI: --", font=("Helvetica", 16))
        self.bmi_result_lbl.pack(pady=10)

        # Widgets for Nivel de estrés tab
        self.stress_value_lbl = self._lbl(self.frames["Nivel de estrés"], "Valor de estrés: --", font=("Helvetica", 18))
        self.stress_value_lbl.pack(expand=True, pady=20)
        self.stress_lbl = self._lbl(self.frames["Nivel de estrés"], "Nivel de estrés: --", font=("Helvetica", 20))
        self.stress_lbl.pack(expand=True, pady=20)

    def _build_port_config_widgets(self, parent_frame: tk.Widget) -> ttk.Frame:
        """
        Helper to create port configuration widgets (Label, Combobox, Refresh Button, Apply Button).
        These widgets are created within the given parent_frame.
        """
        config_outer_frame = ttk.Frame(parent_frame)
        config_outer_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)  # Reduced padding slightly

        config_frame = ttk.Frame(config_outer_frame)
        config_frame.pack(anchor=tk.CENTER, pady=10)

        ttk.Label(config_frame, text="Puerto ESP32:").grid(row=0, column=0, padx=(0, 5), pady=10, sticky=tk.W)

        # Combobox for port selection
        port_combobox = ttk.Combobox(config_frame, textvariable=self.port_value, width=20, state="readonly")
        port_combobox.grid(row=0, column=1, padx=5, pady=10, sticky=tk.EW)

        # Button to apply the selected port and reconnect
        reconnect_button = ttk.Button(config_frame, text="Aplicar y Reintentar", command=self._trigger_reconnect)

        # This button's state will be managed by refresh_this_combobox_list

        def refresh_this_combobox_list():
            """Scans for available serial ports and updates this specific Combobox."""
            try:
                ports = [p.device for p in serial.tools.list_ports.comports()]
            except Exception as e:
                ports = []
                messagebox.showwarning("Error al escanear puertos", f"No se pudieron listar los puertos seriales:\n{e}",
                                       parent=self.root)

            current_selection = self.port_value.get()
            port_combobox['values'] = ports

            if ports:
                if current_selection in ports:
                    self.port_value.set(current_selection)
                else:
                    self.port_value.set(ports[0])  # Default to the first port if current is not valid or empty
                port_combobox.config(state="readonly")
                reconnect_button.config(state="normal")  # Enable Apply button
            else:
                self.port_value.set("")  # Clear selection if no ports
                port_combobox.config(state="disabled")  # Disable combobox
                reconnect_button.config(state="disabled")  # Disable Apply button
            # print(f"Puertos actualizados: {ports}, Seleccionado: {self.port_value.get()}") # Debug

        refresh_button = ttk.Button(config_frame, text="Refrescar", command=refresh_this_combobox_list)
        refresh_button.grid(row=0, column=2, padx=(5, 0), pady=10, sticky=tk.W)

        reconnect_button.grid(row=1, column=0, columnspan=3, pady=(10, 0), sticky=tk.EW)

        config_frame.columnconfigure(1, weight=1)  # Allow combobox to expand

        refresh_this_combobox_list()  # Initial population for this combobox

        return config_outer_frame  # Return the main frame containing these widgets

    def _populate_port_config_tab(self):
        """Populates the 'Configuración Puerto' tab."""
        tab_frame = self.frames["Configuración Puerto"]
        # Build the widgets directly into the tab_frame
        self._build_port_config_widgets(tab_frame)

    def _stop_serial_thread(self):
        if self.serial_thread and self.serial_thread.is_alive():
            self.running = False
            if self.ser_instance:
                try:
                    self.ser_instance.close()
                except Exception:
                    pass
            self.serial_thread.join(timeout=1.5)  # Increased timeout slightly
            if self.serial_thread.is_alive():
                print("Advertencia: El hilo serial no terminó limpiamente.")
        self.serial_thread = None
        self.ser_instance = None

    def _start_serial_reader(self):
        self._stop_serial_thread()
        self.running = True
        self.serial_thread = threading.Thread(target=self._serial_loop, daemon=True)
        self.serial_thread.start()

    @staticmethod
    def _extract_int(line: str) -> float | None:
        try:
            val_part = line.split(";", 1)[1]
            digits = ''.join(ch for ch in val_part if (ch.isdigit() or ch == "."))
            return float(digits) if digits else None
        except (IndexError, ValueError):
            return None

    def _serial_loop(self):
        port_to_try = self.port_value.get()
        if not port_to_try:  # If port is empty (e.g. no ports found and user didn't select one)
            self._dispatch(self._show_error, "No se ha seleccionado ningún puerto.")
            return

        try:
            # print(f"Intentando conectar al puerto: {port_to_try} a {BAUD} baudios")
            with serial.Serial(port_to_try, BAUD, timeout=1) as ser:
                self.ser_instance = ser
                # print(f"Conectado exitosamente a {port_to_try}")
                self._dispatch(self._hide_error_show_main)

                while self.running:
                    if not ser.is_open:
                        if self.running:
                            raise serial.SerialException(f"El puerto {port_to_try} se cerró inesperadamente.")
                        else:
                            break
                    try:
                        raw_line = ser.readline()
                    except serial.SerialException as e:
                        if self.running:
                            raise e
                        else:
                            break
                    if not raw_line:
                        continue

                    for line in raw_line.decode(errors="ignore").split("\n"):
                        line = line.strip()
                        if not line or not self.running:
                            continue

                        value = self._extract_int(line)
                        if value is None:
                            continue

                        if line.startswith("pulse value;"):
                            self._dispatch(self._update_pulse, value)
                        elif line.startswith("flex value;"):
                            self._dispatch(self._update_posture, value)
                        elif line.startswith(
                                "height value;"):  # Removed "and self.height_cm is None" to allow re-reading if needed
                            self._dispatch(self._update_height_once, value)
                        elif line.startswith("sweat value;"):
                            self._dispatch(self._update_sweat, value)
        except serial.SerialException as e:
            error_message = f"No se pudo conectar al puerto '{port_to_try}'."
            if "FileNotFoundError" in str(e) or "Errno 2" in str(e):
                error_message = f"Puerto '{port_to_try}' no encontrado o no disponible."
            elif "PermissionError" in str(e) or "Errno 13" in str(e):
                error_message = f"Permiso denegado para el puerto '{port_to_try}'."
            elif "OSError: [WinError 5]" in str(e) or "[Errno 5]" in str(
                    e):  # Access denied (Windows and potentially others)
                error_message = f"Acceso denegado al puerto '{port_to_try}'. ¿Está en uso por otro programa?"
            else:
                error_message = f"Error al abrir puerto '{port_to_try}': {e}"
            self._dispatch(self._show_error, error_message)
        except Exception as e:
            self._dispatch(self._show_error, f"Error inesperado en comunicación serial: {str(e)}")
        finally:
            if self.ser_instance:
                try:
                    self.ser_instance.close()
                except Exception:
                    pass
            self.ser_instance = None
            # print(f"Hilo serial para {port_to_try} terminado.")

    def _dispatch(self, func, *args):
        if self.root.winfo_exists() and None not in args:
            if func == self._show_error or self.running:
                self.root.after(0, func, *args)

    def _reset_ui_status(self):
        if hasattr(self, 'posture_val_lbl') and self.posture_val_lbl.winfo_exists():
            self.posture_val_lbl.config(text="Valor flex: --")
            self.posture_status_lbl.config(text="Estado: --", fg=self.text_colour)

        if hasattr(self, 'pulse_val_lbl') and self.pulse_val_lbl.winfo_exists():
            self.pulse_val_lbl.config(text="Pulso: -- bpm")
            self.pulse_status_lbl.config(text="Estado: --", fg=self.text_colour)

        if hasattr(self, 'sweat_val_lbl') and self.sweat_val_lbl.winfo_exists():
            self.sweat_val_lbl.config(text="Humedad: --")
            self.sweat_status_lbl.config(text="Estado: --", fg=self.text_colour)

        if hasattr(self, 'bmi_height_lbl') and self.bmi_height_lbl.winfo_exists():
            self.bmi_height_lbl.config(text="Altura: -- cm (sensor)")
        if hasattr(self, 'bmi_result_lbl') and self.bmi_result_lbl.winfo_exists():
            self.bmi_result_lbl.config(text="BMI: --")

        if hasattr(self, 'stress_value_lbl') and self.stress_value_lbl.winfo_exists():
            self.stress_value_lbl.config(text="Valor de estrés: --")
        if hasattr(self, 'stress_lbl') and self.stress_lbl.winfo_exists():
            self.stress_lbl.config(text="Nivel de estrés: --", fg=self.text_colour)

        self.warnings = {"POSTURE": False, "PULSE": False, "SWEAT": False}
        self.height_cm = None
        self.pulse_times.clear()

    def _trigger_reconnect(self):
        new_port = self.port_value.get().strip()
        if not new_port:
            messagebox.showerror("Puerto Vacío", "Por favor, seleccione un puerto de la lista.", parent=self.root)
            return

        # globals()['PORT'] = new_port # This line is not strictly necessary if _serial_loop always uses self.port_value.get()

        self._hide_error_show_main()
        self._reset_ui_status()
        self._start_serial_reader()

        if hasattr(self, 'nb'):
            self.nb.select(0)

    def _hide_error_show_main(self):
        if self.error_frame.winfo_ismapped():
            self.error_frame.pack_forget()
        if not self.main_frame.winfo_ismapped():
            self.main_frame.pack(expand=True, fill="both")

    def _show_error(self, msg: str):
        self._stop_serial_thread()

        if self.main_frame.winfo_ismapped():
            self.main_frame.pack_forget()

        for widget in self.error_frame.winfo_children():
            widget.destroy()

        error_info_frame = ttk.Frame(self.error_frame)
        error_info_frame.pack(pady=(10, 5), padx=20, fill=tk.X)  # Reduced top padding

        error_icon_lbl = ttk.Label(error_info_frame, text="⚠️", font=("Helvetica", 24))
        error_icon_lbl.pack(side=tk.LEFT, padx=(0, 10))

        error_message_lbl = self._lbl(error_info_frame, f"{msg}\nVerifique la conexión o configure el puerto abajo.",
                                      font=("Helvetica", 11), justify=tk.LEFT)  # Slightly smaller font
        error_message_lbl.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Add port configuration widgets directly to the error screen
        self._build_port_config_widgets(self.error_frame)  # This will create and populate the combobox

        if not self.error_frame.winfo_ismapped():
            self.error_frame.pack(expand=True, fill="both")

        # print(f"Mostrando error: {msg}")

    # ───────────────────────── GUI updaters ──────────────────────────── #
    def _update_posture(self, v: int):
        self.posture_val_lbl.config(text=f"Valor flex: {v}")
        self.S = v # update for stress calculation
        ok = v >= POSTURE_THRESHOLD
        self.posture_status_lbl.config(text="Correcto" if ok else "Incorrecto", fg="green" if ok else "red")
        self.warnings["POSTURE"] = not ok
        self._update_stress()
        if ok:
            self._stop_beep()
        else:
            self._start_beep()

    def _update_pulse(self, bpm: int):
        self.pulse_val_lbl.config(text=f"Pulso: {bpm} bpm")
        self.P = bpm  # update for stress calculation
        ok = PULSE_MIN <= bpm <= PULSE_MAX
        self.pulse_status_lbl.config(
            text="Normal" if ok else "Fuera de rango",
            fg="green" if ok else "red"
        )
        self.warnings["PULSE"] = not ok
        self._update_stress()

    def _update_height_once(self, cm: float):
        self.height_cm = cm  # Store the new height
        if hasattr(self, 'bmi_height_lbl') and self.bmi_height_lbl.winfo_exists():
            self.bmi_height_lbl.config(text=f"Altura: {cm:.1f} cm (sensor)")
        self._calc_bmi()  # Recalculate BMI if height changes

    def _update_sweat(self, v: int):
        ok = v == 1
        val = random.randint(0, 10) if ok else random.randint(40, 75)
        self.sweat_val_lbl.config(text=f"Humedad: {val}%")
        self.H = val/100  # update for stress calculation
        self.sweat_status_lbl.config(text="Normal (No se detecta sudor)" if ok else "Alta (Sudor detectado)",
                                     fg="green" if ok else "red")
        self.warnings["SWEAT"] = not ok
        self._update_stress()

    def _calc_bmi(self):
        if self.height_cm is None:
            return
        try:
            txt = self.weight_entry.get().strip()
            if not txt:
                self.weight_kg = None
                self.bmi_result_lbl.config(text="BMI: --")
                return
            self.weight_kg = float(txt)
        except ValueError:
            self.weight_kg = None
            return

        if self.weight_kg is None or self.weight_kg <= 0:
            self.bmi_result_lbl.config(text="BMI: (peso inválido)")
            return

        h_m = self.height_cm / 100.0
        if h_m <= 0:
            self.bmi_result_lbl.config(text="BMI: (altura inválida)")
            return
        bmi = self.weight_kg / (h_m ** 2)
        self.bmi_result_lbl.config(text=f"BMI: {bmi:.1f}")
        self.I = bmi

    def _update_stress(self):
        n = sum(self.warnings.values())

        if (self.I is None or self.H is None or self.P is None or self.S is None):
            return

        stress = ( ( self.I * self.H ) + ( self.P * self.P ) ) / ( self.S + 1 )

        level = STRESS_LEVELS.get(n, STRESS_LEVELS[
            max(STRESS_LEVELS.keys()) if STRESS_LEVELS else 3])  # Default to highest defined stress if n is out of typical range
        colour = "green" if level == "Bajo" else ("orange" if level == "Medio" else "red")
        self.stress_value_lbl.config(text=f"Valor de estrés: {stress:.2f}", fg=colour)
        self.stress_lbl.config(text=f"Nivel de estrés: {level}", fg=colour)

    # ───────────── BEEP CONTROL ───────────── #
    def _start_beep(self) -> None:
        if not self.beep_active:
            self.beep_active = True
            self.root.after(100, self._perform_beep_if_needed)

    def _perform_beep_if_needed(self):
        if self.beep_active and self.warnings["POSTURE"]:
            self.root.bell()
            self.root.after(600, self._perform_beep_if_needed)

    def _stop_beep(self) -> None:
        self.beep_active = False


# ─────────────────────────────── Main ───────────────────────────────── #

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    available_themes = style.theme_names()

    if 'vista' in available_themes and platform.system() == "Windows":
        style.theme_use('vista')
    elif 'aqua' in available_themes and platform.system() == "Darwin":  # macOS
        style.theme_use('aqua')

    app = FlexMonitorGUI(root)
    root.mainloop()
