import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
import re

class MacTableBuffer:
    """Terminalden gelen karmaşık MAC çıktılarını süzüp Treeview Tablosuna ekleyen Akıllı Filtre"""
    def __init__(self, treeview):
        self.treeview = treeview
        self.buffer = ""

    def insert(self, index, text):
        self.buffer += text
        self.parse_buffer()

    def see(self, index):
        pass
        
    def delete(self, *args):
        self.buffer = ""
        for item in self.treeview.get_children():
            self.treeview.delete(item)

    def parse_buffer(self):
        lines = self.buffer.split('\n')
        self.buffer = lines.pop() # Son satır yarım kalmış olabilir, onu bufferta tut
        
        for line in lines:
            self.process_line(line)

    def process_line(self, line):
        line = line.strip()
        if not line: return
        
        # Allied Telesis ve standart formattaki MAC adreslerini ayıkla (Örn: 0011.2233.4455 veya 00:11:22:33:44:55)
        mac_pattern = r'([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}|(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2})'
        mac_match = re.search(mac_pattern, line)
        
        if mac_match:
            mac = mac_match.group(1)
            parts = [p for p in line.split() if p != mac]
            
            vlan, port, mtype = "-", "-", "DYNAMIC"
            for p in parts:
                if p.isdigit() and vlan == "-": vlan = p
                elif p.lower() in ["dynamic", "static", "learned", "secure", "system", "cpu", "inter-vlan"]: mtype = p.upper()
                elif "/" in p or "Gi" in p or "Fa" in p or "Te" in p or "Tw" in p or "Eth" in p or "port" in p.lower() or p.startswith("Po") or p.startswith("Trk"): port = p
                    
            self.treeview.insert("", "end", values=(vlan, mac, mtype, port))
            children = self.treeview.get_children()
            if children: self.treeview.see(children[-1]) # Otomatik en alta kaydır

def open_mac_table_popup(parent_gui):
    parent_gui.close_current_popup()
    brand = parent_gui.selected_brand.get()
    popup = ctk.CTkToplevel(parent_gui.root)
    parent_gui.set_window_icon(popup)
    parent_gui.active_popup = popup
    popup.transient(parent_gui.root)
    popup.title(f"MAC Adres Listesi - {brand}")
    popup.geometry("700x500")
    
    ctk.CTkLabel(popup, text="Aktif MAC Adres Tablosu", font=("Segoe UI", 14, "bold")).pack(pady=15)
    
    # --- Modern Treeview (Tablo) Tasarımı ---
    tree_frame = ctk.CTkFrame(popup)
    tree_frame.pack(padx=10, pady=10, fill="both", expand=True)
    
    style = ttk.Style(popup)
    style.theme_use("default")
    style.configure("Treeview", background="#2B2B2B", foreground="white", rowheight=28, fieldbackground="#2B2B2B", bordercolor="#343638", borderwidth=0, font=("Segoe UI", 11))
    style.map('Treeview', background=[('selected', '#1976D2')])
    style.configure("Treeview.Heading", background="#3C3C3C", foreground="white", relief="flat", font=("Segoe UI", 11, "bold"))
    style.map("Treeview.Heading", background=[('active', '#505050')])
    
    columns = ("VLAN", "MAC Adresi", "Tip", "Port")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", style="Treeview")
    
    tree.heading("VLAN", text="VLAN")
    tree.heading("MAC Adresi", text="MAC Adresi")
    tree.heading("Tip", text="Tip")
    tree.heading("Port", text="Port")
    
    tree.column("VLAN", width=80, anchor="center")
    tree.column("MAC Adresi", width=220, anchor="center")
    tree.column("Tip", width=120, anchor="center")
    tree.column("Port", width=150, anchor="center")
    
    scrollbar = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Gelen veriyi Treeview'a yönlendiren aracı sınıfı (Proxy) bağla
    parent_gui.mac_display_area = MacTableBuffer(tree)

    def fetch():
        parent_gui.mac_display_area.delete() # Yenilemeden önce tabloyu temizle
        cmd = "show mac address-table"
        if parent_gui.serial_conn.is_connected:
            parent_gui.log_to_terminal(f"\n[BİLGİ] MAC Tablosu çekiliyor...\n")
            parent_gui.serial_conn.write_data(cmd + "\r\n")
        else:
            messagebox.showerror("Hata", "Bağlantı yok!", parent=popup)
            
    def export_data():
        if not tree.get_children():
            return messagebox.showwarning("Uyarı", "Dışa aktarılacak veri yok!", parent=popup)
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Dosyası", "*.csv"), ("Metin Belgesi (TXT)", "*.txt")], title="MAC Tablosunu Kaydet", parent=popup)
        if not filepath: return
            
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                if filepath.lower().endswith('.txt'):
                    f.write(f"{'VLAN':<10} {'MAC Adresi':<25} {'Tip':<15} {'Port':<20}\n")
                    f.write("-" * 70 + "\n")
                    for item in tree.get_children():
                        v = tree.item(item, "values")
                        f.write(f"{v[0]:<10} {v[1]:<25} {v[2]:<15} {v[3]:<20}\n")
                else:
                    f.write("VLAN,MAC Adresi,Tip,Port\n")
                    for item in tree.get_children():
                        v = tree.item(item, "values")
                        f.write(f"{v[0]},{v[1]},{v[2]},{v[3]}\n")
            messagebox.showinfo("Başarılı", "MAC tablosu dışa aktarıldı.", parent=popup)
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya kaydedilemedi:\n{e}", parent=popup)

    btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
    btn_frame.pack(fill="x", padx=10, pady=10)

    ctk.CTkButton(btn_frame, text="SORGULA / YENİLE", fg_color="#3A3A3C", hover_color="#505055", font=("Segoe UI", 12, "bold"), command=fetch).pack(side="left", fill="x", expand=True, padx=5)
    ctk.CTkButton(btn_frame, text="DIŞA AKTAR", fg_color="#3A3A3C", hover_color="#505055", font=("Segoe UI", 12, "bold"), command=export_data).pack(side="left", fill="x", expand=True, padx=5)
    ctk.CTkButton(btn_frame, text="TEMİZLE", fg_color="#3A3A3C", hover_color="#505055", font=("Segoe UI", 12, "bold"), command=lambda: parent_gui.mac_display_area.delete()).pack(side="left", fill="x", expand=True, padx=5)

    def on_close():
        parent_gui.mac_display_area = None
        parent_gui.active_popup = None
        popup.destroy()
    popup.protocol("WM_DELETE_WINDOW", on_close)