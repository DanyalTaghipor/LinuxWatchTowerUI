import os
import customtkinter as ctk
from tkinter import ttk, messagebox
from ansible_utils.inventory import get_host_nicknames
from ansible_utils.roles_enum import Tools
from ansible_utils.check_tool import check_tool_remote
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
                    
                    state_table = ttk.Treeview(state_frame, columns=("Number", "Tool", "State"), show='headings')
                    state_table.heading("Number", text="Number")
                    state_table.heading("Tool", text="Tool")
                    state_table.heading("State", text="State")
                    
                    tool_list = get_available_tools(custom_roles_path=custom_roles_path)

                    for index, tool in enumerate(tool_list, start=1):
                        state = check_tool_remote(selected_host, tool.name)
                        state_table.insert("", "end", values=(index, tool.name, state))
                    
                    state_table.pack(fill="both", expand=True)
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
