import os
import customtkinter as ctk
from tkinter import messagebox
from .utils import clear_frame

def show_set_target(frame):
    from .buttons import show_main_buttons

    clear_frame(frame)
    
    nickname_label = ctk.CTkLabel(frame, text="Nickname:")
    nickname_label.pack(pady=5)
    nickname_entry = ctk.CTkEntry(frame)
    nickname_entry.pack(pady=5)
    
    server_label = ctk.CTkLabel(frame, text="Server Address:")
    server_label.pack(pady=5)
    server_entry = ctk.CTkEntry(frame)
    server_entry.pack(pady=5)

    user_label = ctk.CTkLabel(frame, text="User:")
    user_label.pack(pady=5)
    user_entry = ctk.CTkEntry(frame)
    user_entry.pack(pady=5)

    identity_file_label = ctk.CTkLabel(frame, text="Identity File (default: ~/.ssh/id_rsa):")
    identity_file_label.pack(pady=5)
    identity_file_entry = ctk.CTkEntry(frame)
    identity_file_entry.pack(pady=5)

    port_label = ctk.CTkLabel(frame, text="Port (default: 22):")
    port_label.pack(pady=5)
    port_entry = ctk.CTkEntry(frame)
    port_entry.pack(pady=5)

    config_path_label = ctk.CTkLabel(frame, text="Config Path (default: ~/.ssh/config):")
    config_path_label.pack(pady=5)
    config_path_entry = ctk.CTkEntry(frame)
    config_path_entry.pack(pady=5)

    def save_target():
        nickname = nickname_entry.get()
        server = server_entry.get()
        user = user_entry.get()
        identity_file = identity_file_entry.get() or os.path.expanduser('~/.ssh/id_rsa')
        port = port_entry.get() or '22'
        default_path = os.path.expanduser("~/.ssh/config")
        config_path = config_path_entry.get() or default_path

        if not nickname or not server or not user:
            messagebox.showerror("Error", "Nickname, Server Address, and User are mandatory fields.")
            for entry, value in [(nickname_entry, nickname), (server_entry, server), (user_entry, user)]:
                if not value:
                    entry.configure(border_color="red")
                else:
                    entry.configure(border_color="default")
            return

        try:
            with open(config_path, 'a') as configfile:
                configfile.write(f"\nHost {nickname}\n")
                configfile.write(f"   HostName {server}\n")
                configfile.write(f"   User {user}\n")
                configfile.write(f"   IdentityFile {identity_file}\n")
                configfile.write(f"   Port {port}\n")
            messagebox.showinfo("Success", "Target set successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    save_button = ctk.CTkButton(frame, text="Save", command=save_target)
    save_button.pack(pady=20)

    cancel_button = ctk.CTkButton(frame, text="Return to Homepage", command=lambda: show_main_buttons(frame))
    cancel_button.pack(pady=10)