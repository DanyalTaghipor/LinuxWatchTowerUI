import os
import sys
import customtkinter as ctk
from tkinter import ttk, messagebox
import tkinter as tk
from rich.console import Console
from ansible_utils.inventory import get_host_nicknames
from ansible_utils.roles_enum import Tools
from ansible_utils.ansible_executor import install_tool
from db.database import init_db, log_installation, log_host_status, get_host_status, update_host_status, check_installation
import paramiko
import subprocess
import time
import socket
import logging
import threading

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Console for rich logging
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
        self.steps = [
            self.config_path_step,
            self.select_host_step,
            self.select_tool_step,
            self.install_tools_step
        ]
        self.current_step = 0
        self.config_path = ''
        self.selected_hosts = []
        self.selected_tool = ''
        self.host_nicknames = []
        self.tool_list = []
        self.sudo_passwords = {}
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

    def prev_step(self):
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
        try:
            self.host_nicknames = get_host_nicknames(config_path=self.config_path)
            if not self.host_nicknames:
                messagebox.showerror("Error", "No hosts found in the SSH config file.")
                return

            table_frame = ctk.CTkFrame(self.parent)
            table_frame.pack(fill="both", expand=True)

            table = ttk.Treeview(table_frame, columns=("Number", "Host", "Accessible", "Sudo Password Needed", "Last Checked"), show='headings')
            table.heading("Number", text="Number")
            table.heading("Host", text="Host")
            table.heading("Accessible", text="Accessible")
            table.heading("Sudo Password Needed", text="Sudo Password Needed")
            table.heading("Last Checked", text="Last Checked")

            self.selected_hosts_vars = []

            for index, host in enumerate(self.host_nicknames, start=1):
                var = tk.BooleanVar()
                self.selected_hosts_vars.append((var, host))

                host_status = get_host_status(host)
                accessible, needs_sudo_password, last_checked = host_status if host_status else ("Unknown", "Unknown", "Never")
                table.insert("", "end", values=(index, host, accessible, needs_sudo_password, last_checked))

            table.pack(fill="both", expand=True)
            table.update_idletasks()

            checkbox_frame = tk.Frame(table_frame)
            checkbox_frame.place(relx=0, rely=0, relwidth=0.05, relheight=1)

            for index, child in enumerate(table.get_children(), start=1):
                bbox = table.bbox(child)
                if bbox:
                    var, host = self.selected_hosts_vars[index - 1]
                    checkbox = tk.Checkbutton(checkbox_frame, variable=var)
                    checkbox.place(x=5, y=bbox[1] + bbox[3] // 2 - checkbox.winfo_reqheight() // 2)

            def update_host_statuses():
                selected_hosts = [host for var, host in self.selected_hosts_vars if var.get()]
                if not selected_hosts:
                    messagebox.showerror("Error", "Please select at least one host.")
                    return

                def run_update_host_statuses():
                    try:
                        for var, host in self.selected_hosts_vars:
                            if var.get():
                                accessible, needs_sudo_password = self.check_host_status(host)
                                if needs_sudo_password is None:
                                    needs_sudo_password = "Unknown"
                                log_host_status(host, accessible, needs_sudo_password)
                                print(f'hoy!!! => {host} | {accessible} | {needs_sudo_password} \n')

                        messagebox.showinfo("Info", "Host statuses updated.")
                    except Exception as e:
                        print(f'hey!!! => {e}')
                        console.print_exception()
                        messagebox.showerror("Error", str(e))
                    finally:
                        progress_window.destroy()

                def create_progress_window():
                    progress_window = ctk.CTkToplevel(self.parent)
                    progress_window.title("Checking Hosts")
                    progress_window.geometry("300x100")
                    progress_label = ctk.CTkLabel(progress_window, text="Updating host statuses. Please wait...")
                    progress_label.pack(pady=20)
                    progress_window.after(100, lambda: progress_window.grab_set())
                    return progress_window

                progress_window = create_progress_window()
                threading.Thread(target=run_update_host_statuses).start()

            def on_next():
                self.selected_hosts = [host for var, host in self.selected_hosts_vars if var.get()]
                if not self.selected_hosts:
                    messagebox.showerror("Error", "Please select at least one host.")

                hosts_needing_sudo = []
                for host in self.selected_hosts:
                    status = get_host_status(host)
                    if status and status[1] == "Yes":
                        hosts_needing_sudo.append(host)

                if hosts_needing_sudo:
                    self.show_sudo_password_input(hosts_needing_sudo)
                else:
                    self.next_step()


            next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
            next_button.pack(pady=20)

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.prev_step)
            back_button.pack(pady=10)

            update_status_button = ctk.CTkButton(self.parent, text="Update Statuses", command=update_host_statuses)
            update_status_button.pack(pady=10)

        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))

    def show_sudo_password_input(self, hosts_needing_sudo):
        popup = ctk.CTkToplevel(self.parent)
        popup.title("Sudo Password Input")
        popup.geometry("400x300")

        label = ctk.CTkLabel(popup, text="Please enter sudo passwords for the following hosts:")
        label.pack(pady=10)

        entries = {}

        for host in hosts_needing_sudo:
            host_label = ctk.CTkLabel(popup, text=host)
            host_label.pack(pady=5)
            entry = ctk.CTkEntry(popup, show="*")
            entry.pack(pady=5)
            entries[host] = entry

        def on_submit():
            for host, entry in entries.items():
                self.sudo_passwords[host] = entry.get()
            popup.destroy()
            self.next_step()

        submit_button = ctk.CTkButton(popup, text="Submit", command=on_submit)
        submit_button.pack(pady=20)

    def check_host_status(self, host):
        accessible = False
        needs_sudo_password = "Unknown"

        try:
            hostname = self.get_hostname_from_host(host, self.config_path)
            accessible = self.check_host_accessibility(hostname)
            needs_sudo_password = self.check_sudo_password_requirement(host, self.config_path)
        except socket.timeout:
            console.log(f"Connection to {host} timed out")
            accessible = "Unknown"
            needs_sudo_password = "Unknown"
        except Exception as e:
            console.print_exception()
        
        return accessible, needs_sudo_password


    def select_tool_step(self):
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

            def on_next():
                self.selected_tool = self.selected_tool_var.get()
                if not self.selected_tool:
                    messagebox.showerror("Error", "Please select a tool.")
                else:
                    self.next_step()

            next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
            next_button.pack(pady=20)

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.prev_step)
            back_button.pack(pady=10)
        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))

    def install_tools_step(self):
        from .buttons import show_main_buttons
        try:
            output_text = ctk.CTkTextbox(self.parent)
            output_text.pack(fill="both", expand=True, padx=20, pady=20)
            output_text.insert(tk.END, "Installing tools on selected hosts...\n")

            progress_bar = ttk.Progressbar(self.parent, mode='determinate')
            progress_bar.pack(fill="x", padx=20, pady=10)

            def install_on_host(host):
                try:
                    sudo_password = self.sudo_passwords.get(host, None)
                    status, logs = install_tool(host, self.selected_tool, sudo_password, self.custom_roles_path)
                    log_installation(host, self.selected_tool)
                    if status == 'failed':
                        output_text.insert(tk.END, f"Failed to install {self.selected_tool} on host {host}. Logs:\n{logs}\n")
                    else:
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

                return_button = ctk.CTkButton(self.parent, text="Return to Homepage", command=lambda: show_main_buttons(self.parent))
                return_button.pack(pady=20)

            threading.Thread(target=install_on_all_hosts).start()

        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))

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

            if str(host_config['hostname']) not in ['127.0.0.1', 'localhost']:
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
