import customtkinter as ctk
from tkinter import messagebox
import time
import ipaddress
from . import command_builder

def open_create_vlan_popup(parent_gui):
    parent_gui.close_current_popup()
    popup = ctk.CTkToplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("VLAN Oluştur")
    popup.geometry("350x340")
    
    ctk.CTkLabel(popup, text="Switch Üzerinde VLAN Oluştur", font=("Segoe UI", 14, "bold")).pack(pady=15)
    
    frame = ctk.CTkFrame(popup, fg_color="transparent")
    frame.pack(pady=5)
    
    ctk.CTkLabel(frame, text="VLAN ID:", font=("Segoe UI", 12)).grid(row=0, column=0, padx=5, pady=5, sticky="e")
    vlan_id_entry = ctk.CTkEntry(frame, font=("Segoe UI", 12))
    vlan_id_entry.grid(row=0, column=1, padx=5, pady=5)
    
    ctk.CTkLabel(frame, text="VLAN Name:", font=("Segoe UI", 12)).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    vlan_name_entry = ctk.CTkEntry(frame, font=("Segoe UI", 12))
    vlan_name_entry.grid(row=1, column=1, padx=5, pady=5)
    
    ctk.CTkLabel(frame, text="IP Adresi (Opsiyonel):", font=("Segoe UI", 12)).grid(row=2, column=0, padx=5, pady=5, sticky="e")
    ip_entry = ctk.CTkEntry(frame, font=("Segoe UI", 12))
    ip_entry.grid(row=2, column=1, padx=5, pady=5)
    
    ctk.CTkLabel(frame, text="Subnet Mask (Ops):", font=("Segoe UI", 12)).grid(row=3, column=0, padx=5, pady=5, sticky="e")
    mask_entry = ctk.CTkEntry(frame, font=("Segoe UI", 12))
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
        
        vlan_id_entry.delete(0, "end")
        vlan_name_entry.delete(0, "end")
        ip_entry.delete(0, "end")
        mask_entry.delete(0, "end")
            
    ctk.CTkButton(popup, text="OLUŞTUR", fg_color="#C62828", hover_color="#E53935", font=("Segoe UI", 12, "bold"), command=apply_create).pack(fill=ctk.X, padx=40, pady=(10, 5))
    ctk.CTkButton(popup, text="ÇIKIŞ", fg_color="#505050", hover_color="#606060", font=("Segoe UI", 12, "bold"), command=popup.destroy).pack(fill=ctk.X, padx=40, pady=(0, 10))
              
def open_assign_vlan_popup(parent_gui):
    if not parent_gui.selected_ports: return messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
        
    parent_gui.close_current_popup()
    popup = ctk.CTkToplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("VLAN Ata")
    popup.geometry("350x250")
    
    vlan_mode = ctk.StringVar(value="Access")
    ctk.CTkLabel(popup, text=f"Seçili {len(parent_gui.selected_ports)} Porta VLAN Ata", font=("Segoe UI", 14, "bold")).pack(pady=10)
    mode_frame = ctk.CTkFrame(popup, fg_color="transparent")
    mode_frame.pack(pady=5)
    ctk.CTkRadioButton(mode_frame, text="ACCESS", variable=vlan_mode, value="Access", fg_color="#C62828").pack(side=ctk.LEFT, padx=15)
    ctk.CTkRadioButton(mode_frame, text="TRUNK", variable=vlan_mode, value="Trunk", fg_color="#C62828").pack(side=ctk.LEFT, padx=15)
    
    frame = ctk.CTkFrame(popup, fg_color="transparent")
    frame.pack(pady=15)
    ctk.CTkLabel(frame, text="VLAN ID (Örn: 10 veya 10,20,30):", font=("Segoe UI", 12)).pack()
    vlan_id_entry = ctk.CTkEntry(frame, font=("Segoe UI", 14), justify="center")
    vlan_id_entry.pack(pady=5, fill=ctk.X)
    
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
            
    ctk.CTkButton(popup, text="UYGULA", fg_color="#C62828", hover_color="#E53935", font=("Segoe UI", 12, "bold"), command=apply_assign).pack(fill=ctk.X, padx=40, pady=5)

def open_stp_config_popup(parent_gui):
    if not parent_gui.selected_ports: return messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
        
    parent_gui.close_current_popup()
    popup = ctk.CTkToplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("STP Ayarları")
    popup.geometry("300x200")
    
    ctk.CTkLabel(popup, text=f"Seçili {len(parent_gui.selected_ports)} Port - STP", font=("Segoe UI", 14, "bold")).pack(pady=15)
    
    stp_mode = ctk.StringVar(value="portfast")
    ctk.CTkRadioButton(popup, text="Portfast Aktif Et", variable=stp_mode, value="portfast", fg_color="#C62828").pack(anchor=ctk.W, padx=60, pady=5)
    ctk.CTkRadioButton(popup, text="BPDU Guard Aktif Et", variable=stp_mode, value="bpduguard", fg_color="#C62828").pack(anchor=ctk.W, padx=60, pady=5)
    
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
            
    ctk.CTkButton(popup, text="UYGULA", fg_color="#C62828", hover_color="#E53935", font=("Segoe UI", 12, "bold"), command=apply_stp).pack(fill=ctk.X, padx=40, pady=15)

def open_management_ip_popup(parent_gui):
    parent_gui.close_current_popup()
    popup = ctk.CTkToplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("Management IP Ata")
    popup.geometry("350x300")
    
    ctk.CTkLabel(popup, text="Management Interface Ayarı", font=("Segoe UI", 14, "bold")).pack(pady=10)
    frame = ctk.CTkFrame(popup, fg_color="transparent")
    frame.pack(pady=5)
    
    ctk.CTkLabel(frame, text="VLAN ID:", font=("Segoe UI", 12)).grid(row=0, column=0, sticky="e", padx=5, pady=2)
    vid_entry = ctk.CTkEntry(frame)
    vid_entry.grid(row=0, column=1, padx=5, pady=2)
    
    ctk.CTkLabel(frame, text="IP Adresi:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="e", padx=5, pady=2)
    ip_entry = ctk.CTkEntry(frame)
    ip_entry.grid(row=1, column=1, padx=5, pady=2)
    
    ctk.CTkLabel(frame, text="Subnet Mask:", font=("Segoe UI", 12)).grid(row=2, column=0, sticky="e", padx=5, pady=2)
    mask_entry = ctk.CTkEntry(frame)
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
            
    ctk.CTkButton(popup, text="UYGULA", fg_color="#C62828", hover_color="#E53935", font=("Segoe UI", 12, "bold"), command=apply_mgmt).pack(fill=ctk.X, padx=40, pady=15)

def open_port_control_popup_new(parent_gui):
    if not parent_gui.selected_ports: return messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
    parent_gui.close_current_popup()
    popup = ctk.CTkToplevel(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("Port Aç / Kapat")
    popup.geometry("300x200")
    
    ctk.CTkLabel(popup, text=f"Seçili {len(parent_gui.selected_ports)} Portu", font=("Segoe UI", 14, "bold")).pack(pady=15)
    port_state = ctk.StringVar(value="no shutdown")
    ctk.CTkRadioButton(popup, text="AÇ (no shutdown)", variable=port_state, value="no shutdown", fg_color="#4CAF50").pack(anchor=ctk.W, padx=70, pady=5)
    ctk.CTkRadioButton(popup, text="KAPAT (shutdown)", variable=port_state, value="shutdown", fg_color="#E53935").pack(anchor=ctk.W, padx=70, pady=5)
    
    def apply_port_state():
        state = port_state.get()
        for cmd in command_builder.build_port_control_cmds(parent_gui.selected_brand.get(), sorted(list(parent_gui.selected_ports)), state):
            if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
            else: parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
        parent_gui.log_to_terminal(f"\n[PORT KONTROL] Seçili portlara '{state}' uygulandı.\n")
        popup.destroy()
        parent_gui.clear_port_selection()
            
    ctk.CTkButton(popup, text="UYGULA", fg_color="#C62828", hover_color="#E53935", font=("Segoe UI", 12, "bold"), command=apply_port_state).pack(fill=ctk.X, padx=40, pady=15)

def apply_default_port_settings(parent_gui):
    if not parent_gui.selected_ports: return messagebox.showwarning("Uyarı", "Lütfen port panelinden port seçin!")
    if not messagebox.askyesno("Onay", f"Seçili {len(parent_gui.selected_ports)} port default ayarlarına döndürülecek. Emin misiniz?"): return
    
    for cmd in command_builder.build_default_port_cmds(parent_gui.selected_brand.get(), sorted(list(parent_gui.selected_ports))):
        if parent_gui.serial_conn.is_connected: parent_gui.serial_conn.write_data(cmd + "\r\n")
        else: parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
        time.sleep(0.05)
    parent_gui.log_to_terminal(f"\n[DEFAULT PORT] Seçili {len(parent_gui.selected_ports)} port sıfırlandı.\n")
    parent_gui.clear_port_selection()