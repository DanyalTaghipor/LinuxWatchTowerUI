import os
import sys
import socket
import time
import threading
import paramiko
import customtkinter as ctk
from tkinter import ttk, messagebox
from ansible_utils.inventory import get_host_nicknames
from .utils import clear_frame
from rich.console import Console

console = Console()

def get_available_tools(custom_roles_path=None):
    roles_dirs = [
        os.path.join(sys._MEIPASS, 'ansible_utils', 'roles'),
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

def load_ssh_config(host, config_path):
    ssh_config = paramiko.SSHConfig()
    with open(config_path) as f:
        ssh_config.parse(f)
    host_config = ssh_config.lookup(host)
    return host_config

def check_tool_remote(host, tool, config_path):
    console.log(f"Checking {tool} on {host}")
    try:
        host_config = load_ssh_config(host, config_path)
        console.log(f"Loaded SSH config for {host}: {host_config}")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        pkey = None
        if 'identityfile' in host_config:
            console.log(f"Loading private key from {host_config['identityfile'][0]}")
            pkey = paramiko.RSAKey.from_private_key_file(host_config['identityfile'][0])

        console.log(f"Connecting to {host_config['hostname']} on port {host_config.get('port', 22)} as user {host_config.get('user')}")

        ssh.connect(
            hostname=host_config['hostname'],
            port=int(host_config.get('port', 22)),
            username=host_config.get('user'),
            pkey=pkey,
            look_for_keys=True,
            timeout=10
        )

        stdin, stdout, stderr = ssh.exec_command(f"command -v {tool}")
        tool_path = stdout.read().decode().strip()
        ssh.close()

        if tool_path:
            console.log(f"{tool} is available on {host}")
            stdin, stdout, stderr = ssh.exec_command(f"{tool} --version")
            version = stdout.read().decode().strip().split("\n")[0]  # Get the first line of the version output
            return "Available", version
        else:
            console.log(f"{tool} is not available on {host}")
            return "Not Available", "N/A"
    except socket.timeout:
        console.log(f"Connection to {host} timed out")
        return "Timeout", "N/A"
    except paramiko.ssh_exception.SSHException as e:
        console.log(f"SSHException occurred: {e}")
        return f"SSH Error: {e}", "N/A"
    except Exception as e:
        console.print_exception()
        return f"Error: {e}", "N/A"

def show_check_state(frame):
    from .buttons import show_return_button, show_main_buttons

    clear_frame(frame)
    
    default_config_path = os.path.expanduser("~/.ssh/config")
    config_path_label = ctk.CTkLabel(frame, text=f"Config Path (default is {default_config_path}):")
    config_path_label.pack(pady=5)
    config_path_entry = ctk.CTkEntry(frame)
    config_path_entry.pack(pady=5)

    custom_roles_path_label = ctk.CTkLabel(frame, text="Custom Roles Path (optional):")
    custom_roles_path_label.pack(pady=5)
    custom_roles_path_entry = ctk.CTkEntry(frame)
    custom_roles_path_entry.pack(pady=5)

    def create_progress_window():
        progress_window = ctk.CTkToplevel(frame)
        progress_window.title("Checking Hosts")
        progress_window.geometry("300x100")
        progress_label = ctk.CTkLabel(progress_window, text="Checking tool statuses. Please wait...")
        progress_label.pack(pady=20)
        progress_window.after(100, lambda: progress_window.grab_set())
        return progress_window

    def start_check():
        try:
            config_path = config_path_entry.get() or default_config_path
            custom_roles_path = custom_roles_path_entry.get() or None    
            host_nicknames = get_host_nicknames(config_path=config_path)
            if not host_nicknames:
                messagebox.showerror("Error", "No hosts found in the SSH config file.")
                return
            
            clear_frame(frame)
            
            table_frame = ctk.CTkFrame(frame)
            table_frame.pack(fill="both", expand=True)
            
            table = ttk.Treeview(table_frame, columns=("Number", "Host Nickname"), show='headings')
            table.heading("Number", text="Number")
            table.heading("Host Nickname", text="Host Nickname")
            
            for index, nickname in enumerate(host_nicknames, start=1):
                table.insert("", "end", values=(index, nickname))
            
            table.pack(fill="both", expand=True)
            
            def select_host():
                try:
                    selected_item = table.selection()[0]
                    selected_host = table.item(selected_item, "values")[1]
                    
                    clear_frame(frame)
                    
                    state_frame = ctk.CTkFrame(frame)
                    state_frame.pack(fill="both", expand=True)
                    
                    state_table = ttk.Treeview(state_frame, columns=("Number", "Tool", "State", "Version"), show='headings')
                    state_table.heading("Number", text="Number")
                    state_table.heading("Tool", text="Tool")
                    state_table.heading("State", text="State")
                    state_table.heading("Version", text="Version")
                    
                    tool_list = get_available_tools(custom_roles_path=custom_roles_path)

                    def run_check_tools():
                        progress_window = create_progress_window()
                        try:
                            for index, tool in enumerate(tool_list, start=1):
                                state, version = check_tool_remote(selected_host, tool, config_path)
                                state_table.insert("", "end", values=(index, tool, state, version))
                        except Exception as e:
                            console.print_exception()
                            messagebox.showerror("Error", str(e))
                        finally:
                            progress_window.destroy()

                    threading.Thread(target=run_check_tools).start()
                    
                    state_table.pack(fill="both", expand=True)

                    return_homepage = ctk.CTkButton(frame, text="Return to Homepage", command=lambda: show_main_buttons(frame))
                    return_homepage.pack(pady=10)
                except IndexError:
                    messagebox.showerror("Error", "Please select a host.")
                except ModuleNotFoundError as mnfe:
                    console.print_exception()
                    messagebox.showerror("Error", f"Module not found: {str(mnfe)}")
                    show_return_button(frame)
                except Exception as e:
                    console.print_exception()
                    messagebox.showerror("Error", str(e))
                    show_return_button(frame)

            select_host_button = ctk.CTkButton(frame, text="Select Host", command=select_host)
            select_host_button.pack(pady=20)
            
            cancel_button = ctk.CTkButton(frame, text="Cancel", command=lambda: show_main_buttons(frame))
            cancel_button.pack(pady=10)
        
        except Exception as e:
            console.print_exception()
            messagebox.showerror("Error", str(e))
            show_return_button(frame)
    
    start_button = ctk.CTkButton(frame, text="Start Check", command=start_check)
    start_button.pack(pady=20)
    
    cancel_button = ctk.CTkButton(frame, text="Cancel", command=lambda: show_main_buttons(frame))
    cancel_button.pack(pady=10)
