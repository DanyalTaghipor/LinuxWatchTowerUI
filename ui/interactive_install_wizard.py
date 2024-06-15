import os
import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
from rich.console import Console
from ansible_utils.inventory import get_host_nicknames
from ansible_utils.roles_enum import Tools
from ansible_utils.ansible_executor import install_tool
from ansible_utils.check_tool import check_tool_remote
from db.database import init_db, log_installation, check_installation
import paramiko
import subprocess
import time
import paramiko.config
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

class InteractiveInstallWizard:

    def __init__(self, parent):
        self.parent = parent
        self.steps = [self.config_path_step, self.select_host_step, self.select_tool_step, self.check_tool_status_step]
        self.current_step = 0
        self.config_path = ''
        self.selected_host = ''
        self.selected_tool = ''
        self.version = ''
        self.host_nicknames = []
        self.tool_list = list(Tools)
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

        def on_next():
            self.config_path = config_path_entry.get() or default_config_path
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
                tool_table.insert("", "end", values=(index, tool.name))

            tool_table.pack(fill="both", expand=True)

            def on_next():
                try:
                    selected_tool_item = tool_table.selection()[0]
                    self.selected_tool = tool_table.item(selected_tool_item, "values")[1]
                    self.check_tool_status_step()
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
        status_frame = ctk.CTkFrame(self.parent)
        status_frame.pack(fill="both", expand=True)

        status_table = ttk.Treeview(status_frame, columns=("Host", "Hostname", "Accessible", "Sudo Password Required", "Password"), show='headings')
        status_table.heading("Host", text="Host")
        status_table.heading("Hostname", text="Hostname")
        status_table.heading("Accessible", text="Accessible")
        status_table.heading("Sudo Password Required", text="Sudo Password Required")
        status_table.heading("Password", text="Password")

        self.sudo_passwords = {}

        for host, hostname, accessible, needs_sudo_password in status_info:
            password_var = tk.StringVar()
            self.sudo_passwords[host] = password_var

            if needs_sudo_password:
                password_entry = ctk.CTkEntry(status_frame, textvariable=password_var, show="*")
            else:
                password_entry = ctk.CTkEntry(status_frame, textvariable=password_var, state='readonly')

            status_table.insert("", "end", values=(host, hostname, "Yes" if accessible else "No", "Yes" if needs_sudo_password else "No"))

            status_table.pack(fill="both", expand=True)
            status_table.update_idletasks()

            bbox = status_table.bbox(status_table.get_children()[-1])
            password_entry.place(x=bbox[0] + bbox[2] - 100, y=bbox[1] + bbox[3]//2 - password_entry.winfo_reqheight()//2)

        def on_finish():
            for host, hostname, accessible, needs_sudo_password in status_info:
                if accessible:
                    role_name = Tools[self.selected_tool].value['default']
                    sudo_password = self.sudo_passwords[host].get() if needs_sudo_password else None
                    try:
                        console.log(f"Installing tool {self.selected_tool} on host {host} with role {role_name}")
                        install_tool([host], role_name, sudo_password=sudo_password)
                        log_installation(host, self.selected_tool, "latest")
                    except Exception as e:
                        console.print_exception()
                        messagebox.showerror("Installation Error", f"Failed to install tool on {host}: {e}")

            messagebox.showinfo("Status", "Check the status of the installation on the hosts.")
            show_main_buttons(self.parent)

        finish_button = ctk.CTkButton(self.parent, text="Finish", command=on_finish)
        finish_button.pack(pady=20)

        back_button = ctk.CTkButton(self.parent, text="Back", command=self.previous_step)
        back_button.pack(pady=10)

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
