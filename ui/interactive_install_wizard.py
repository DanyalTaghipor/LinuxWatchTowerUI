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

            table = ttk.Treeview(table_frame, columns=("Number", "Host Nickname"), show='headings')
            table.heading("Number", text="Number")
            table.heading("Host Nickname", text="Host Nickname")

            self.selected_hosts_vars = []

            for index, nickname in enumerate(self.host_nicknames, start=1):
                var = tk.BooleanVar()
                self.selected_hosts_vars.append((var, nickname))
                
                # Insert rows in the treeview
                table.insert("", "end", values=(index, nickname))

            table.pack(fill="both", expand=True)

            # Ensure the treeview is updated and rendered
            table.update_idletasks()

            # Create a frame to hold the checkboxes
            checkbox_frame = tk.Frame(table_frame)
            checkbox_frame.place(relx=0, rely=0, relwidth=0.05, relheight=1)

            for index, child in enumerate(table.get_children(), start=1):
                bbox = table.bbox(child)
                if bbox:
                    # Create a checkbox for each row and place it accurately
                    var, nickname = self.selected_hosts_vars[index - 1]
                    checkbox = tk.Checkbutton(checkbox_frame, variable=var)
                    checkbox.place(x=5, y=bbox[1] + bbox[3]//2 - checkbox.winfo_reqheight()//2)

            def on_next():
                self.selected_hosts = [nickname for var, nickname in self.selected_hosts_vars if var.get()]
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

        try:
            status_info = []

            # Check each host for accessibility and sudo password requirement
            for host in self.selected_hosts:
                accessible = self.check_host_accessibility(host)
                needs_sudo_password = self.check_sudo_password_requirement(host, self.config_path)
                status_info.append((host, accessible, needs_sudo_password))

            # Display installation status in a table format
            status_frame = ctk.CTkFrame(self.parent)
            status_frame.pack(fill="both", expand=True)

            status_table = ttk.Treeview(status_frame, columns=("Host", "Accessible", "Sudo Password Required"), show='headings')
            status_table.heading("Host", text="Host")
            status_table.heading("Accessible", text="Accessible")
            status_table.heading("Sudo Password Required", text="Sudo Password Required")

            for host, accessible, needs_sudo_password in status_info:
                status_table.insert("", "end", values=(host, "Yes" if accessible else "No", "Yes" if needs_sudo_password else "No"))

            status_table.pack(fill="both", expand=True)

            def on_finish():
                for host, accessible, needs_sudo_password in status_info:
                    if accessible and not needs_sudo_password:
                        role_name = Tools[self.selected_tool].value['default']
                        install_tool([host], role_name)
                        log_installation(host, self.selected_tool, "latest")

                messagebox.showinfo("Status", "Check the status of the installation on the hosts.")
                show_main_buttons(self.parent)

            finish_button = ctk.CTkButton(self.parent, text="Finish", command=on_finish)
            finish_button.pack(pady=20)

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.previous_step)
            back_button.pack(pady=10)
        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))
            show_return_button(self.parent)

    def check_host_accessibility(self, hostname):
        try:
            response = subprocess.run(['ping', '-c', '1', hostname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return response.returncode == 0
        except Exception as e:
            console.print_exception()
            return False

    def load_ssh_config(self, hostname, config_path):
        ssh_config = paramiko.SSHConfig()
        with open(config_path) as f:
            ssh_config.parse(f)
        host_config = ssh_config.lookup(hostname)
        return host_config

    def check_sudo_password_requirement(self, hostname, config_path):
        console.log(f"Checking sudo password requirement for {hostname}")
        try:
            host_config = self.load_ssh_config(hostname, config_path)
            console.log(f"Loaded SSH config for {hostname}: {host_config}")
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load private key if specified
            pkey = None
            if 'identityfile' in host_config:
                console.log(f"Loading private key from {host_config['identityfile'][0]}")
                pkey = load_private_key(host_config['identityfile'][0])

            console.log(f"Connecting to {host_config['hostname']} on port {host_config.get('port', 22)} as user {host_config.get('user')}")
            ssh.connect(
                hostname=host_config['hostname'],
                port=int(host_config.get('port', 22)),
                username=host_config.get('user'),
                pkey=pkey,
                look_for_keys=True
            )

            ssh_transport = ssh.get_transport()
            channel = ssh_transport.open_session()
            channel.get_pty()
            channel.invoke_shell()

            time.sleep(1)
            console.log("Sending sudo check command")
            channel.send('sudo -n true\n')
            time.sleep(2)
            output = channel.recv(1024).decode('utf-8')
            console.log(f"Received output: {output}")

            channel.close()
            ssh.close()

            if 'sudo:' in output:
                console.log(f"Sudo password required for {hostname}")
                return True
            console.log(f"No sudo password required for {hostname}")
            return False
        except Exception as e:
            console.print_exception()
            return None

def show_interactive_install(frame):
    InteractiveInstallWizard(frame)

def load_private_key(identityfile):
    pkey = None
    if identityfile:
        try:
            pkey = paramiko.RSAKey.from_private_key_file(identityfile)
        except paramiko.ssh_exception.SSHException:
            try:
                pkey = paramiko.ECDSAKey.from_private_key_file(identityfile)
            except paramiko.ssh_exception.SSHException:
                try:
                    pkey = paramiko.Ed25519Key.from_private_key_file(identityfile)
                except paramiko.ssh_exception.SSHException:
                    raise ValueError("Invalid key or unsupported key type.")
    return pkey
