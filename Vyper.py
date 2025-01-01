import os
import platform
import json
import shutil
import subprocess
from threading import Thread
from tkinter import filedialog, colorchooser, messagebox
import customtkinter as ctk

# Determine the base directory for Vyper based on the operating system
if platform.system() == "Windows":
    BASE_DIR = r"C:\Program Files\Vyper"
elif platform.system() == "Linux":
    BASE_DIR = "/opt/Vyper"
else:
    raise OSError("Unsupported operating system.")

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
VPN_DIR = os.path.join(BASE_DIR, "vpns")

# Ensure the required directories exist
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(VPN_DIR, exist_ok=True)


class VPNLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Vyper VPN Launcher")
        self.resizable(False, False)

        # Initialize theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.vpn_file = None
        self.username = None
        self.password = None
        self.current_status = "Disconnected"
        self.is_vpn_running = False  # Track VPN state
        self.process = None  # Track the VPN process
        self.load_config()
        self.create_widgets()

        # Load VPN files into the list
        self.refresh_vpn_list()

        # Automatically adjust window size to content
        self.update()
        self.geometry(f"{self.winfo_width()}x{self.winfo_height()}")

        # Add protocol handler for graceful shutdown
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Main container
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Left Panel (Main Controls)
        self.left_panel = ctk.CTkFrame(self.main_frame)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        # Drop Area with Unicode Icon
        self.drop_icon = ctk.CTkLabel(
            self.left_panel,
            text="📂",
            font=("Helvetica", 40),
            text_color="gray70",
        )
        self.drop_icon.bind("<Button-1>", self.handle_drop)
        self.drop_icon.grid(row=0, column=0, pady=5, sticky="n")

        self.drop_label = ctk.CTkLabel(
            self.left_panel,
            text="Drag and Drop VPN Files Here",
            font=("Helvetica", 12),
            text_color="gray70",
        )
        self.drop_label.grid(row=1, column=0, pady=5, sticky="n")

        # Username Input
        self.username_entry = ctk.CTkEntry(
            self.left_panel,
            placeholder_text="VPN Username (optional)",
        )
        self.username_entry.grid(row=2, column=0, pady=5, sticky="ew")

        # Password Input with Toggle Visibility
        self.password_entry = ctk.CTkEntry(
            self.left_panel,
            placeholder_text="VPN Password (optional)",
            show="*",
        )
        self.password_entry.grid(row=3, column=0, pady=5, sticky="ew")

        self.password_toggle = ctk.CTkCheckBox(
            self.left_panel,
            text="Show Password",
            command=self.toggle_password_visibility,
        )
        self.password_toggle.grid(row=4, column=0, pady=5, sticky="ew")

        # Connect/Disconnect button
        self.toggle_button = ctk.CTkButton(
            self.left_panel,
            text="Connect",
            command=self.toggle_vpn,
            state="disabled",
            height=35,
        )
        self.toggle_button.grid(row=5, column=0, pady=10, sticky="ew")

        # Status Display
        self.status_label = ctk.CTkLabel(
            self.left_panel,
            text="Status: Disconnected",
            font=("Helvetica", 12),
        )
        self.status_label.grid(row=6, column=0, pady=10, sticky="n")

        # Right Panel (VPN File List)
        self.right_panel = ctk.CTkFrame(self.main_frame)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(0, weight=1)

        self.vpn_listbox = ctk.CTkScrollableFrame(self.right_panel)
        self.vpn_listbox.grid(row=0, column=0, sticky="nsew")

        self.vpn_list = []
        self.vpn_buttons = {}

        # Bottom Configuration Panel
        self.config_pane = ctk.CTkFrame(self, fg_color="gray20", height=50)
        self.config_pane.grid(row=1, column=0, sticky="ew", padx=5, pady=5, columnspan=2)
        self.config_pane.grid_columnconfigure((0, 1), weight=1)

        # Accent color selector
        self.accent_button = ctk.CTkButton(
            self.config_pane,
            text="Change Button Color",
            command=self.change_accent_color,
            height=30,
        )
        self.accent_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Appearance mode toggle
        self.mode_switch = ctk.CTkSwitch(
            self.config_pane,
            text="Dark Mode",
            command=self.toggle_appearance,
        )
        self.mode_switch.grid(row=0, column=1, padx=5, pady=5)

        # Load initial appearance mode
        self.mode_switch.select() if self.config.get("appearance", "Dark") == "Dark" else self.mode_switch.deselect()
        self.update_config_pane_color()

    def toggle_password_visibility(self):
        """Toggle the visibility of the password field."""
        if self.password_entry.cget("show") == "*":
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="*")

    def toggle_vpn(self):
        """Toggle the VPN connection (connect or disconnect)."""
        self.username = self.username_entry.get().strip()
        self.password = self.password_entry.get().strip()

        if self.is_vpn_running:
            self.stop_vpn()
        else:
            self.start_vpn()

    def start_vpn(self):
        """Start the VPN connection."""
        if not self.vpn_file:
            messagebox.showerror("Error", "No VPN file selected.")
            return

        self.toggle_button.configure(text="Connecting...", state="disabled")
        self.update_status("Connecting")

        self.vpn_thread = Thread(target=self.run_vpn)
        self.vpn_thread.start()

    def run_vpn(self):
        try:
            # Pass credentials if provided
            env = os.environ.copy()
            if self.username and self.password:
                env["OPENVPN_USERNAME"] = self.username
                env["OPENVPN_PASSWORD"] = self.password

            command = ["sudo", "openvpn", self.vpn_file]
            self.process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = self.process.communicate()

            if self.process.returncode == 0:
                self.update_status("Connected")
                self.is_vpn_running = True
                self.toggle_button.configure(text="Disconnect", state="normal")
            else:
                self.update_status("Disconnected")
                self.is_vpn_running = False
                self.toggle_button.configure(text="Connect", state="normal")
        except Exception as e:
            self.update_status("Disconnected")
            messagebox.showerror("Error", f"Failed to start VPN: {e}")
            self.is_vpn_running = False
            self.toggle_button.configure(text="Connect", state="normal")

    def stop_vpn(self):
        """Stop the VPN connection."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop VPN: {e}")
        self.update_status("Disconnected")
        self.is_vpn_running = False
        self.toggle_button.configure(text="Connect", state="normal")

    def update_status(self, status):
        """Update the connection status."""
        self.current_status = status
        self.status_label.configure(text=f"Status: {status}")

    def handle_drop(self, event):
        """Handle file drop for .ovpn files."""
        filetypes = [("OpenVPN Files", "*.ovpn")]
        selected_file = filedialog.askopenfilename(filetypes=filetypes)
        if selected_file:
            try:
                file_name = os.path.basename(selected_file)
                destination = os.path.join(VPN_DIR, file_name)  # Save to VPN_DIR
                shutil.copy(selected_file, destination)
                self.refresh_vpn_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add VPN file: {e}")

    def refresh_vpn_list(self):
        """Refresh the list of VPN files in the right panel."""
        for button in self.vpn_buttons.values():
            button.destroy()
        self.vpn_buttons.clear()

        self.vpn_list = [f for f in os.listdir(VPN_DIR) if f.endswith(".ovpn")]

        for vpn_file in self.vpn_list:
            button = ctk.CTkButton(
                self.vpn_listbox,
                text=vpn_file,
                command=lambda file=vpn_file: self.select_vpn_file(file),
                width=150,
            )
            button.pack(pady=5)
            self.vpn_buttons[vpn_file] = button

    def select_vpn_file(self, vpn_file):
        """Select a VPN file to connect."""
        self.vpn_file = os.path.join(VPN_DIR, vpn_file)
        self.toggle_button.configure(state="normal")

    def on_closing(self):
        """Handle the application closing event."""
        if self.is_vpn_running:
            self.stop_vpn()
        self.destroy()

    def load_config(self):
        """Load user configuration from the JSON file."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
            else:
                self.config = {"appearance": "Dark", "accent_color": "#0078D7"}
                self.save_config()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")
            self.config = {"appearance": "Dark", "accent_color": "#0078D7"}

    def save_config(self):
        """Save the user configuration to the JSON file."""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def change_accent_color(self):
        """Allow the user to choose a new accent color."""
        color = colorchooser.askcolor(title="Choose Button Color")[1]
        if color:
            self.config["accent_color"] = color
            self.save_config()
            text_color = self.adjust_text_color(color)
            self.toggle_button.configure(fg_color=color, text_color=text_color)
            self.accent_button.configure(fg_color=color, text_color=text_color)

    def toggle_appearance(self):
        """Toggle between light and dark mode."""
        appearance = "Dark" if self.mode_switch.get() == 1 else "Light"
        self.config["appearance"] = appearance
        ctk.set_appearance_mode(appearance)
        self.update_config_pane_color()
        self.save_config()

    def update_config_pane_color(self):
        """Update the configuration pane color based on the appearance mode."""
        if self.config["appearance"] == "Dark":
            self.config_pane.configure(fg_color="gray20")
        else:
            self.config_pane.configure(fg_color="white")

    def adjust_text_color(self, bg_color):
        """Calculate the appropriate text color (white or black) based on background color luminance."""
        bg_color = bg_color.lstrip("#")  # Remove the '#' if present
        r, g, b = int(bg_color[:2], 16), int(bg_color[2:4], 16), int(bg_color[4:], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255  # Calculate luminance
        return "white" if luminance < 0.5 else "black"  # Return white for dark backgrounds, black for light


if __name__ == "__main__":
    app = VPNLauncher()
    app.mainloop()
