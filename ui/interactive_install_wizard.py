import os
import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
from rich.console import Console
from ansible_utils.inventory import get_host_nicknames
from ansible_utils.roles_enum import Tools
from ansible_utils.ansible_executor import install_tool
from db.database import init_db, log_installation
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
        self.tool_list = get_available_tools()  # Initialize with dynamic tool list
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

            for index, tool in enumerate(self.tool_list, start=1):
                tool_table.insert("", "end", values=(index, tool))

            tool_table.pack(fill="both", expand=True)

            def on_next():
                try:
                    selected_tool_item = tool_table.selection()[0]
                    self.selected_tool = tool_table.item(selected_tool_item, "values")[1]
                    self.next_step()
                except IndexError:
                    messagebox.showerror("Error", "Please select a tool.")

            next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
            next_button.pack(pady=20)

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.previous_step)
            back_button.pack(pady=10)
        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))
            show_return_button(self.parent)

    def check_tool_status_step(self):
        from .buttons import show_main_buttons, show_return_button

        def run_check_tool_status():
            try:
                status_info = []

                for host in self.selected_hosts:
                    hostname = self.get_hostname_from_host(host, self.config_path)
                    accessible = self.check_host_accessibility(hostname)
                    needs_sudo_password = self.check_sudo_password_requirement(host, self.config_path)
                    status_info.append((host, hostname, accessible, needs_sudo_password))

                self.show_status_info(status_info)
            except Exception as e:
                console.print_exception()
                messagebox.showerror("Error", str(e))
                show_return_button(self.parent)
            finally:
                progress_window.destroy()

        def create_progress_window():
            progress_window = ctk.CTkToplevel(self.parent)
            progress_window.title("Checking Hosts")
            progress_window.geometry("300x100")
            progress_label = ctk.CTkLabel(progress_window, text="Checking host status. Please wait...")
            progress_label.pack(pady=20)
            progress_window.after(100, lambda: progress_window.grab_set())
            return progress_window

        progress_window = create_progress_window()
        threading.Thread(target=run_check_tool_status).start()

    def show_status_info(self, status_info):
        from .buttons import show_main_buttons, show_return_button

        if not any(host_info[2] for host_info in status_info):
            messagebox.showerror("Error", "None of the selected hosts are available.")
            show_main_buttons(self.parent)
            return

        status_frame = ctk.CTkFrame(self.parent)
        status_frame.pack(fill="both", expand=True)

        status_table = ttk.Treeview(status_frame, columns=("Host", "Hostname", "Accessible", "Sudo Password Required"), show='headings')
        status_table.heading("Host", text="Host")
        status_table.heading("Hostname", text="Hostname")
        status_table.heading("Accessible", text="Accessible")
        status_table.heading("Sudo Password Required", text="Sudo Password Required")

        self.sudo_password_vars = {}

        status_table.pack(fill="both", expand=True)

        for host, hostname, accessible, needs_sudo_password in status_info:
            status_table.insert("", "end", values=(host, hostname, "Yes" if accessible else "No", "Yes" if needs_sudo_password else "No"))
            if needs_sudo_password:
                self.sudo_password_vars[host] = tk.StringVar()

        def on_next():
            sudo_passwords = {host: var.get() for host, var in self.sudo_password_vars.items()}

            if self.sudo_password_vars:
                self.check_sudo_passwords(sudo_passwords)
            else:
                self.on_finish(sudo_passwords)

        next_button = ctk.CTkButton(self.parent, text="Start", command=on_next)
        next_button.pack(pady=20)

        back_button = ctk.CTkButton(self.parent, text="Back", command=self.previous_step)
        back_button.pack(pady=10)

    def check_sudo_passwords(self, sudo_passwords):
        def validate_passwords():
            invalid_hosts = []

            for host, password in sudo_passwords.items():
                if not password or not self.validate_sudo_password(host, password):
                    invalid_hosts.append(host)

            if invalid_hosts:
                for host in invalid_hosts:
                    self.sudo_password_entries[host].configure(border_color="red")
                messagebox.showerror("Error", f"Invalid or missing sudo password(s) for host(s): {', '.join(invalid_hosts)}")
            else:
                self.on_finish(sudo_passwords)
            popup_window.destroy()

        def create_popup_window():
            popup_window = ctk.CTkToplevel(self.parent)
            popup_window.title("Enter Sudo Passwords")
            popup_window.geometry("300x200")

            self.sudo_password_entries = {}

            for host in self.sudo_password_vars:
                if self.sudo_password_vars[host].get() == '':
                    label = ctk.CTkLabel(popup_window, text=f"Enter sudo password for {host}:")
                    label.pack(pady=5)
                    entry = ctk.CTkEntry(popup_window, textvariable=self.sudo_password_vars[host], show='*')
                    entry.pack(pady=5)
                    self.sudo_password_entries[host] = entry

            check_button = ctk.CTkButton(popup_window, text="Check", command=validate_passwords)
            check_button.pack(pady=20)
            return popup_window

        popup_window = create_popup_window()

    def validate_sudo_password(self, host, password):
        try:
            host_config = self.load_ssh_config(host, self.config_path)

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            pkey = None
            if 'identityfile' in host_config:
                pkey = self.load_private_key(host_config['identityfile'][0])

            ssh.connect(
                hostname=host_config['hostname'],
                port=int(host_config.get('port', 22)),
                username=host_config.get('user'),
                password=password,
                pkey=pkey,
                look_for_keys=True,
                timeout=10
            )

            stdin, stdout, stderr = ssh.exec_command("echo 'sudo password valid'")
            exit_status = stdout.channel.recv_exit_status()
            ssh.close()
            return exit_status == 0
        except Exception as e:
            console.print_exception()
            return False

    def on_finish(self, sudo_passwords):
        from .buttons import show_main_buttons

        available_hosts = []
        for host in self.selected_hosts:
            hostname = self.get_hostname_from_host(host, self.config_path)
            accessible = self.check_host_accessibility(hostname)
            needs_sudo_password = self.check_sudo_password_requirement(host, self.config_path)
            sudo_password = sudo_passwords.get(host) if needs_sudo_password else None

            if accessible and (not needs_sudo_password or sudo_password):
                available_hosts.append((host, hostname, sudo_password))

        if not available_hosts:
            messagebox.showerror("Error", "No available hosts to install the tool.")
            show_main_buttons(self.parent)
            return

        for host, hostname, sudo_password in available_hosts:
            try:
                console.log(f"Installing tool {self.selected_tool} on host {host}")
                install_tool([host], self.selected_tool, sudo_password=sudo_password, custom_roles_path=self.custom_roles_path)
                log_installation(host, self.selected_tool, "latest")
            except Exception as e:
                console.print_exception()
                messagebox.showerror("Installation Error", f"Failed to install tool on {host}: {e}")

        messagebox.showinfo("Status", "Check the status of the installation on the hosts.")
        show_main_buttons(self.parent)

    def get_hostname_from_host(self, host, config_path):
        ssh_config = paramiko.config.SSHConfig()
        with open(config_path) as f:
            ssh_config.parse(f)
        host_info = ssh_config.lookup(host)
        return host_info.get("hostname")

    def check_host_accessibility(self, hostname):
        try:
            response = subprocess.run(['ping', '-c', '1', hostname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return response.returncode == 0
        except Exception as e:
            console.print_exception()
            return False

    def load_ssh_config(self, host, config_path):
        ssh_config = paramiko.SSHConfig()
        with open(config_path) as f:
            ssh_config.parse(f)
        host_config = ssh_config.lookup(host)
        return host_config

    def check_sudo_password_requirement(self, host, config_path):
        console.log(f"Checking sudo password requirement for {host}")
        try:
            host_config = self.load_ssh_config(host, config_path)
            console.log(f"Loaded SSH config for {host}: {host_config}")

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            pkey = None
            if 'identityfile' in host_config:
                console.log(f"Loading private key from {host_config['identityfile'][0]}")
                pkey = self.load_private_key(host_config['identityfile'][0])

            console.log(f"Connecting to {host_config['hostname']} on port {host_config.get('port', 22)} as user {host_config.get('user')}")

            ssh.connect(
                hostname=host_config['hostname'],
                port=int(host_config.get('port', 22)),
                username=host_config.get('user'),
                pkey=pkey,
                look_for_keys=True,
                timeout=10
            )

            ssh_transport = ssh.get_transport()
            channel = ssh_transport.open_session()
            channel.get_pty()
            channel.invoke_shell()

            time.sleep(1)
            # Read and discard the initial login messages
            while not channel.recv_ready():
                time.sleep(0.1)
            channel.recv(1024)

            console.log("Sending sudo check command")
            channel.send('sudo -n true 2>&1\n')
            time.sleep(2)
            output = channel.recv(1024).decode('utf-8')
            console.log(f"Received output: {output}")

            channel.close()
            ssh.close()

            if 'sudo:' in output or 'password' in output.lower():
                console.log(f"Sudo password required for {host}")
                return True
            console.log(f"No sudo password required for {host}")
            return False
        except socket.timeout:
            console.log(f"Connection to {host} timed out")
            return None
        except paramiko.ssh_exception.SSHException as e:
            console.log(f"SSHException occurred: {e}")
            return None
        except Exception as e:
            console.print_exception()
            return None

    def load_private_key(self, path):
        try:
            return paramiko.RSAKey.from_private_key_file(path)
        except paramiko.SSHException:
            return paramiko.Ed25519Key.from_private_key_file(path)

def show_interactive_install(frame):
    InteractiveInstallWizard(frame)
