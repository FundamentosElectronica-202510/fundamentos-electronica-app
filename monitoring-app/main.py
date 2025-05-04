import serial
import threading
import tkinter as tk

# Set your Arduino's port — find it via: `ls /dev/tty.usb*`
PORT = '/dev/tty.usbmodem1101'  # <- update if needed
BAUD = 9600

class FlexMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de sensores - Arduino")
        self.root.attributes('-topmost', True) # Make window stay on top

        # Define window size
        window_width = 300
        window_height = 200

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Calculate position x, y
        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)

        # Set geometry with position
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        self.label = tk.Label(root, text="Esperando información del dispositivo...", font=("Helvetica", 16))
        self.label.pack(pady=30)

        self.status = tk.Label(root, text="", font=("Helvetica", 14), fg="black")
        self.status.pack()

        self.serial_thread = threading.Thread(target=self.read_serial)
        self.serial_thread.daemon = True
        self.serial_thread.start()

    def read_serial(self):
        try:
            with serial.Serial(PORT, BAUD, timeout=1) as ser:
                while True:
                    line = ser.readline().decode('utf-8').strip()
                    if line.startswith("[WARNING]"):
                        value = int(line.split("-")[1])
                        # Use after to schedule GUI updates on the main thread
                        self.root.after(0, self.update_gui, value)
        except serial.SerialException as e:
            # Use after to schedule GUI updates on the main thread
            self.root.after(0, self.label.config, {"text": f"Error: {e}"})
        except Exception as e: # Catch potential decoding or int conversion errors
             self.root.after(0, self.label.config, {"text": f"Processing Error: {e}"})


    def update_gui(self, value):
        self.label.config(text=f"Flex value: {value}")
        if value < 220:
            self.status.config(text="⚠️ WARNING: Sensor Triggered!", fg="red")
        else:
            self.status.config(text="Sensor OK", fg="green")

# Run the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = FlexMonitor(root)
    root.mainloop()