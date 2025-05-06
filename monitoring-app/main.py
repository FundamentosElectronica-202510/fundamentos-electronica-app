import platform
import subprocess
import serial
import threading
import tkinter as tk

# Set your Arduino's port — find it via: `ls /dev/tty.usb*`
PORT = '/dev/tty.usbmodem1101'  # TODO update serial port if needed
BAUD = 9600


def is_macos_dark_mode():
    """ AUX FUN. Check if macOS is in dark mode."""
    if platform.system() != "Darwin":
        return False
    try:
        cmd = 'defaults read -g AppleInterfaceStyle'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True)
        stdout, _ = p.communicate()
        return stdout.decode().strip() == 'Dark'
    except Exception:
        return False


class FlexMonitor:
    
    def __init__(self, root):
        self.serial_thread = None
        self.error_frame = None
        self.root = root
        self.root.title("Monitor de sensores - Fundamentos de Electrónica")
        self.root.attributes('-topmost', True)  # Make window stay on top

        # Determine text color based on mode
        self.text_color = "white" if is_macos_dark_mode() else "black"
        # Set background for visibility in dark mode if needed (optional)
        # if is_macos_dark_mode():
        #     self.root.config(bg='black') # Or a dark gray

        # Define window size
        window_width = 500
        window_height = 400

        # Store dimensions for error layout
        self.window_width = window_width
        self.window_height = window_height

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate position x, y
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)

        # Set geometry with position
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.resizable(True, True)
        # Prevent the window from being resized below its initial dimensions
        self.root.minsize(self.window_width, self.window_height)

        self.label = tk.Label(root, text="Esperando información del dispositivo...", font=("Helvetica", 16),
                              fg=self.text_color)
        self.label.pack(pady=30)

        self.status = tk.Label(root, text="", font=("Helvetica", 14), fg=self.text_color)
        self.status.pack()

        # Start the serial-reading thread
        self.start_serial()

    def read_serial(self):
        """Read data from the serial port and update the GUI."""
        # TODO modificar función: debería haber una función para cada sensor, y no una función que lea todos los sensores. Utilizar Threads
        try:
            with serial.Serial(PORT, BAUD, timeout=1) as ser:
                while True:
                    line = ser.readline().decode('utf-8').strip()
                    if line.startswith("flex value"):
                        value = int(line.split(";")[1])
                        # Use after to schedule GUI updates on the main thread
                        self.root.after(0, self.update_gui, value)
        except serial.SerialException as e:
            # Use after to schedule GUI updates on the main thread
            self.root.after(0, self.show_error, e)
        except Exception as e:  # Catch potential decoding or int conversion errors
            self.root.after(0, self.show_error, e)

    def start_serial(self):
        """Launch or relaunch the serial-reading thread."""
        # TODO garantizar la existencia de 1 thread para cada sensor
        self.serial_thread = threading.Thread(target=self.read_serial)
        self.serial_thread.daemon = True
        self.serial_thread.start()

    def show_error(self, error):
        """Display an error panel when no device is connected."""
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        # Create error frame
        self.error_frame = tk.Frame(self.root)
        # if is_macos_dark_mode(): # Optional: Set frame background
        #     self.error_frame.config(bg='black')
        self.error_frame.pack(expand=True, fill="both")
        # Error message
        error_label = tk.Label(
            self.error_frame,
            text="No se detectó el dispositivo. Verifica la conexión.",
            fg=self.text_color,  # Use determined text color
            font=("Helvetica", 16),
            wraplength=self.window_width - 20,
            justify="center"
        )
        error_label.pack(padx=10, pady=20, expand=True)
        # Retry button
        retry_button = tk.Button(self.error_frame, text="Volver a intentar",
                                 command=self.retry)
        retry_button.pack(side="bottom", pady=20)

    def retry(self):
        """Handle retry: destroy error panel and restart serial logic."""
        if hasattr(self, 'error_frame'):
            self.error_frame.destroy()
        # Recreate original labels with correct color
        self.label = tk.Label(self.root, text="Esperando información del dispositivo...",
                              font=("Helvetica", 16), fg=self.text_color)
        self.label.pack(pady=30)
        self.status = tk.Label(self.root, text="", font=("Helvetica", 14), fg=self.text_color)
        self.status.pack()
        # Restart serial thread
        self.start_serial()

    def update_gui(self, value):
        self.label.config(text=f"Flex value: {value}", fg=self.text_color)  # Ensure label color is correct
        if value < 220:
            self.status.config(text="WARNING: Sensor activado!", fg="red")  # Warning is always red
        else:
            self.status.config(text="Sensor OK", fg="green")  # OK status is green


# Run the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = FlexMonitor(root)
    root.mainloop()
