import os
import sys
import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
from rich.console import Console
from ansible_utils.inventory import get_host_nicknames
from ansible_utils.roles_enum import Tools
from ansible_utils.ansible_executor import install_tool
from db.database import init_db, log_installation, log_host_status, get_host_status, update_host_status
import paramiko
import subprocess
import time
import socket
import logging
import threading

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
    for roles_dir in roles_dirs:
        if os.path.exists(roles_dir):
            for role_name in os.listdir(roles_dir):
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

        try:
            self.host_nicknames = get_host_nicknames(config_path=self.config_path)
            if not self.host_nicknames:
                messagebox.showerror("Error", "No hosts found in the SSH config file.")
                return

            table_frame = ctk.CTkFrame(self.parent)
            table_frame.pack(fill="both", expand=True)

            table = ttk.Treeview(table_frame, columns=("Number", "Host"), show='headings')
            table.heading("Number", text="Number")
            table.heading("Host", text="Host")

            self.selected_hosts_vars = []

            for index, host in enumerate(self.host_nicknames, start=1):
                var = tk.BooleanVar()
                self.selected_hosts_vars.append((var, host))
                table.insert("", "end", values=(index, host))

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

            def on_next():
                self.selected_hosts = [host for var, host in self.selected_hosts_vars if var.get()]
                if not self.selected_hosts:
                    messagebox.showerror("Error", "Please select at least one host.")
                else:
                    self.next_step()

            next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
            next_button.pack(pady=20)

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.previous_step)
            back_button.pack(pady=10)
        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))
            show_return_button(self.parent)

    def select_tool_step(self):
        from .buttons import show_return_button

        try:
            table_frame = ctk.CTkFrame(self.parent)
            table_frame.pack(fill="both", expand=True)

            tool_table = ttk.Treeview(table_frame, columns=("Number", "Tool"), show='headings')
            tool_table.heading("Number", text="Number")
            tool_table.heading("Tool", text="Tool")

            self.selected_tool_var = tk.StringVar()

            for index, tool in enumerate(self.tool_list, start=1):
                tool_table.insert("", "end", values=(index, tool))

            tool_table.pack(fill="both", expand=True)
            tool_table.update_idletasks()

            radio_frame = tk.Frame(table_frame)
            radio_frame.place(relx=0, rely=0, relwidth=0.05, relheight=1)

            for index, child in enumerate(tool_table.get_children(), start=1):
                bbox = tool_table.bbox(child)
                if bbox:
                    tool = self.tool_list[index - 1]
                    radio = tk.Radiobutton(radio_frame, variable=self.selected_tool_var, value=tool)
                    radio.place(x=5, y=bbox[1] + bbox[3]//2 - radio.winfo_reqheight()//2)

            version_label = ctk.CTkLabel(self.parent, text="Version (optional):")
            version_label.pack(pady=5)
            version_entry = ctk.CTkEntry(self.parent)
            version_entry.pack(pady=5)

            def on_next():
                self.selected_tool = self.selected_tool_var.get()
                self.version = version_entry.get()
                if not self.selected_tool:
                    messagebox.showerror("Error", "Please select a tool.")
                else:
                    self.next_step()

            next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
            next_button.pack(pady=20)

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.previous_step)
            back_button.pack(pady=10)
        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))
            show_return_button(self.parent)

    def check_tool_status_step(self):
        from .buttons import show_return_button

        try:
            output_text = ctk.CTkTextbox(self.parent)
            output_text.pack(fill="both", expand=True, padx=20, pady=20)
            output_text.insert(tk.END, "Checking tool status on selected hosts...\n")

            progress_bar = ttk.Progressbar(self.parent, mode='determinate')
            progress_bar.pack(fill="x", padx=20, pady=10)

            def check_host_status(host):
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                accessible = False
                needs_sudo_password = False

                try:
                    host_config = self.load_ssh_config(host, self.config_path)
                    ssh.connect(
                        hostname=host_config['hostname'],
                        port=int(host_config.get('port', 22)),
                        username=host_config.get('user'),
                        pkey=self.load_private_key(host_config['identityfile'][0]) if 'identityfile' in host_config else None,
                        look_for_keys=True,
                        timeout=10
                    )
                    accessible = True

                    stdin, stdout, stderr = ssh.exec_command("sudo -n true")
                    stdout.channel.recv_exit_status()
                except paramiko.ssh_exception.AuthenticationException:
                    needs_sudo_password = True
                except Exception as e:
                    console.print_exception()

                ssh.close()
                return accessible, needs_sudo_password

            def log_host_statuses():
                total_hosts = len(self.selected_hosts)
                progress_increment = 100 / total_hosts

                for host in self.selected_hosts:
                    hostname = self.get_hostname_from_host(host, self.config_path)
                    if not hostname:
                        output_text.insert(tk.END, f"Host: {host}, Error: Unable to resolve hostname\n")
                        continue

                    accessible, needs_sudo_password = check_host_status(host)
                    log_host_status(host, accessible, needs_sudo_password)

                    output_text.insert(tk.END, f"Host: {host}, Accessible: {accessible}, Needs Sudo Password: {needs_sudo_password}\n")
                    progress_bar['value'] += progress_increment
                    self.parent.update_idletasks()

                self.next_step()

            threading.Thread(target=log_host_statuses).start()

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.previous_step)
            back_button.pack(pady=10)
        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))
            show_return_button(self.parent)

    def install_tools(self):
        from .buttons import show_return_button

        try:
            output_text = ctk.CTkTextbox(self.parent)
            output_text.pack(fill="both", expand=True, padx=20, pady=20)
            output_text.insert(tk.END, "Installing tools on selected hosts...\n")

            progress_bar = ttk.Progressbar(self.parent, mode='determinate')
            progress_bar.pack(fill="x", padx=20, pady=10)

            def install_on_host(host):
                try:
                    if check_installation(host, self.selected_tool):
                        output_text.insert(tk.END, f"Tool {self.selected_tool} is already installed on host {host}.\n")
                    else:
                        install_tool(host, self.selected_tool, self.version)
                        log_installation(host, self.selected_tool, self.version)
                        output_text.insert(tk.END, f"Tool {self.selected_tool} installed successfully on host {host}.\n")
                except Exception as e:
                    output_text.insert(tk.END, f"Failed to install {self.selected_tool} on host {host}: {str(e)}\n")
                    console.print_exception()

            def install_on_all_hosts():
                total_hosts = len(self.selected_hosts)
                progress_increment = 100 / total_hosts

                for host in self.selected_hosts:
                    install_on_host(host)
                    progress_bar['value'] += progress_increment
                    self.parent.update_idletasks()

                output_text.insert(tk.END, "Installation process completed.\n")

            threading.Thread(target=install_on_all_hosts).start()

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.previous_step)
            back_button.pack(pady=10)
        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))
            show_return_button(self.parent)


def show_interactive_install(frame):
    InteractiveInstallWizard(frame)
