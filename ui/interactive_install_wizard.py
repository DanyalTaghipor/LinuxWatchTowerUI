import os
import sys
import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
from rich.console import Console
from ansible_utils.inventory import get_host_nicknames
from ansible_utils.roles_enum import Tools
from ansible_utils.ansible_executor import install_tool
import paramiko
import subprocess
import time
import socket
import logging
import threading
from db.database import init_db, log_installation, get_host_status, log_host_status, update_host_status

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

console = Console()


def get_available_tools(custom_roles_path=None):
    roles_dirs = [
        os.path.join(sys._MEIPASS, 'ansible_utils', 'roles'),  # Default roles path
    ]

    if custom_roles_path and os.path.exists(custom_roles_path):
        roles_dirs.append(custom_roles_path)

    tools = []
    print(f"Hey => {custom_roles_path}")
    print(f"Hey => {roles_dirs} \n")
    for roles_dir in roles_dirs:
        print(f"Role Status => {os.path.exists(roles_dir)} \n")
        if os.path.exists(roles_dir):
            for role_name in os.listdir(roles_dir):
                print(f"Role Name => {role_name} \n")
                role_path = os.path.join(roles_dir, role_name)
                if os.path.isdir(role_path):
                    tools.append(role_name)

    return tools

class InteractiveInstallWizard:

    def __init__(self, parent):
        self.parent = parent
        self.steps = [self.config_path_step, self.select_host_step, self.select_tool_step, self.check_tool_status_step]
        self.current_step = 0
        self.config_path = ''
        self.selected_hosts = []
        self.selected_tool = ''
        self.version = ''
        self.host_nicknames = []
        self.tool_list = []
        self.init_db()
        self.show_step()

    def init_db(self):
        init_db()

    def clear_frame(self):
        for widget in self.parent.winfo_children():
            widget.destroy()

    def show_step(self):
        self.clear_frame()
        step_function = self.steps[self.current_step]
        step_function()

    def next_step(self):
        self.current_step += 1
        self.show_step()

    def previous_step(self):
        self.current_step -= 1
        self.show_step()

    def config_path_step(self):
        from .buttons import show_main_buttons

        default_config_path = os.path.expanduser("~/.ssh/config")
        config_path_label = ctk.CTkLabel(self.parent, text=f"Config Path (default is {default_config_path}):")
        config_path_label.pack(pady=5)
        config_path_entry = ctk.CTkEntry(self.parent)
        config_path_entry.pack(pady=5)

        custom_roles_path_label = ctk.CTkLabel(self.parent, text="Custom Roles Path (optional):")
        custom_roles_path_label.pack(pady=5)
        custom_roles_path_entry = ctk.CTkEntry(self.parent)
        custom_roles_path_entry.pack(pady=5)

        def on_next():
            self.config_path = config_path_entry.get() or default_config_path
            self.custom_roles_path = custom_roles_path_entry.get() or None
            self.tool_list = get_available_tools(custom_roles_path=self.custom_roles_path)
            self.next_step()

        next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
        next_button.pack(pady=20)

        cancel_button = ctk.CTkButton(self.parent, text="Cancel", command=lambda: show_main_buttons(self.parent))
        cancel_button.pack(pady=10)

    def select_host_step(self):
        from .buttons import show_return_button

        def load_host_status_from_db(host):
            status = get_host_status(host)
            if status:
                accessible, needs_sudo_password, last_checked = status
                return accessible == 1, needs_sudo_password == 1, last_checked
            return None, None, None

        def update_host_status_in_db(host):
            accessible = self.check_host_accessibility(host)
            needs_sudo_password = self.check_sudo_password_requirement(host)
            if accessible is not None and needs_sudo_password is not None:
                update_host_status(host, accessible, needs_sudo_password)

        try:
            self.host_nicknames = get_host_nicknames(config_path=self.config_path)
            if not self.host_nicknames:
                messagebox.showerror("Error", "No hosts found in the SSH config file.")
                return

            table_frame = ctk.CTkFrame(self.parent)
            table_frame.pack(fill="both", expand=True)

            table = ttk.Treeview(table_frame, columns=("Number", "Host", "Accessible", "Sudo Password Required", "Last Checked"), show='headings')
            table.heading("Number", text="Number")
            table.heading("Host", text="Host")
            table.heading("Accessible", text="Accessible")
            table.heading("Sudo Password Required", text="Sudo Password Required")
            table.heading("Last Checked", text="Last Checked")

            self.selected_hosts_vars = []

            for index, host in enumerate(self.host_nicknames, start=1):
                accessible, needs_sudo_password, last_checked = load_host_status_from_db(host)
                var = tk.BooleanVar()
                self.selected_hosts_vars.append((var, host))
                
                table.insert("", "end", values=(
                    index, 
                    host, 
                    "Yes" if accessible else "No" if accessible is not None else "Unknown", 
                    "Yes" if needs_sudo_password else "No" if needs_sudo_password is not None else "Unknown", 
                    last_checked or "Unknown"
                ))

            table.pack(fill="both", expand=True)
            table.update_idletasks()

            checkbox_frame = tk.Frame(table_frame)
            checkbox_frame.place(relx=0, rely=0, relwidth=0.05, relheight=1)

            for index, child in enumerate(table.get_children(), start=1):
                bbox = table.bbox(child)
                if bbox:
                    var, host = self.selected_hosts_vars[index - 1]
                    checkbox = tk.Checkbutton(checkbox_frame, variable=var)
                    checkbox.place(x=5, y=bbox[1] + bbox[3]//2 - checkbox.winfo_reqheight()//2)

            def on_check():
                for var, host in self.selected_hosts_vars:
                    if var.get():
                        update_host_status_in_db(host)
                self.show_step()

            def on_next():
                self.selected_hosts = [host for var, host in self.selected_hosts_vars if var.get()]
                if not self.selected_hosts:
                    messagebox.showerror("Error", "No host selected.")
                    return
                self.next_step()

            check_button = ctk.CTkButton(self.parent, text="Check", command=on_check)
            check_button.pack(pady=20)

            next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
            next_button.pack(pady=20)

            show_return_button(self.parent)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def check_host_accessibility(self, host):
        console.log(f"Checking accessibility for host: {host}")
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(host)
            client.close()
            return True
        except Exception as e:
            console.log(f"Error checking accessibility for host {host}: {e}")
            return False

    def check_sudo_password_requirement(self, host):
        console.log(f"Checking sudo password requirement for host: {host}")
        try:
            command = 'echo "Checking sudo access"'
            result = subprocess.run(['ssh', host, 'sudo', '-n', command], capture_output=True)
            return result.returncode != 0
        except Exception as e:
            console.log(f"Error checking sudo password requirement for host {host}: {e}")
            return False

    def select_tool_step(self):
        from .buttons import show_return_button

        if not self.tool_list:
            messagebox.showerror("Error", "No tools available.")
            return

        selected_tool_var = tk.StringVar(value=self.tool_list[0])
        tool_label = ctk.CTkLabel(self.parent, text="Select Tool:")
        tool_label.pack(pady=5)
        tool_dropdown = ctk.CTkComboBox(self.parent, variable=selected_tool_var, values=self.tool_list)
        tool_dropdown.pack(pady=5)

        def on_next():
            self.selected_tool = selected_tool_var.get()
            self.next_step()

        next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
        next_button.pack(pady=20)

        show_return_button(self.parent)

    def check_tool_status_step(self):
        from .buttons import show_return_button
        from threading import Thread

        log_box = ctk.CTkTextbox(self.parent, width=500, height=300)
        log_box.pack(pady=20)

        def append_log(message):
            log_box.insert("end", message + "\n")
            log_box.see("end")

        def perform_installation():
            success = True
            for host in self.selected_hosts:
                try:
                    if not check_installation(host, self.selected_tool):
                        append_log(f"Installing {self.selected_tool} on {host}")
                        result = install_tool(host, self.selected_tool)  # Removed version parameter
                        if result:
                            log_installation(host, self.selected_tool)
                            append_log(f"Successfully installed {self.selected_tool} on {host}")
                        else:
                            append_log(f"Failed to install {self.selected_tool} on {host}")
                            success = False
                    else:
                        append_log(f"{self.selected_tool} is already installed on {host}")
                except Exception as e:
                    append_log(f"Error installing {self.selected_tool} on {host}: {e}")
                    success = False
            if success:
                messagebox.showinfo("Success", f"{self.selected_tool} installation completed.")
            else:
                messagebox.showerror("Error", f"{self.selected_tool} installation failed on one or more hosts.")

        installation_thread = Thread(target=perform_installation)
        installation_thread.start()

        show_return_button(self.parent)


def show_interactive_install(frame):
    InteractiveInstallWizard(frame)
