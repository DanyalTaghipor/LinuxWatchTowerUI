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
                output_text.insert(tk.END, "Updating host statuses...\n")
                progress_bar['value'] = 0
                total_hosts = len(self.selected_hosts_vars)
                progress_increment = 100 / total_hosts

                for var, host in self.selected_hosts_vars:
                    if var.get():
                        accessible, needs_sudo_password = self.check_host_status(host)
                        update_host_status(host, accessible, needs_sudo_password)
                        output_text.insert(tk.END, f"Host: {host}, Accessible: {accessible}, Needs Sudo Password: {needs_sudo_password}\n")
                        progress_bar['value'] += progress_increment
                        self.parent.update_idletasks()

                output_text.insert(tk.END, "Host statuses updated.\n")

            def on_next():
                self.selected_hosts = [host for var, host in self.selected_hosts_vars if var.get()]
                if not self.selected_hosts:
                    messagebox.showerror("Error", "Please select at least one host.")
                else:
                    self.next_step()

            output_text = ctk.CTkTextbox(self.parent)
            output_text.pack(fill="both", expand=True, padx=20, pady=20)

            progress_bar = ttk.Progressbar(self.parent, mode='determinate')
            progress_bar.pack(fill="x", padx=20, pady=10)

            next_button = ctk.CTkButton(self.parent, text="Next", command=on_next)
            next_button.pack(pady=20)

            back_button = ctk.CTkButton(self.parent, text="Back", command=self.prev_step)
            back_button.pack(pady=10)

            update_status_button = ctk.CTkButton(self.parent, text="Update Statuses", command=update_host_statuses)
            update_status_button.pack(pady=10)