import tkinter as tk
from tkinter import messagebox
import time
from port_grid import PortGrid

def open_default_port_popup(parent_gui):
    parent_gui.close_current_popup()
    brand = parent_gui.selected_brand.get()
    popup = tk.Toplevel(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title(f"Default Port İşlemi - {brand}")
    popup.geometry("500x550")
    popup.configure(bg="#282828")

    tk.Label(popup, text="Sıfırlanacak Portları Seçin", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 14, "bold")).pack(pady=15)
    
    grid = PortGrid(popup)

    tk.Button(popup, text="SEÇİMİ TEMİZLE", bg="#505050", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#606060", command=grid.clear).pack(pady=10, ipady=3)

    def run_action():
        if not grid.selected_ports:
            messagebox.showwarning("Uyarı", "Lütfen port seçin!")
            return
        
        if not messagebox.askyesno("Onay", "Portlar default ayarlara dönecek. Emin misiniz?"): return

        commands = []
        port_mapping = getattr(parent_gui, 'port_mapping', None)
        
        if brand == "Cisco":
            commands.append("conf t")
            for p in sorted(list(grid.selected_ports)):
                if port_mapping and p in port_mapping:
                    commands.append(f"default interface {port_mapping[p]}")
                else:
                    commands.append(f"default interface GigabitEthernet 1/0/{p}")
            commands.append("end")
        elif brand == "Allied Telesis":
            commands.append("conf t")
            for p in sorted(list(grid.selected_ports)):
                if port_mapping and p in port_mapping:
                    commands.append(f"default interface {port_mapping[p]}")
                else:
                    commands.append(f"default interface port1.0.{p}")
            commands.append("end")
        elif brand == "Ruijie":
            commands.append("configure terminal")
            for p in sorted(list(grid.selected_ports)):
                if port_mapping and p in port_mapping:
                    commands.append(f"default interface {port_mapping[p]}")
                else:
                    commands.append(f"default interface GigabitEthernet 0/{p}")
            commands.append("end")

        if parent_gui.serial_conn.is_connected:
            parent_gui.log_to_terminal(f"\n[OTOMASYON] {brand} port sıfırlama başlıyor...\n")
            for cmd in commands:
                parent_gui.serial_conn.write_data(cmd + "\r\n")
                time.sleep(0.1)
            popup.destroy()
        else:
            messagebox.showerror("Hata", "Bağlantı yok!")

    tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 11, "bold"),
              bd=0, cursor="hand2", relief=tk.FLAT, pady=10, activebackground="#E53935", command=run_action).pack(fill=tk.X, padx=50, pady=20, ipady=5)