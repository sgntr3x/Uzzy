import customtkinter as ctk
from tkinter import messagebox

def open_mac_table_popup(parent_gui):
    parent_gui.close_current_popup()
    brand = parent_gui.selected_brand.get()
    popup = ctk.CTkToplevel(parent_gui.root)
    parent_gui.active_popup = popup
    popup.transient(parent_gui.root)
    popup.title(f"MAC Adres Listesi - {brand}")
    popup.geometry("700x500")
    
    ctk.CTkLabel(popup, text="Aktif MAC Adres Tablosu", font=("Segoe UI", 14, "bold")).pack(pady=15)
    
    parent_gui.mac_display_area = ctk.CTkTextbox(popup, font=("Consolas", 12), wrap="none")
    parent_gui.mac_display_area.pack(padx=10, pady=10, fill="both", expand=True)

    def fetch():
        cmd = "show mac-address-table" if brand == "Ruijie" else "show mac address-table"
        if parent_gui.serial_conn.is_connected:
            parent_gui.mac_display_area.insert("end", f"\n> {cmd} gönderiliyor...\n")
            parent_gui.serial_conn.write_data(cmd + "\r\n")
        else:
            messagebox.showerror("Hata", "Bağlantı yok!", parent=popup)

    btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
    btn_frame.pack(fill="x", padx=10, pady=10)

    ctk.CTkButton(btn_frame, text="SORGULA / YENİLE", fg_color="#C62828", hover_color="#E53935", font=("Segoe UI", 12, "bold"), command=fetch).pack(side="left", fill="x", expand=True, padx=5)
    ctk.CTkButton(btn_frame, text="TEMİZLE", fg_color="#505050", hover_color="#606060", font=("Segoe UI", 12, "bold"), command=lambda: parent_gui.mac_display_area.delete('1.0', "end")).pack(side="left", fill="x", expand=True, padx=5)

    def on_close():
        parent_gui.mac_display_area = None
        parent_gui.active_popup = None
        popup.destroy()
    popup.protocol("WM_DELETE_WINDOW", on_close)