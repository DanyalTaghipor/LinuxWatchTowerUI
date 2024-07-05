import customtkinter as ctk
from tkinter import Menu
from ui.buttons import show_main_buttons
from ui.utils import display_readme
from ui.set_target import show_set_target
from ui.check_state import show_check_state
from ui.interactive_install_wizard import show_interactive_install

def main():
    app = ctk.CTk()
    app.title("Taikuri")
    app.geometry("800x600")

    # Create a menu bar using standard Tkinter
    menu_bar = Menu(app)
    app.config(menu=menu_bar)

    # Add menu items
    file_menu = Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Set Target", command=lambda: show_set_target(main_frame))
    file_menu.add_command(label="Interactive Install", command=lambda: show_interactive_install(main_frame))
    file_menu.add_command(label="Check State", command=lambda: show_check_state(main_frame))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=app.quit)
    menu_bar.add_cascade(label="File", menu=file_menu)

    help_menu = Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="About", command=display_readme)

    # Create a main frame to hold content
    main_frame = ctk.CTkFrame(app)
    main_frame.pack(fill="both", expand=True)

    # Show main buttons
    show_main_buttons(main_frame)

    # Run the application
    app.mainloop()

if __name__ == "__main__":
    main()
