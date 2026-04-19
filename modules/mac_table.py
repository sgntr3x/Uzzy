import tkinter as tk
from tkinter import scrolledtext, messagebox

def open_mac_table_popup(parent_gui):
    parent_gui.close_current_popup()
    brand = parent_gui.selected_brand.get()
    popup = tk.Toplevel(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title(f"MAC Adres Listesi - {brand}")
    popup.geometry("700x500")
    popup.configure(bg="#282828")
    
    tk.Label(popup, text="Aktif MAC Adres Tablosu", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 14, "bold")).pack(pady=15)
    
    parent_gui.mac_display_area = scrolledtext.ScrolledText(popup, bg="#101010", fg="#E0E0E0", font=("Consolas", 10), selectbackground="#C62828")
    parent_gui.mac_display_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    def fetch():
        cmd = "show mac-address-table" if brand == "Ruijie" else "show mac address-table"
        if parent_gui.serial_conn.is_connected:
            parent_gui.mac_display_area.insert(tk.END, f"\n> {cmd} gönderiliyor...\n")
            parent_gui.serial_conn.write_data(cmd + "\r\n")
        else:
            messagebox.showerror("Hata", "Bağlantı yok!")

    btn_frame = tk.Frame(popup, bg="#282828")
    btn_frame.pack(fill=tk.X, padx=10, pady=10)

    tk.Button(btn_frame, text="SORGULA / YENİLE", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#E53935", command=fetch, pady=10).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, ipady=3)
    tk.Button(btn_frame, text="TEMİZLE", bg="#505050", fg="#E0E0E0", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#606060", command=lambda: parent_gui.mac_display_area.delete('1.0', tk.END), pady=10).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, ipady=3)

    def on_close():
        parent_gui.mac_display_area = None
        parent_gui.active_popup = None
        popup.destroy()
    popup.protocol("WM_DELETE_WINDOW", on_close)