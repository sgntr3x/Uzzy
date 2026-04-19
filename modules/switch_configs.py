import tkinter as tk
from tkinter import messagebox
import time
import ipaddress
from . import command_builder

def open_create_vlan_popup(parent_gui):
    parent_gui.close_current_popup()
    popup = tk.Toplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("VLAN Oluştur")
    popup.geometry("350x340")
    popup.configure(bg="#282828")
    
    tk.Label(popup, text="Switch Üzerinde VLAN Oluştur", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 12, "bold")).pack(pady=15)
    
    frame = tk.Frame(popup, bg="#282828")
    frame.pack(pady=5)
    
    tk.Label(frame, text="VLAN ID:", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 10)).grid(row=0, column=0, padx=5, pady=5, sticky="e")
    vlan_id_entry = tk.Entry(frame, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0, font=("Segoe UI", 10))
    vlan_id_entry.grid(row=0, column=1, padx=5, pady=5)
    
    tk.Label(frame, text="VLAN Name:", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 10)).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    vlan_name_entry = tk.Entry(frame, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0, font=("Segoe UI", 10))
    vlan_name_entry.grid(row=1, column=1, padx=5, pady=5)
    
    tk.Label(frame, text="IP Adresi (Opsiyonel):", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 10)).grid(row=2, column=0, padx=5, pady=5, sticky="e")
    ip_entry = tk.Entry(frame, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0, font=("Segoe UI", 10))
    ip_entry.grid(row=2, column=1, padx=5, pady=5)
    
    tk.Label(frame, text="Subnet Mask (Opsiyonel):", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 10)).grid(row=3, column=0, padx=5, pady=5, sticky="e")
    mask_entry = tk.Entry(frame, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0, font=("Segoe UI", 10))
    mask_entry.grid(row=3, column=1, padx=5, pady=5)
    
    def apply_create():
        v_id = vlan_id_entry.get().strip()
        v_name = vlan_name_entry.get().strip()
        ip = ip_entry.get().strip()
        mask = mask_entry.get().strip()
        
        if not v_id: return messagebox.showwarning("Uyarı", "VLAN ID zorunludur!", parent=popup)
            
        if ip or mask:
            if not ip or not mask: return messagebox.showwarning("Uyarı", "Hem IP hem de Mask girilmelidir!", parent=popup)
            try:
                ipaddress.IPv4Address(ip)
                ipaddress.IPv4Address(mask)
            except ValueError:
                return messagebox.showerror("Hata", "Geçersiz format!", parent=popup)
            
        brand = parent_gui.selected_brand.get()
        commands = command_builder.build_create_vlan_cmds(brand, v_id, v_name, ip, mask)

        for cmd in commands:
            if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
            else: parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
            time.sleep(0.05)
        
        ip_log = f" IP: {ip}" if ip else ""
        parent_gui.log_to_terminal(f"\n[VLAN OLUŞTURULDU] ID: {v_id} Name: {v_name}{ip_log}\n")
        
        vlan_id_entry.delete(0, tk.END)
        vlan_name_entry.delete(0, tk.END)
        ip_entry.delete(0, tk.END)
        mask_entry.delete(0, tk.END)
            
    tk.Button(popup, text="OLUŞTUR", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=apply_create, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=(10, 5), ipady=4)
    tk.Button(popup, text="ÇIKIŞ", bg="#505050", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=popup.destroy, activebackground="#606060").pack(fill=tk.X, padx=40, pady=(0, 10), ipady=4)
              
def open_assign_vlan_popup(parent_gui):
    if not parent_gui.selected_ports: return messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
        
    parent_gui.close_current_popup()
    popup = tk.Toplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("VLAN Ata")
    popup.geometry("350x250")
    popup.configure(bg="#282828")
    
    vlan_mode = tk.StringVar(value="Access")
    tk.Label(popup, text=f"Seçili {len(parent_gui.selected_ports)} Porta VLAN Ata", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 12, "bold")).pack(pady=10)
    mode_frame = tk.Frame(popup, bg="#282828")
    mode_frame.pack(pady=5)
    tk.Radiobutton(mode_frame, text="ACCESS", variable=vlan_mode, value="Access", bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), selectcolor="#C62828", indicatoron=0, width=12).pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(mode_frame, text="TRUNK", variable=vlan_mode, value="Trunk", bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), selectcolor="#C62828", indicatoron=0, width=12).pack(side=tk.LEFT, padx=5)
    
    frame = tk.Frame(popup, bg="#282828")
    frame.pack(pady=15)
    tk.Label(frame, text="VLAN ID (Örn: 10 veya 10,20,30):", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 9)).pack()
    vlan_id_entry = tk.Entry(frame, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0, font=("Segoe UI", 11), justify="center")
    vlan_id_entry.pack(pady=5, fill=tk.X, ipady=3)
    
    def apply_assign():
        v_id = vlan_id_entry.get().strip()
        if not v_id: return
            
        brand = parent_gui.selected_brand.get()
        ports = sorted(list(parent_gui.selected_ports))
        commands = command_builder.build_assign_vlan_cmds(brand, ports, v_id, vlan_mode.get())
        
        for cmd in commands:
            if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
            else: parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
            time.sleep(0.05)
        parent_gui.log_to_terminal(f"\n[{vlan_mode.get().upper()} VLAN ATANDI] Portlar: {list(parent_gui.selected_ports)} VLAN: {v_id}\n")
        popup.destroy()
        parent_gui.clear_port_selection()
            
    tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=apply_assign, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=5, ipady=4)

def open_stp_config_popup(parent_gui):
    if not parent_gui.selected_ports: return messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
        
    parent_gui.close_current_popup()
    popup = tk.Toplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("STP Ayarları")
    popup.geometry("300x200")
    popup.configure(bg="#282828")
    
    tk.Label(popup, text=f"Seçili {len(parent_gui.selected_ports)} Port - STP", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 12, "bold")).pack(pady=15)
    
    stp_mode = tk.StringVar(value="portfast")
    tk.Radiobutton(popup, text="Portfast Aktif Et", variable=stp_mode, value="portfast", bg="#282828", fg="#E0E0E0", selectcolor="#C62828").pack(anchor=tk.W, padx=60)
    tk.Radiobutton(popup, text="BPDU Guard Aktif Et", variable=stp_mode, value="bpduguard", bg="#282828", fg="#E0E0E0", selectcolor="#C62828").pack(anchor=tk.W, padx=60)
    
    def apply_stp():
        mode = stp_mode.get()
        brand = parent_gui.selected_brand.get()
        commands = command_builder.build_stp_cmds(brand, sorted(list(parent_gui.selected_ports)), mode)
        
        for cmd in commands:
            if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
            else: parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
            time.sleep(0.05)
        parent_gui.log_to_terminal(f"\n[STP AYARLANDI] Seçili portlara {mode} uygulandı.\n")
        popup.destroy()
        parent_gui.clear_port_selection()
            
    tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=apply_stp, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=20, ipady=4)

def open_management_ip_popup(parent_gui):
    parent_gui.close_current_popup()
    popup = tk.Toplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("Management IP Ata")
    popup.geometry("350x300")
    popup.configure(bg="#282828")
    
    tk.Label(popup, text="Management Interface Ayarı", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 11, "bold")).pack(pady=10)
    frame = tk.Frame(popup, bg="#282828")
    frame.pack(pady=5)
    
    tk.Label(frame, text="VLAN ID:", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=5, pady=2)
    vid_entry = tk.Entry(frame, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0)
    vid_entry.grid(row=0, column=1, padx=5, pady=2)
    
    tk.Label(frame, text="IP Adresi:", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="e", padx=5, pady=2)
    ip_entry = tk.Entry(frame, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0)
    ip_entry.grid(row=1, column=1, padx=5, pady=2)
    
    tk.Label(frame, text="Subnet Mask:", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 9)).grid(row=2, column=0, sticky="e", padx=5, pady=2)
    mask_entry = tk.Entry(frame, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0)
    mask_entry.grid(row=2, column=1, padx=5, pady=2)
    mask_entry.insert(0, "255.255.255.0")
    
    def apply_mgmt():
        vid = vid_entry.get().strip()
        ip = ip_entry.get().strip()
        mask = mask_entry.get().strip()
        if not vid or not ip or not mask: return messagebox.showwarning("Uyarı", "Lütfen tüm alanları doldurun!", parent=popup)
        commands = command_builder.build_management_ip_cmds(parent_gui.selected_brand.get(), vid, ip, mask, None)
        for cmd in commands:
            if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
            else: parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
            time.sleep(0.05)
        parent_gui.log_to_terminal(f"\n[MANAGEMENT IP] VLAN {vid} -> IP: {ip} Mask: {mask}\n")
        popup.destroy()
            
    tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=apply_mgmt, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=15, ipady=4)

def open_port_control_popup_new(parent_gui):
    if not parent_gui.selected_ports: return messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
    parent_gui.close_current_popup()
    popup = tk.Toplevel(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("Port Aç / Kapat")
    popup.geometry("300x200")
    popup.configure(bg="#282828")
    
    tk.Label(popup, text=f"Seçili {len(parent_gui.selected_ports)} Portu", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 12, "bold")).pack(pady=15)
    port_state = tk.StringVar(value="no shutdown")
    tk.Radiobutton(popup, text="AÇ (no shutdown)", variable=port_state, value="no shutdown", bg="#282828", fg="#E0E0E0", selectcolor="#4CAF50").pack(anchor=tk.W, padx=70, pady=5)
    tk.Radiobutton(popup, text="KAPAT (shutdown)", variable=port_state, value="shutdown", bg="#282828", fg="#E0E0E0", selectcolor="#E53935").pack(anchor=tk.W, padx=70, pady=5)
    
    def apply_port_state():
        state = port_state.get()
        for cmd in command_builder.build_port_control_cmds(parent_gui.selected_brand.get(), sorted(list(parent_gui.selected_ports)), state):
            if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
            else: parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
        parent_gui.log_to_terminal(f"\n[PORT KONTROL] Seçili portlara '{state}' uygulandı.\n")
        popup.destroy()
        parent_gui.clear_port_selection()
            
    tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=apply_port_state, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=15, ipady=4)

def apply_default_port_settings(parent_gui):
    if not parent_gui.selected_ports: return messagebox.showwarning("Uyarı", "Lütfen port panelinden port seçin!")
    if not messagebox.askyesno("Onay", f"Seçili {len(parent_gui.selected_ports)} port default ayarlarına döndürülecek. Emin misiniz?"): return
    
    for cmd in command_builder.build_default_port_cmds(parent_gui.selected_brand.get(), sorted(list(parent_gui.selected_ports))):
        if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
        else: parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
        time.sleep(0.05)
    parent_gui.log_to_terminal(f"\n[DEFAULT PORT] Seçili {len(parent_gui.selected_ports)} port sıfırlandı.\n")
    parent_gui.clear_port_selection()