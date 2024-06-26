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
                                update_host_status(host, accessible, needs_sudo_password)
                        messagebox.showinfo("Info", "Host statuses updated.")
                    except Exception as e:
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
                else:
                    self.next_step()

            next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
            next_button.pack(pady=20)

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.prev_step)
            back_button.pack(pady=10)

            update_status_button = ctk.CTkButton(self.parent, text="Update Statuses", command=update_host_statuses)
            update_status_button.pack(pady=10)