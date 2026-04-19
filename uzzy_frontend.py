import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import time
import threading
import os

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
import uzzy_backend

class UzzyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Uzzy Serial Terminal")
        self.root.geometry("1000x750")
        self.root.configure(bg="#1A1A1A")

        # State (Durum Değişkenleri)
        self.selected_brand = tk.StringVar(value="Cisco")
        self.port_count_var = tk.IntVar(value=48)
        
        # Servisleri Backend'den Çağır
        self.scanner = uzzy_backend.UzzyScanner()
        self.scanner.start()
        self.serial_conn = uzzy_backend.UzzySerialConnection(baudrate=115200)
        self.active_popup = None

        # --- LAYOUT (YERLEŞİM) ---
        
        # 1. Üst Toolbar (Marka Seçimi ve Aksiyonlar)
        self.top_toolbar = tk.Frame(root, bg="#2D2D30", padx=15, pady=10)
        self.top_toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Marka Seçimi (Sol Taraf)
        brand_frame = tk.Frame(self.top_toolbar, bg="#2D2D30")
        brand_frame.pack(side=tk.LEFT)
        tk.Label(brand_frame, text="MARKA:", fg="#A0A0A0", bg="#2D2D30", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        brands = ["Cisco", "Allied Telesis", "Ruijie"]
        self.brand_menu = tk.OptionMenu(brand_frame, self.selected_brand, *brands)
        self.brand_menu.config(bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#505050", highlightthickness=0)
        self.brand_menu["menu"].config(bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9), bd=0)
        self.brand_menu.pack(side=tk.LEFT, padx=2)
            
        # Port Sayısı Seçimi (Orta/Sol Taraf)
        port_count_frame = tk.Frame(self.top_toolbar, bg="#2D2D30")
        port_count_frame.pack(side=tk.LEFT, padx=(20, 0))
        tk.Label(port_count_frame, text="PORT SAYISI:", fg="#A0A0A0", bg="#2D2D30", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        
        port_counts = [8, 12, 16, 24, 48]
        self.port_count_menu = tk.OptionMenu(port_count_frame, self.port_count_var, *port_counts, command=lambda _: self.draw_port_panel())
        self.port_count_menu.config(bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#505050", highlightthickness=0)
        self.port_count_menu["menu"].config(bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9), bd=0)
        self.port_count_menu.pack(side=tk.LEFT, padx=2)

        # AI Butonu (Port sayısı ile Yenile butonu arası)
        ai_button_frame = tk.Frame(self.top_toolbar, bg="#2D2D30")
        ai_button_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        self.btn_ai = tk.Button(ai_button_frame, text="✨ AI Config", bg="#8E44AD", fg="white", 
                                  bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#9B59B6", command=lambda: ai_config.open_ai_config_popup(self))
        self.btn_ai.pack(side=tk.LEFT, ipady=3, ipadx=8)

        # Aksiyon Butonları (Sağ Taraf)
        action_frame = tk.Frame(self.top_toolbar, bg="#2D2D30")
        action_frame.pack(side=tk.RIGHT)
        
        self.btn_refresh = tk.Button(action_frame, text="⟳ Yenile", bg="#0277BD", fg="white", 
                                     bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#01579B", command=self.refresh_connection)
        self.btn_refresh.pack(side=tk.LEFT, padx=5, ipady=3, ipadx=5)
        
        self.btn_select_all = tk.Button(action_frame, text="Tümünü Seç", bg="#505050", fg="#E0E0E0", 
                                        bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#606060", command=self.select_all_ports)
        self.btn_select_all.pack(side=tk.LEFT, padx=5, ipady=3, ipadx=5)

        self.btn_clear = tk.Button(action_frame, text="Seçimi Temizle", bg="#505050", fg="#E0E0E0", 
                                   bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#606060", command=self.clear_port_selection)
        self.btn_clear.pack(side=tk.LEFT, padx=5, ipady=3, ipadx=5)
        
        self.btn_config = tk.Menubutton(action_frame, text="Config ▼", bg="#C62828", fg="white", 
                                        bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#E53935", activeforeground="white")
        self.config_menu = tk.Menu(self.btn_config, tearoff=0, bg="#3C3C3C", fg="#E0E0E0", activebackground="#C62828", bd=0)
        self.config_menu.add_command(label="VLAN Oluştur", command=lambda: switch_configs.open_create_vlan_popup(self))
        self.config_menu.add_command(label="VLAN Ata", command=lambda: switch_configs.open_assign_vlan_popup(self))
        self.config_menu.add_command(label="STP Ayarı Yap", command=lambda: switch_configs.open_stp_config_popup(self))
        self.config_menu.add_command(label="Management IP Ata", command=lambda: switch_configs.open_management_ip_popup(self))
        self.config_menu.add_separator()
        self.config_menu.add_command(label="Port Aç/Kapa", command=lambda: switch_configs.open_port_control_popup_new(self))
        self.config_menu.add_command(label="Portları Sıfırla (Default)", command=lambda: switch_configs.apply_default_port_settings(self))
        self.btn_config.config(menu=self.config_menu)
        self.btn_config.pack(side=tk.LEFT, padx=5, ipady=3, ipadx=10)
        self.config_menu.add_separator()
        self.config_menu.add_command(label="MAC Adres Listesi", command=lambda: mac_table.open_mac_table_popup(self))

        # 2. Port Görünümü (Fiziksel Switch Paneli)
        self.port_container = tk.Frame(root, bg="#1E1E1E", padx=15, pady=10)
        self.port_container.pack(side=tk.TOP, fill=tk.X)
        tk.Label(self.port_container, text="FİZİKSEL PORT GÖRÜNÜMÜ (Sürükleyerek Çoklu Seçim Yapabilirsiniz)", fg="#888888", bg="#1E1E1E", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        self.switch_panel = tk.Frame(self.port_container, bg="#0A0A0A", padx=15, pady=15, bd=2, relief=tk.GROOVE)
        self.switch_panel.pack(fill=tk.X)
        
        self.selected_ports = set()
        self.port_buttons = {}
        self.start_port_id = [None]
        self.initial_snapshot = [set()]
        self.drag_mode = [None]
        
        self.draw_port_panel()

        # 3. Ana Orta Alan (Terminal)
        self.main_container = tk.Frame(root, bg="#1A1A1A")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.terminal_font_size = 11

        self.terminal_frame = tk.Frame(self.main_container, bg="#1A1A1A")
        self.terminal_frame.pack(padx=10, pady=(10, 5), fill=tk.BOTH, expand=True)

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure("Dark.Vertical.TScrollbar", 
                        background="#3C3C3C", troughcolor="#1A1A1A", bordercolor="#1A1A1A", 
                        arrowcolor="#A0A0A0", lightcolor="#3C3C3C", darkcolor="#3C3C3C", gripcount=0)
        style.map("Dark.Vertical.TScrollbar",
                  background=[('active', '#505050'), ('pressed', '#606060')])

        self.terminal = tk.Text(
            self.terminal_frame, bg="#101010", fg="#E0E0E0", 
            insertbackground="white", font=("Consolas", self.terminal_font_size), selectbackground="#C62828", bd=0
        )
        self.scrollbar = ttk.Scrollbar(self.terminal_frame, orient="vertical", command=self.terminal.yview, style="Dark.Vertical.TScrollbar")
        self.terminal.configure(yscrollcommand=self.scrollbar.set)
        
        self.terminal.place(x=0, y=0, relwidth=1.0, relheight=1.0, width=-15)
        self.scrollbar.place(relx=1.0, y=0, relheight=1.0, anchor="ne", width=15)
        self.terminal.config(state=tk.DISABLED) 

        # --- KISAYOLLAR (Shortcuts) ALANI ---
        self.shortcuts_frame = tk.Frame(self.main_container, bg="#1A1A1A")
        self.shortcuts_frame.pack(fill=tk.X, padx=15, pady=(0, 5))
        
        font_frame = tk.Frame(self.shortcuts_frame, bg="#1A1A1A")
        font_frame.pack(side=tk.RIGHT)
        tk.Button(font_frame, text="A-", bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Consolas", 9, "bold"), cursor="hand2", activebackground="#505050", command=self.decrease_font).pack(side=tk.LEFT, padx=2, ipady=2, ipadx=4)
        tk.Button(font_frame, text="A+", bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Consolas", 9, "bold"), cursor="hand2", activebackground="#505050", command=self.increase_font).pack(side=tk.LEFT, padx=2, ipady=2, ipadx=4)

        tk.Button(self.shortcuts_frame, text="sh run", bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Consolas", 9, "bold"), cursor="hand2", activebackground="#505050", command=lambda: self.send_shortcut_command("show running-config")).pack(side=tk.LEFT, padx=(0, 5), ipady=2, ipadx=5)
        tk.Button(self.shortcuts_frame, text="sh int status", bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Consolas", 9, "bold"), cursor="hand2", activebackground="#505050", command=lambda: self.send_shortcut_command("show interfaces status")).pack(side=tk.LEFT, padx=5, ipady=2, ipadx=5)
        tk.Button(self.shortcuts_frame, text="sh vlan", bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Consolas", 9, "bold"), cursor="hand2", activebackground="#505050", command=lambda: self.send_shortcut_command("show vlan brief")).pack(side=tk.LEFT, padx=5, ipady=2, ipadx=5)
        tk.Button(self.shortcuts_frame, text="sh mac", bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Consolas", 9, "bold"), cursor="hand2", activebackground="#505050", command=lambda: self.send_shortcut_command("show mac address-table")).pack(side=tk.LEFT, padx=5, ipady=2, ipadx=5)
        tk.Button(self.shortcuts_frame, text="sh cdp nei", bg="#3C3C3C", fg="#E0E0E0", bd=0, font=("Consolas", 9, "bold"), cursor="hand2", activebackground="#505050", command=lambda: self.send_shortcut_command("show cdp neighbors")).pack(side=tk.LEFT, padx=5, ipady=2, ipadx=5)

        # Giriş Alanı
        self.entry_container = tk.Frame(self.main_container, bg="#282828", bd=1, relief=tk.FLAT)
        self.entry_container.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        self.entry_inner_frame = tk.Frame(self.entry_container, bg="#3C3C3C", padx=10, pady=5)
        self.entry_inner_frame.pack(fill=tk.X, expand=True)
        
        self.prompt_label = tk.Label(
            self.entry_inner_frame, text="Uzzy @ terminal:~$", 
            fg="#E53935", bg="#3C3C3C", font=("Consolas", 10, "bold")
        )
        self.prompt_label.pack(side=tk.LEFT)
        
        self.entry = tk.Entry(
            self.entry_inner_frame, bg="#3C3C3C", fg="#E0E0E0", 
            insertbackground="white", font=("Consolas", 11), relief=tk.FLAT, borderwidth=0, width=1
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.entry.bind("<Return>", self.send_command)

        # Durum Çubuğu
        self.status_var = tk.StringVar(value="Sistem Hazır - Port Bekleniyor...")
        self.status_bar = tk.Label(root, textvariable=self.status_var, bd=0, relief=tk.FLAT, anchor=tk.W, bg="#C62828", fg="white", font=("Segoe UI", 9, "bold"), padx=10)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, ipady=4)

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
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, message)
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)
        
        if self.mac_display_area:
            try:
                self.mac_display_area.insert(tk.END, message)
                self.mac_display_area.see(tk.END)
            except:
                self.mac_display_area = None

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
            self.terminal.config(font=("Consolas", self.terminal_font_size))

    def decrease_font(self):
        if self.terminal_font_size > 6:
            self.terminal_font_size -= 1
            self.terminal.config(font=("Consolas", self.terminal_font_size))

    def draw_port_panel(self):
        for widget in self.switch_panel.winfo_children():
            widget.destroy()
            
        self.selected_ports.clear()
        self.port_buttons.clear()
        
        port_count = self.port_count_var.get()
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
        self.selected_ports = set(range(1, self.port_count_var.get() + 1))
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

def main():
    root = tk.Tk()
    
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

    root.withdraw()
    
    app = UzzyGUI(root)
    
    def on_closing():
        app.serial_conn.disconnect()
        app.scanner.running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    
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

    root.mainloop()

if __name__ == "__main__":
    main()