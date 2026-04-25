import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import customtkinter as ctk
import time
import threading
import os
import re

try:
    from PIL import Image, ImageTk, ImageDraw, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Uzzy Modüllerinin İçe Aktarılması
from modules import mac_table
from modules import command_builder
from modules import ai_config
from modules import switch_configs
from modules import poe_config
from modules import config_diff
import uzzy_backend

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class UzzyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Uzzy Serial Terminal")
        self.root.geometry("1280x750")

        # State (Durum Değişkenleri)
        self.selected_brand = ctk.StringVar(value="Cisco")
        self.port_count_var = ctk.StringVar(value="48")
        
        # Servisleri Backend'den Çağır
        self.scanner = uzzy_backend.UzzyScanner()
        self.scanner.start()
        self.serial_conn = uzzy_backend.UzzySerialConnection(baudrate=115200)
        self.active_popup = None
        self.capture_filepath = None

        # --- LAYOUT (YERLEŞİM) ---
        
        # 1. Üst Toolbar (Marka Seçimi ve Aksiyonlar)
        self.top_toolbar = ctk.CTkFrame(root, fg_color="#2D2D30", corner_radius=0)
        self.top_toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Marka Seçimi (Sol Taraf)
        brand_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        brand_frame.pack(side=tk.LEFT, padx=15, pady=10)
        ctk.CTkLabel(brand_frame, text="MARKA:", text_color="#A0A0A0", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        brands = ["Cisco", "Allied Telesis", "Ruijie", "HPE Aruba"]
        self.brand_menu = ctk.CTkOptionMenu(brand_frame, variable=self.selected_brand, values=brands, fg_color="#3C3C3C", button_color="#505050")
        self.brand_menu.pack(side=tk.LEFT, padx=2)
            
        # Port Sayısı Seçimi (Orta/Sol Taraf)
        port_count_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        port_count_frame.pack(side=tk.LEFT, padx=10, pady=10)
        ctk.CTkLabel(port_count_frame, text="PORT SAYISI:", text_color="#A0A0A0", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        
        port_counts = ["8", "12", "16", "24", "28", "48", "52"]
        self.port_count_menu = ctk.CTkOptionMenu(port_count_frame, variable=self.port_count_var, values=port_counts, command=lambda _: self.draw_port_panel(), fg_color="#3C3C3C", button_color="#505050")
        self.port_count_menu.pack(side=tk.LEFT, padx=2)

        self.btn_auto_port = ctk.CTkButton(port_count_frame, text="Otomatik Algıla", fg_color="#F39C12", hover_color="#D68910", 
                                           font=("Segoe UI", 12, "bold"), width=100, command=self.auto_detect_ports)
        self.btn_auto_port.pack(side=tk.LEFT, padx=10)

        # AI Butonu (Port sayısı ile Yenile butonu arası)
        ai_button_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        ai_button_frame.pack(side=tk.LEFT, padx=15, pady=10)
        
        self.btn_ai = ctk.CTkButton(ai_button_frame, text="✨ AI Config", fg_color="#8E44AD", hover_color="#9B59B6",
                                    font=("Segoe UI", 12, "bold"), command=lambda: ai_config.open_ai_config_popup(self))
        self.btn_ai.pack(side=tk.LEFT)

        # Aksiyon Butonları (Sağ Taraf)
        action_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        action_frame.pack(side=tk.RIGHT, padx=15, pady=10)
        
        self.btn_refresh = ctk.CTkButton(action_frame, text="⟳ Yenile", fg_color="#0277BD", hover_color="#01579B", 
                                         font=("Segoe UI", 12, "bold"), width=80, command=self.refresh_connection)
        self.btn_refresh.pack(side=tk.LEFT, padx=5)
        
        self.btn_download_cfg = ctk.CTkButton(action_frame, text="📥 Config İndir", fg_color="#2E7D32", hover_color="#1B5E20", 
                                              font=("Segoe UI", 12, "bold"), width=100, command=self.start_config_backup)
        self.btn_download_cfg.pack(side=tk.LEFT, padx=5)

        self.btn_select_all = ctk.CTkButton(action_frame, text="Tümünü Seç", fg_color="#505050", hover_color="#606060", 
                                            font=("Segoe UI", 12, "bold"), width=90, command=self.select_all_ports)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ctk.CTkButton(action_frame, text="Temizle", fg_color="#505050", hover_color="#606060", 
                                       font=("Segoe UI", 12, "bold"), width=70, command=self.clear_port_selection)
        self.btn_clear.pack(side=tk.LEFT, padx=5)
        
        self.btn_config = ctk.CTkButton(action_frame, text="Config ▼", fg_color="#C62828", hover_color="#E53935", 
                                        font=("Segoe UI", 12, "bold"), width=80)
        
        self.config_menu = tk.Menu(self.root, tearoff=0, bg="#3C3C3C", fg="#E0E0E0", activebackground="#C62828", bd=0, font=("Segoe UI", 10))
        self.config_menu.add_command(label="VLAN Oluştur", command=lambda: switch_configs.open_create_vlan_popup(self))
        self.config_menu.add_command(label="VLAN Ata", command=lambda: switch_configs.open_assign_vlan_popup(self))
        self.config_menu.add_command(label="STP Ayarı Yap", command=lambda: switch_configs.open_stp_config_popup(self))
        self.config_menu.add_command(label="Management IP Ata", command=lambda: switch_configs.open_management_ip_popup(self))
        self.config_menu.add_command(label="PoE Kontrolü", command=lambda: poe_config.open_poe_control_popup(self))
        self.config_menu.add_separator()
        self.config_menu.add_command(label="Port Aç/Kapa", command=lambda: switch_configs.open_port_control_popup_new(self))
        self.config_menu.add_command(label="Portları Sıfırla (Default)", command=lambda: switch_configs.apply_default_port_settings(self))
        self.config_menu.add_separator()
        self.config_menu.add_command(label="MAC Adres Listesi", command=lambda: mac_table.open_mac_table_popup(self))
        self.config_menu.add_command(label="Config Karşılaştırma (Diff)", command=lambda: config_diff.open_diff_tool(self))
        
        def show_config_menu(event):
            self.config_menu.post(event.x_root, event.y_root + 15)
        self.btn_config.bind("<Button-1>", show_config_menu)
        self.btn_config.pack(side=tk.LEFT, padx=5)

        # 2. Port Görünümü (Fiziksel Switch Paneli)
        self.port_container = ctk.CTkFrame(root, fg_color="#1E1E1E", corner_radius=0)
        self.port_container.pack(side=tk.TOP, fill=tk.X, padx=15, pady=10)
        ctk.CTkLabel(self.port_container, text="FİZİKSEL PORT GÖRÜNÜMÜ (Sürükleyerek Çoklu Seçim Yapabilirsiniz)", text_color="#888888", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        self.switch_panel = tk.Frame(self.port_container, bg="#0A0A0A", padx=15, pady=15, bd=2, relief=tk.GROOVE)
        self.switch_panel.pack(fill=tk.X)
        
        self.selected_ports = set()
        self.port_buttons = {}
        self.start_port_id = [None]
        self.initial_snapshot = [set()]
        self.drag_mode = [None]
        
        self.draw_port_panel()

        # 3. Ana Orta Alan (Terminal)
        self.main_container = ctk.CTkFrame(root, fg_color="transparent")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.terminal_font_size = 14

        self.terminal_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.terminal_frame.pack(padx=10, pady=(10, 5), fill=tk.BOTH, expand=True)

        self.terminal = ctk.CTkTextbox(self.terminal_frame, font=("Consolas", self.terminal_font_size), fg_color="#101010", text_color="#E0E0E0")
        self.terminal.pack(fill=tk.BOTH, expand=True)
        self.terminal.tag_config("success", foreground="#4CAF50")
        self.terminal.tag_config("error", foreground="#F44336")
        self.terminal.tag_config("info", foreground="#29B6F6")
        self.terminal.tag_config("warning", foreground="#FFA726")
        
        self.terminal.configure(state="disabled") 

        # --- KISAYOLLAR (Shortcuts) ALANI ---
        self.shortcuts_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.shortcuts_frame.pack(fill=tk.X, padx=15, pady=(0, 5))
        
        font_frame = ctk.CTkFrame(self.shortcuts_frame, fg_color="transparent")
        font_frame.pack(side=tk.RIGHT)
        ctk.CTkButton(font_frame, text="A-", fg_color="#3C3C3C", width=30, height=24, font=("Consolas", 12, "bold"), command=self.decrease_font).pack(side=tk.LEFT, padx=2)
        ctk.CTkButton(font_frame, text="A+", fg_color="#3C3C3C", width=30, height=24, font=("Consolas", 12, "bold"), command=self.increase_font).pack(side=tk.LEFT, padx=2)

        self.btn_clear_terminal = ctk.CTkButton(font_frame, text="🗑️ Temizle", fg_color="#C62828", hover_color="#E53935", height=24, font=("Segoe UI", 11, "bold"), command=self.clear_terminal)
        self.btn_clear_terminal.pack(side=tk.LEFT, padx=10)

        shortcuts = [("sh run", "show running-config"), ("sh int status", "show interfaces status"), 
                     ("sh vlan", "show vlan brief"), ("sh mac", "show mac address-table"), ("sh cdp nei", "show cdp neighbors")]
        for lbl, cmd in shortcuts:
            ctk.CTkButton(self.shortcuts_frame, text=lbl, fg_color="#3C3C3C", hover_color="#505050", height=24, font=("Consolas", 11, "bold"), command=lambda c=cmd: self.send_shortcut_command(c)).pack(side=tk.LEFT, padx=3)

        # Giriş Alanı
        self.entry_container = ctk.CTkFrame(self.main_container, fg_color="#3C3C3C", corner_radius=5)
        self.entry_container.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        ctk.CTkLabel(self.entry_container, text="Uzzy @ terminal:~$", text_color="#E53935", font=("Consolas", 11, "bold")).pack(side=tk.LEFT, padx=10, pady=5)
        self.entry = ctk.CTkEntry(self.entry_container, font=("Consolas", 12), fg_color="transparent", border_width=0)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 10), pady=5)
        self.entry.bind("<Return>", self.send_command)

        # Durum Çubuğu
        self.status_var = tk.StringVar(value="Sistem Hazır - Port Bekleniyor...")
        self.status_bar = ctk.CTkLabel(root, textvariable=self.status_var, anchor=tk.W, fg_color="#C62828", text_color="white", font=("Segoe UI", 12, "bold"))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, ipadx=10, ipady=4)

        self.mac_display_area = None
        self.check_for_data()
        self.auto_connect_service()

    def close_current_popup(self):
        if self.active_popup:
            try:
                self.active_popup.destroy()
            except:
                pass
        self.active_popup = None
        self.mac_display_area = None

    def log_to_terminal(self, message):
        self.terminal.configure(state="normal")
        
        tag = None
        msg_upper = message.upper()
        if "[HATA]" in msg_upper or "HATASI" in msg_upper or "ERROR" in msg_upper: tag = "error"
        elif "[BİLGİ]" in msg_upper or "[SİSTEM]" in msg_upper or "BAĞLANDI" in msg_upper or "BAĞLANTISI KURULDU" in msg_upper: tag = "info"
        elif "[YENİ CİHAZ]" in msg_upper or "[VLAN OLUŞTURULDU]" in msg_upper or "ATANDI]" in msg_upper or "AYARLANDI]" in msg_upper or "BAŞARIYLA" in msg_upper or "TAMAMLANDI" in msg_upper: tag = "success"
        elif "[UYARI]" in msg_upper: tag = "warning"
        
        if tag: self.terminal.insert("end", message, tag)
        else: self.terminal.insert("end", message)
            
        self.terminal.see("end")
        self.terminal.configure(state="disabled")
        
        if self.mac_display_area:
            try:
                self.mac_display_area.insert(tk.END, message)
                self.mac_display_area.see(tk.END)
            except:
                self.mac_display_area = None

    def clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", tk.END)
        self.terminal.configure(state="disabled")

    def send_command(self, event=None):
        command = self.entry.get()
        if command:
            self.log_to_terminal(f"Uzzy >> {command}\n")
            if self.serial_conn.is_connected:
                self.serial_conn.write_data(command + "\r\n")
            else:
                self.log_to_terminal(f"(Simülasyon) Komut işlendi: {command}\n")
            self.entry.delete(0, tk.END)

    def send_shortcut_command(self, cmd):
        self.log_to_terminal(f"Uzzy >> {cmd}\n")
        if self.serial_conn.is_connected:
            self.serial_conn.write_data(cmd + "\r\n")
        else:
            self.log_to_terminal(f"(Simülasyon) Komut işlendi: {cmd}\n")

    def increase_font(self):
        if self.terminal_font_size < 36:
            self.terminal_font_size += 1
            self.terminal.configure(font=("Consolas", self.terminal_font_size))

    def decrease_font(self):
        if self.terminal_font_size > 6:
            self.terminal_font_size -= 1
            self.terminal.configure(font=("Consolas", self.terminal_font_size))

    def draw_port_panel(self):
        for widget in self.switch_panel.winfo_children():
            widget.destroy()
            
        self.selected_ports.clear()
        self.port_buttons.clear()
        
        port_count = int(self.port_count_var.get())
        max_col = (port_count - 1) // 2
        
        for i in range(1, port_count + 1):
            row = 0 if i % 2 != 0 else 1
            col = (i - 1) // 2
            
            pad_x = (2, 12) if col % 4 == 3 and col != max_col else (2, 2)
            
            btn = tk.Button(self.switch_panel, text=str(i), width=3, height=1, bg="#3C3C3C", fg="#E0E0E0", 
                            font=("Consolas", 10, "bold"), bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#606060")
            btn.grid(row=row, column=col, padx=pad_x, pady=3)
            btn.bind("<Button-1>", lambda e, p=i: self.on_port_button_press(p))
            btn.bind("<B1-Motion>", self.on_port_drag)
            self.port_buttons[i] = btn

    def update_port_grid_colors(self):
        for p_id, btn in self.port_buttons.items():
            if p_id in self.selected_ports:
                btn.config(bg="#E53935", fg="white")
            else:
                btn.config(bg="#3C3C3C", fg="#E0E0E0")

    def on_port_button_press(self, p_num):
        self.start_port_id[0] = p_num
        self.initial_snapshot[0] = self.selected_ports.copy()
        if p_num in self.selected_ports:
            self.drag_mode[0] = "remove"
            self.selected_ports.remove(p_num)
        else:
            self.drag_mode[0] = "add"
            self.selected_ports.add(p_num)
        self.update_port_grid_colors()

    def auto_detect_ports(self):
        if not self.serial_conn.is_connected:
            messagebox.showwarning("Uyarı", "Lütfen önce cihaza bağlanın ve giriş yaptıysanız şifrenizi girin.")
            return
        self.log_to_terminal("\n[BİLGİ] Port sayısı otomatik algılanıyor...\n")
        
        brand = self.selected_brand.get()
        if brand == "HPE Aruba": self.serial_conn.write_data("no page\r\n")
        else: self.serial_conn.write_data("terminal length 0\r\n")
        time.sleep(0.5)
        self.serial_conn.write_data("show interfaces status\r\n")
        
        threading.Thread(target=self._analyze_port_count, daemon=True).start()

    def _analyze_port_count(self):
        time.sleep(3) 
        content = self.terminal.get("1.0", tk.END).splitlines()
        unique_ports = set()
        
        for line in content[-300:]: 
            # Cisco, Ruijie, Allied Telesis (Örn: Gi1/0/1, Te1/1, port1.0.1 vb.)
            match_standard = re.match(r'^\s*(Gi|Fa|Te|Tw|Fo|Eth|port)[a-zA-Z]*\s*((?:\d+[/.]){0,2}\d+)', line, re.IGNORECASE)
            # Aruba (Örn: "1 ", "24 ", "1/1 " - satır başındaki sadece sayılar)
            match_aruba = re.match(r'^\s*(\d+(?:/\d+)?)\s+', line)
            
            if match_standard:
                unique_ports.add(f"{match_standard.group(1).lower()}{match_standard.group(2)}")
            elif match_aruba:
                unique_ports.add(match_aruba.group(1))
                
        total_ports = len(unique_ports)
        if total_ports > 0:
            final_count = "8" if total_ports <= 8 else "12" if total_ports <= 12 else "16" if total_ports <= 16 else "24" if total_ports <= 24 else "28" if total_ports <= 28 else "48" if total_ports <= 48 else "52"
            self.port_count_var.set(final_count)
            self.root.after(0, self.draw_port_panel)
            self.log_to_terminal(f"\n[BAŞARILI] Sistem {total_ports} adet aktif fiziksel port algıladı. Arayüz {final_count} portlu yapıya güncellendi.\n")
        else:
            self.log_to_terminal("\n[HATA] Otomatik algılama başarısız oldu. Cihazın 'enable' modunda olduğuna emin olun.\n")

    def on_port_drag(self, event):
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        if widget in self.port_buttons.values():
            try:
                current_p = int(widget.cget("text"))
                start_p = self.start_port_id[0]
                if start_p is None: return
                
                port_range = set(range(min(start_p, current_p), max(start_p, current_p) + 1))
                new_selection = self.initial_snapshot[0].copy()
                
                if self.drag_mode[0] == "add":
                    new_selection.update(port_range)
                else:
                    new_selection.difference_update(port_range)
                
                if new_selection != self.selected_ports:
                    self.selected_ports.clear()
                    self.selected_ports.update(new_selection)
                    self.update_port_grid_colors()
            except: pass

    def clear_port_selection(self):
        self.selected_ports.clear()
        self.update_port_grid_colors()
        
    def select_all_ports(self):
        self.selected_ports = set(range(1, int(self.port_count_var.get()) + 1))
        self.update_port_grid_colors()

    def refresh_connection(self):
        self.log_to_terminal("\n[SİSTEM] Bağlantı yenileniyor...\n")
        if self.serial_conn.is_connected:
            self.serial_conn.disconnect()
            
        self.scanner.discovered_ports.clear()
        self.status_var.set("Sistem Hazır - Yeniden Bağlanılıyor...")

    def check_for_data(self):
        while not self.serial_conn.data_queue.empty():
            data = self.serial_conn.data_queue.get()
            self.log_to_terminal(data)
        self.root.after(50, self.check_for_data)

    def auto_connect_service(self):
        if not self.serial_conn.is_connected:
            current_ports = self.scanner.discovered_ports
            if current_ports:
                target_port = list(current_ports)[0]
                self.log_to_terminal(f"\n[OTOMATİK BAĞLANTI] {target_port} tespit edildi, bağlanılıyor...\n")
                success, msg = self.serial_conn.connect(port=target_port)
                if success:
                    self.status_var.set(f"Bağlı: {target_port} (115200 Baud)")
                    self.log_to_terminal(f"--- {target_port} BAĞLANTISI KURULDU ---\n")
                else:
                    self.status_var.set(f"Bağlantı Hatası: {target_port}")
                    self.log_to_terminal(f"[HATA] {msg}\n")
        
        elif self.serial_conn.is_connected:
            if self.serial_conn.port not in self.scanner.discovered_ports:
                self.log_to_terminal(f"\n[BİLGİ] {self.serial_conn.port} fiziksel olarak ayrıldı.\n")
                self.serial_conn.disconnect()
                self.status_var.set("Cihaz Ayrıldı - Yeni Port Bekleniyor...")

        self.root.after(1000, self.auto_connect_service)

    def start_config_backup(self):
        if not self.serial_conn.is_connected:
            messagebox.showerror("Hata", "Lütfen önce bir cihaza bağlanın.")
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Switch Config'ini Kaydet"
        )
        if not filepath:
            return
            
        try:
            self.capture_filepath = filepath
            self.capture_file_obj = open(self.capture_filepath, "w", encoding="utf-8")
            self.capture_file_obj.write(f"! --- Uzzy Config Backup | Marka: {self.selected_brand.get()} ---\n\n")
            self.is_capturing = True
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya oluşturulamadı:\n{e}")
            return

        brand = self.selected_brand.get()
        if brand == "HPE Aruba":
            self.serial_conn.write_data("no page\r\n")
        else:
            self.serial_conn.write_data("terminal length 0\r\n")
        
        self.root.after(500, lambda: self.serial_conn.write_data("show running-config\r\n"))
        
        self.log_to_terminal(f"\n[BİLGİ] Config indiriliyor... Lütfen bitene kadar bekleyin.\n")
        self.reset_capture_timer()

    def reset_capture_timer(self):
        if hasattr(self, 'capture_timer') and self.capture_timer:
            self.root.after_cancel(self.capture_timer)
        self.capture_timer = self.root.after(3000, self.stop_config_backup)

    def stop_config_backup(self):
        if getattr(self, 'is_capturing', False):
            self.is_capturing = False
            if hasattr(self, 'capture_file_obj') and self.capture_file_obj:
                self.capture_file_obj.close()
                self.capture_file_obj = None
            self.log_to_terminal(f"\n[BİLGİ] Config başarıyla kaydedildi: {self.capture_filepath}\n")
            messagebox.showinfo("Başarılı", f"Config yedeği alındı:\n{self.capture_filepath}")

def main():
    root = ctk.CTk()
    
    import sys
    def resource_path(relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    icon_path = resource_path("uzzy_icon.png")

    try:
        icon_img = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon_img)
    except Exception as e:
        print(f"İkon yüklenemedi: {e}")

    # root.withdraw() # Geliştirme aşamasında splash ekranını atlamak için kapattık
    
    app = UzzyGUI(root)
    
    def on_closing():
        app.serial_conn.disconnect()
        app.scanner.running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # --- Splash Ekranı Geçici Olarak İptal Edildi ---
    """
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)
    splash.configure(bg="#1A1A1A")
    
    try:
        splash_img = tk.PhotoImage(file=icon_path)
        if HAS_PIL:
            img = Image.open(icon_path).convert("RGBA")
            new_w = int(img.width * 0.3)
            new_h = int(img.height * 0.3)
            
            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.ANTIALIAS
                
            img = img.resize((new_w, new_h), resample_filter)
            
            mask = Image.new('L', (new_w, new_h), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, new_w, new_h), radius=int(new_w * 0.15), fill=255)
            
            r, g, b, a = img.split()
            img.putalpha(ImageChops.darker(a, mask))
            
            splash_img = ImageTk.PhotoImage(img)
        else:
            splash_img = tk.PhotoImage(file=icon_path).subsample(3, 3)

        splash_label = tk.Label(splash, image=splash_img, bg="#1A1A1A", bd=0)
        splash_label.image = splash_img
        splash_label.pack()
        
        splash.update_idletasks()
        w = splash_label.winfo_reqwidth()
        h = splash_label.winfo_reqheight()
    except Exception as e:
        print(f"Splash resmi yüklenemedi: {e}")
        w, h = 300, 300
        tk.Label(splash, text="UZZY", fg="#E53935", bg="#1A1A1A", font=("Segoe UI", 36, "bold")).pack(expand=True, fill=tk.BOTH)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    splash.geometry(f"{w}x{h}+{x}+{y}")
    
    def fade_out():
        alpha = splash.attributes("-alpha")
        if alpha > 0:
            splash.attributes("-alpha", alpha - 0.05)
            splash.after(30, fade_out)
        else:
            splash.destroy()
            root.deiconify()

    splash.after(5000, fade_out)
    splash.after(3000, fade_out)
    """

    root.mainloop()

if __name__ == "__main__":
    main()