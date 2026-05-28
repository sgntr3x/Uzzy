import customtkinter as ctk
from tkinter import messagebox
import time
from . import command_builder

def open_poe_control_popup(parent_gui):
    if not parent_gui.selected_ports:
        return messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
        
    parent_gui.close_current_popup()
    popup = ctk.CTkToplevel(parent_gui.root)
    parent_gui.set_window_icon(popup)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("PoE Kontrolü")
    popup.geometry("300x200")
    
    ctk.CTkLabel(popup, text=f"Seçili {len(parent_gui.selected_ports)} Port - PoE", font=("Segoe UI", 12, "bold")).pack(pady=15)
    
    poe_state = ctk.StringVar(value="enable")
    ctk.CTkRadioButton(popup, text="AÇ (Enable)", variable=poe_state, value="enable", fg_color="#C62828").pack(anchor=ctk.W, padx=70, pady=5)
    ctk.CTkRadioButton(popup, text="KAPAT (Disable)", variable=poe_state, value="disable", fg_color="#C62828").pack(anchor=ctk.W, padx=70, pady=5)
    
    def apply_poe():
        state = poe_state.get()
        commands = command_builder.build_poe_cmds(parent_gui.selected_brand.get(), sorted(list(parent_gui.selected_ports)), state, getattr(parent_gui, 'port_mapping', None))
        for cmd in commands:
            if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
            else: parent_gui.log_to_terminal(f"{parent_gui._current_prompt}{cmd}\n")
            time.sleep(0.05)
        popup.destroy()
            
    ctk.CTkButton(popup, text="UYGULA", command=apply_poe, fg_color="#C62828", hover_color="#E53935").pack(fill=ctk.X, padx=40, pady=15)