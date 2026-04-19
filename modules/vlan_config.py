import tkinter as tk
from tkinter import messagebox
import time
from port_grid import PortGrid

def open_vlan_assignment_popup(parent_gui):
    parent_gui.close_current_popup()
    brand = parent_gui.selected_brand.get()
    popup = tk.Toplevel(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title(f"Vlan Yapılandırması - {brand}")
    popup.geometry("500x650")
    popup.configure(bg="#282828")
    
    vlan_mode = tk.StringVar(value="Access")
    tk.Label(popup, text="Vlan Yapılandırması", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 14, "bold")).pack(pady=15)
    
    mode_frame = tk.Frame(popup, bg="#282828")
    mode_frame.pack(pady=5)
    
    all_btn = None

    def update_ui():
        if vlan_mode.get() == "Trunk": all_btn.pack(side=tk.LEFT, padx=2)
        else: all_btn.pack_forget()

    tk.Radiobutton(mode_frame, text="ACCESS", variable=vlan_mode, value="Access", 
                   bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), cursor="hand2", bd=0, selectcolor="#C62828", activebackground="#992222",
                   activeforeground="white", indicatoron=0, width=15, pady=5, command=update_ui).pack(side=tk.LEFT, padx=5, ipady=3)
    
    tk.Radiobutton(mode_frame, text="TRUNK", variable=vlan_mode, value="Trunk", 
                   bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), cursor="hand2", bd=0, selectcolor="#C62828", activebackground="#992222",
                   activeforeground="white", indicatoron=0, width=15, pady=5, command=update_ui).pack(side=tk.LEFT, padx=5, ipady=3)

    grid = PortGrid(popup)
    tk.Button(popup, text="SEÇİMİ TEMİZLE", bg="#505050", fg="#E0E0E0", font=("Segoe UI", 9, "bold"),
              bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#606060", command=grid.clear).pack(pady=10, ipady=3)

    input_frame = tk.Frame(popup, bg="#282828")
    input_frame.pack(pady=15)
    tk.Label(input_frame, text="VLAN ID:", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)
    vlan_entry = tk.Entry(input_frame, width=15, font=("Segoe UI", 12), bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0, relief=tk.FLAT)
    vlan_entry.pack(side=tk.LEFT, padx=5)

    all_btn = tk.Button(input_frame, text="ALL", bg="#505050", fg="#E0E0E0", font=("Segoe UI", 8, "bold"),
                        bd=0, cursor="hand2", relief=tk.FLAT, width=4, activebackground="#606060", command=lambda: [vlan_entry.delete(0, tk.END), vlan_entry.insert(0, "all")])
    update_ui()

    def apply():
        v_id = vlan_entry.get().strip().lower()
        mode = vlan_mode.get()
        if not grid.selected_ports or not v_id: return
        if mode == "Access" and (v_id == "all" or "," in v_id):
            messagebox.showwarning("Hata", "Access için çoklu vlan girilemez.")
            return

        if not messagebox.askyesno("Onay", f"{mode} VLAN {v_id} uygulanacak. Emin misiniz?"): return

        commands = ["configure terminal" if brand == "Ruijie" else "conf t"]
        for p in sorted(list(grid.selected_ports)):
            if brand == "Cisco": iface = f"interface GigabitEthernet 1/0/{p}"
            elif brand == "Allied Telesis": iface = f"interface port1.0.{p}"
            else: iface = f"interface GigabitEthernet 0/{p}"
            
            commands.append(iface)
            if mode == "Access":
                commands.append("switchport mode access")
                commands.append(f"switchport access vlan {v_id}")
            else:
                commands.append("switchport mode trunk")
                commands.append(f"switchport trunk allowed vlan {v_id}")
        commands.append("end")

        if parent_gui.serial_conn.is_connected:
            for cmd in commands:
                parent_gui.serial_conn.write_data(cmd + "\r\n")
                time.sleep(0.1)
            parent_gui.log_to_terminal(f"\n[VLAN] {v_id} başarıyla atandı.\n")
            popup.destroy()
        else:
            messagebox.showerror("Hata", "Bağlantı yok!")

    tk.Button(popup, text="YAPILANDIRMAYI UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 11, "bold"),
              bd=0, cursor="hand2", activebackground="#E53935", relief=tk.FLAT, pady=10, command=apply).pack(fill=tk.X, padx=50, pady=15, ipady=5)