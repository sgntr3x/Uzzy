import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, simpledialog
import time
import threading
import os
import ipaddress
import traceback

try:
    from PIL import Image, ImageTk, ImageDraw, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import google.generativeai as genai
    HAS_GEMINI = True
    GEMINI_ERR = ""
except Exception:
    HAS_GEMINI = False
    GEMINI_ERR = traceback.format_exc()

# Uzzy Modüllerinin İçe Aktarılması
import default_port
import vlan_config
import mac_table
import command_builder
import uzzy_backend
import get_api_key

if HAS_GEMINI:
    try:
        GEMINI_API_KEY = get_api_key.GEMINI_API_KEY
        if GEMINI_API_KEY and GEMINI_API_KEY != "BURAYA_API_KEY_GIRIN":
            genai.configure(api_key=GEMINI_API_KEY)
        else:
            print("Uyarı: 'get_api_key.py' içerisinde geçerli bir API anahtarı bulunamadı.")
    except Exception as e:
        print(f"Gemini API yapılandırılırken hata oluştu: {e}")

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
                                  bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2", activebackground="#9B59B6", command=self.open_ai_config_popup)
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
        self.config_menu.add_command(label="VLAN Oluştur", command=self.open_create_vlan_popup)
        self.config_menu.add_command(label="VLAN Ata", command=self.open_assign_vlan_popup)
        self.config_menu.add_command(label="STP Ayarı Yap", command=self.open_stp_config_popup)
        self.config_menu.add_command(label="Management IP Ata", command=self.open_management_ip_popup)
        self.config_menu.add_separator()
        self.config_menu.add_command(label="Port Aç/Kapa", command=self.open_port_control_popup_new)
        self.config_menu.add_command(label="Portları Sıfırla (Default)", command=self.apply_default_port_settings)
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

    def open_ai_config_popup(self):
        if not HAS_GEMINI:
            messagebox.showerror("Eksik Kütüphane", f"AI kütüphanesi yüklenirken içsel bir hata oluştu:\n\n{GEMINI_ERR}\n\nBu durum genellikle PyInstaller paketlemesinde alt modüllerin eksik kalmasından kaynaklanır.")
            return
            
        if not get_api_key.GEMINI_API_KEY or get_api_key.GEMINI_API_KEY == "BURAYA_API_KEY_GIRIN":
            messagebox.showerror("API Anahtarı Eksik", "Lütfen 'get_api_key.py' dosyasına geçerli bir Gemini API anahtarı girin ve uygulamayı yeniden başlatın.")
            return

        self.close_current_popup()
        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        self.active_popup = popup
        popup.title("AI ile Yapılandır")
        popup.geometry("600x600")
        popup.minsize(550, 550)
        popup.configure(bg="#282828")

        tk.Label(popup, text="Yapmak istediğiniz işlemi doğal dilde açıklayın:", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 11, "bold")).pack(pady=10)
        
        input_frame = tk.Frame(popup, bg="#101010", bd=1, relief=tk.SOLID)
        input_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        user_input_text = tk.Text(input_frame, bg="#101010", fg="#E0E0E0", font=("Segoe UI", 10), insertbackground="white", bd=0, wrap=tk.WORD)
        ai_scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=user_input_text.yview, style="Dark.Vertical.TScrollbar")
        user_input_text.configure(yscrollcommand=ai_scrollbar.set)
        
        ai_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        user_input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        user_input_text.focus()
        
        user_input_text.insert("1.0", "Örnek: Seçili portları vlan 10'a access modunda ata ve portfast aç.")

        status_label = tk.Label(popup, text="", fg="#A0A0A0", bg="#282828", font=("Segoe UI", 9))
        status_label.pack(pady=5)

        def on_apply():
            user_input = user_input_text.get("1.0", tk.END).strip()
            if not user_input or "Örnek:" in user_input:
                messagebox.showwarning("Uyarı", "Lütfen geçerli bir istek girin.", parent=popup)
                return
            
            apply_button.config(state=tk.DISABLED, text="İşleniyor...")
            status_label.config(text="AI modeli ile iletişim kuruluyor, lütfen bekleyin...")
            threading.Thread(target=self._run_ai_configuration, args=(user_input, popup, apply_button, status_label), daemon=True).start()

        apply_button = tk.Button(popup, text="Yapılandırmayı Oluştur", bg="#8E44AD", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", 
                                 command=on_apply, activebackground="#9B59B6")
        apply_button.pack(fill=tk.X, padx=40, pady=10, ipady=5)

    def _run_ai_configuration(self, user_request, popup, button, status_label):
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            if not available_models:
                messagebox.showerror("Model Hatası", "API anahtarınızla kullanılabilecek hiçbir model bulunamadı.", parent=popup)
                return
                
            selected_model_name = 'models/gemini-2.5-flash'
            if selected_model_name not in available_models:
                messagebox.showerror("Model Hatası", f"API anahtarınız {selected_model_name} modelini desteklemiyor.", parent=popup)
                return
                
            model = genai.GenerativeModel(selected_model_name)
            
            brand = self.selected_brand.get()
            ports = sorted(list(self.selected_ports)) if self.selected_ports else "Hiçbiri"
            
            prompt = f"""
            Sen bir ağ yapılandırma asistanısın. Görevin, kullanıcının isteğine göre bir switch için komut dizisi oluşturmak.
            - Switch Markası: {brand}
            - Seçili Portlar: {ports}
            - Kullanıcı İsteği: '{user_request}'

            Bu bilgilere dayanarak, kullanıcının hedefine ulaşması için gereken komut dizisini oluştur.
            Komutlar belirtilen switch markası ile uyumlu olmalıdır.
            Her komut yeni bir satırda olmalıdır.
            Herhangi bir açıklama, giriş veya sonuç metni ekleme. Sadece ham komutları döndür.
            Eğer kullanıcı isteği belirsiz, tehlikeli (örneğin tüm konfigürasyonu silmek gibi) veya anlamsız ise, 'HATA:' ile başlayan bir hata mesajı döndür.
            Örnek:
            HATA: İstek anlaşılamadı.
            """
            
            response = model.generate_content(prompt)
            
            try:
                generated_text = response.text.strip()
            except ValueError:
                messagebox.showerror("Güvenlik Filtresi", f"İsteğiniz Gemini güvenlik politikaları nedeniyle reddedildi.\n\nModelin yanıtı bloklandı.", parent=popup)
                return

            if generated_text.startswith("HATA:"):
                messagebox.showerror("AI Hatası", generated_text, parent=popup)
                return

            popup.after(0, self._apply_ai_commands, generated_text, popup)

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg or "depleted" in error_msg:
                messagebox.showerror("Kota / Bakiye Doldu (429)", f"API anahtarınızın kotası veya kredisi tükenmiş.\n\nÇözüm: Yeni bir API anahtarı alın veya daha düşük bir modele geçin.\n\nGerçek Hata:\n{e}", parent=popup)
            elif "403" in error_msg or "billing" in error_msg:
                messagebox.showerror("Erişim Reddedildi (403)", f"Google API erişiminizi reddetti.\nBu bir Bölge (Lokasyon) kısıtlaması, model yetkisi veya fatura sorunu olabilir.\n\nGerçek Hata:\n{e}", parent=popup)
            else:
                messagebox.showerror("API Hatası", f"AI modeline erişilirken bir hata oluştu:\n{e}", parent=popup)
        finally:
            def reset_ui():
                button.config(state=tk.NORMAL, text="Yapılandırmayı Oluştur")
                status_label.config(text="")
            popup.after(0, reset_ui)

    def _apply_ai_commands(self, commands_text, popup):
        commands_list = [cmd.strip() for cmd in commands_text.split('\n') if cmd.strip()]
        
        if not commands_list:
            messagebox.showwarning("AI Sonucu", "AI herhangi bir komut üretmedi. Lütfen isteğinizi daha net belirtin.", parent=popup)
            return

        confirm_message = "Aşağıdaki komutlar uygulanacak. Onaylıyor musunuz?\n\n" + "\n".join(commands_list)
        confirm = messagebox.askyesno("Onay", confirm_message, parent=popup)
        
        if confirm:
            self.log_to_terminal(f"\n[AI CONFIG] '{commands_list[0]}...' komutları uygulanıyor...\n")
            for cmd in commands_list:
                if self.serial_conn.is_connected:
                    self.serial_conn.write_data(cmd + "\r\n")
                else:
                    self.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
                time.sleep(0.05)
            
            self.log_to_terminal(f"\n[AI CONFIG] Yapılandırma tamamlandı.\n")
            popup.destroy()
            self.clear_port_selection()

    def open_create_vlan_popup(self):
        self.close_current_popup()
        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        self.active_popup = popup
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
            
            if not v_id:
                messagebox.showwarning("Uyarı", "VLAN ID zorunludur!", parent=popup)
                return
                
            if ip or mask:
                if not ip or not mask:
                    messagebox.showwarning("Uyarı", "IP adresi atamak için hem IP hem de Subnet Mask girilmelidir!", parent=popup)
                    return
                try:
                    ipaddress.IPv4Address(ip)
                except ValueError:
                    messagebox.showerror("Hata", "Geçersiz bir IP Adresi girdiniz! Lütfen doğru formatta girin (Örn: 192.168.1.10)", parent=popup)
                    return
                try:
                    ipaddress.IPv4Address(mask)
                except ValueError:
                    messagebox.showerror("Hata", "Geçersiz bir Subnet Mask girdiniz! (Örn: 255.255.255.0)", parent=popup)
                    return
                
            brand = self.selected_brand.get()
            commands = command_builder.build_create_vlan_cmds(brand, v_id, v_name, ip, mask)

            for cmd in commands:
                if self.serial_conn.is_connected:
                    self.serial_conn.write_data(cmd + "\r\n")
                else:
                    self.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
                time.sleep(0.05)
            
            ip_log = f" IP: {ip}" if ip else ""
            self.log_to_terminal(f"\n[VLAN OLUŞTURULDU] ID: {v_id} Name: {v_name}{ip_log}\n")
            
            vlan_id_entry.delete(0, tk.END)
            vlan_name_entry.delete(0, tk.END)
            ip_entry.delete(0, tk.END)
            mask_entry.delete(0, tk.END)
                
        tk.Button(popup, text="OLUŞTUR", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", 
                  command=apply_create, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=(10, 5), ipady=4)
                  
        tk.Button(popup, text="ÇIKIŞ", bg="#505050", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", 
                  command=popup.destroy, activebackground="#606060").pack(fill=tk.X, padx=40, pady=(0, 10), ipady=4)
                  
    def open_assign_vlan_popup(self):
        if not self.selected_ports:
            messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
            return
            
        self.close_current_popup()
        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        self.active_popup = popup
        popup.title("VLAN Ata")
        popup.geometry("350x250")
        popup.configure(bg="#282828")
        
        vlan_mode = tk.StringVar(value="Access")
        
        tk.Label(popup, text=f"Seçili {len(self.selected_ports)} Porta VLAN Ata", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 12, "bold")).pack(pady=10)
        
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
            mode = vlan_mode.get()
            
            if not v_id: return
                
            brand = self.selected_brand.get()
            ports = sorted(list(self.selected_ports))
            commands = command_builder.build_assign_vlan_cmds(brand, ports, v_id, mode)
            
            for cmd in commands:
                if self.serial_conn.is_connected:
                    self.serial_conn.write_data(cmd + "\r\n")
                else:
                    self.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
                time.sleep(0.05)
            self.log_to_terminal(f"\n[{mode.upper()} VLAN ATANDI] Portlar: {list(self.selected_ports)} VLAN: {v_id}\n")
            popup.destroy()
            self.clear_port_selection()
                
        tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", 
                  command=apply_assign, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=5, ipady=4)

    def open_stp_config_popup(self):
        if not self.selected_ports:
            messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
            return
            
        self.close_current_popup()
        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        self.active_popup = popup
        popup.title("STP Ayarları")
        popup.geometry("300x200")
        popup.configure(bg="#282828")
        
        tk.Label(popup, text=f"Seçili {len(self.selected_ports)} Port - STP", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 12, "bold")).pack(pady=15)
        
        stp_mode = tk.StringVar(value="portfast")
        tk.Radiobutton(popup, text="Portfast Aktif Et", variable=stp_mode, value="portfast", bg="#282828", fg="#E0E0E0", selectcolor="#C62828").pack(anchor=tk.W, padx=60)
        tk.Radiobutton(popup, text="BPDU Guard Aktif Et", variable=stp_mode, value="bpduguard", bg="#282828", fg="#E0E0E0", selectcolor="#C62828").pack(anchor=tk.W, padx=60)
        
        def apply_stp():
            mode = stp_mode.get()
            brand = self.selected_brand.get()
            ports = sorted(list(self.selected_ports))
            commands = command_builder.build_stp_cmds(brand, ports, mode)
            
            for cmd in commands:
                if self.serial_conn.is_connected:
                    self.serial_conn.write_data(cmd + "\r\n")
                else:
                    self.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
                time.sleep(0.05)
            self.log_to_terminal(f"\n[STP AYARLANDI] Seçili portlara {mode} uygulandı.\n")
            popup.destroy()
            self.clear_port_selection()
                
        tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", 
                  command=apply_stp, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=20, ipady=4)

    def open_management_ip_popup(self):
        self.close_current_popup()
        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        self.active_popup = popup
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
        
        tk.Label(frame, text="Port (Opsiyonel):", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 9)).grid(row=3, column=0, sticky="e", padx=5, pady=2)
        
        port_spinner_frame = tk.Frame(frame, bg="#282828")
        port_spinner_frame.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        
        selected_port = tk.StringVar(value="")
        
        def dec_port():
            val = selected_port.get()
            if val.isdigit() and int(val) > 1:
                selected_port.set(str(int(val) - 1))
            else:
                selected_port.set("")
                
        def inc_port():
            val = selected_port.get()
            max_p = self.port_count_var.get()
            if val.isdigit():
                if int(val) < max_p:
                    selected_port.set(str(int(val) + 1))
            else:
                selected_port.set("1")
                
        tk.Button(port_spinner_frame, text="-", bg="#505050", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=dec_port, width=2, activebackground="#606060").pack(side=tk.LEFT)
        tk.Entry(port_spinner_frame, textvariable=selected_port, bg="#3C3C3C", fg="#E0E0E0", insertbackground="white", bd=0, width=6, justify="center", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5, ipady=2)
        tk.Button(port_spinner_frame, text="+", bg="#505050", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=inc_port, width=2, activebackground="#606060").pack(side=tk.LEFT)
        
        def apply_mgmt():
            vid = vid_entry.get().strip()
            ip = ip_entry.get().strip()
            mask = mask_entry.get().strip()
            
            if not vid or not ip or not mask:
                messagebox.showwarning("Uyarı", "Lütfen tüm alanları doldurun!", parent=popup)
                return
                
            try:
                ipaddress.IPv4Address(ip)
                ipaddress.IPv4Address(mask)
            except ValueError:
                messagebox.showerror("Hata", "Geçersiz IP Adresi veya Subnet Mask formatı girdiniz!", parent=popup)
                return
                
            brand = self.selected_brand.get()
            port_val = selected_port.get().strip()
            port_to_assign = port_val if port_val else None
            commands = command_builder.build_management_ip_cmds(brand, vid, ip, mask, port_to_assign)

            for cmd in commands:
                if self.serial_conn.is_connected:
                    self.serial_conn.write_data(cmd + "\r\n")
                else:
                    self.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
                time.sleep(0.05)
            
            port_log = f" | Port: {port_to_assign}" if port_to_assign else ""
            self.log_to_terminal(f"\n[MANAGEMENT IP] VLAN {vid} -> IP: {ip} Mask: {mask}{port_log}\n")
            popup.destroy()
                
        tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", 
                  command=apply_mgmt, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=15, ipady=4)

    def open_port_control_popup_new(self):
        if not self.selected_ports:
            messagebox.showwarning("Uyarı", "Lütfen sol tablodan port seçin!")
            return
            
        self.close_current_popup()
        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        self.active_popup = popup
        popup.title("Port Aç / Kapat")
        popup.geometry("300x200")
        popup.configure(bg="#282828")
        
        tk.Label(popup, text=f"Seçili {len(self.selected_ports)} Portu", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 12, "bold")).pack(pady=15)
        
        port_state = tk.StringVar(value="no shutdown")
        
        tk.Radiobutton(popup, text="AÇ (no shutdown)", variable=port_state, value="no shutdown", bg="#282828", fg="#E0E0E0", selectcolor="#4CAF50").pack(anchor=tk.W, padx=70, pady=5)
        tk.Radiobutton(popup, text="KAPAT (shutdown)", variable=port_state, value="shutdown", bg="#282828", fg="#E0E0E0", selectcolor="#E53935").pack(anchor=tk.W, padx=70, pady=5)
        
        def apply_port_state():
            state = port_state.get()
            brand = self.selected_brand.get()
            ports = sorted(list(self.selected_ports))
            commands = command_builder.build_port_control_cmds(brand, ports, state)
            
            for cmd in commands:
                if self.serial_conn.is_connected:
                    self.serial_conn.write_data(cmd + "\r\n")
                else:
                    self.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
                time.sleep(0.05)
            self.log_to_terminal(f"\n[PORT KONTROL] Seçili portlara '{state}' uygulandı.\n")
            popup.destroy()
            self.clear_port_selection()
                
        tk.Button(popup, text="UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", 
                  command=apply_port_state, activebackground="#E53935").pack(fill=tk.X, padx=40, pady=15, ipady=4)

    def apply_default_port_settings(self):
        if not self.selected_ports:
            messagebox.showwarning("Uyarı", "Lütfen port panelinden port seçin!")
            return
            
        confirm = messagebox.askyesno("Onay", f"Seçili {len(self.selected_ports)} port default (fabrika) ayarlarına döndürülecek. Emin misiniz?")
        if not confirm:
            return
            
        brand = self.selected_brand.get()
        ports = sorted(list(self.selected_ports))
        commands = command_builder.build_default_port_cmds(brand, ports)
        for cmd in commands:
            if self.serial_conn.is_connected:
                self.serial_conn.write_data(cmd + "\r\n")
            else:
                self.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
            time.sleep(0.05)
            
        self.log_to_terminal(f"\n[DEFAULT PORT] Seçili {len(self.selected_ports)} port sıfırlandı.\n")
        self.clear_port_selection()

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