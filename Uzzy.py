import serial
import serial.tools.list_ports
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import time
import queue
import os
try:
    from PIL import Image, ImageTk, ImageDraw, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Yeni Modüllerin İçe Aktarılması
import default_port
import vlan_config
import mac_table

class UzzyScanner:
    def __init__(self):
        self.running = True
        self.discovered_ports = set()
        # İlk açılışta mevcut portları listeye alalım ki 
        # sadece "yeni" takılanları ayırt edebilelim.
        self.update_ports()

    def get_current_ports(self):
        """Sistemdeki aktif portları bir sözlük yapısında döner."""
        ports = serial.tools.list_ports.comports()
        return {port.device: port.description for port in ports}

    def update_ports(self):
        """Mevcut port listesini günceller."""
        current_ports_dict = self.get_current_ports()
        self.discovered_ports = set(current_ports_dict.keys())
        return current_ports_dict

    def monitor_ports_service(self):
        """Arka planda portları sürekli tarayan servis döngüsü."""
        print("--- Uzzy Port Tarama Servisi Başlatıldı ---")
        
        while self.running:
            current_ports_dict = self.get_current_ports()
            current_devices = set(current_ports_dict.keys())

            # Yeni takılan cihazları bul (Current kümesinde olup eski kümede olmayanlar)
            new_ports = current_devices - self.discovered_ports
            # Çıkarılan cihazları bul
            removed_ports = self.discovered_ports - current_devices

            if new_ports:
                for port in new_ports:
                    print(f"\n[YENİ CİHAZ] {port} algılandı!")
                    print(f"Tanım: {current_ports_dict[port]}")
                    print("-" * 30)
            
            if removed_ports:
                for port in removed_ports:
                    print(f"\n[BİLGİ] {port} bağlantısı kesildi.")
                    print("-" * 30)

            # Listeyi güncelle
            self.discovered_ports = current_devices
            
            # İşlemciyi yormamak için 1 saniye bekle
            time.sleep(1)

    def start(self):
        """Servisi ayrı bir thread üzerinde başlatır."""
        self.thread = threading.Thread(target=self.monitor_ports_service, daemon=True)
        self.thread.start()

# Yeni sınıf: Seri port bağlantısını yönetecek
class UzzySerialConnection:
    def __init__(self, port=None, baudrate=9600, timeout=1):
        self.ser = None
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_connected = False
        self.read_thread = None
        self.read_running = False
        self.data_queue = queue.Queue() # GUI'ye veri aktarmak için

    def connect(self, port=None, baudrate=None):
        if port:
            self.port = port
        if baudrate:
            self.baudrate = baudrate

        if not self.port:
            print("Hata: Bağlanmak için bir COM portu belirtilmelidir.")
            return False

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            self.is_connected = True
            print(f"[{self.port}] Bağlantı başarılı: Baudrate={self.baudrate}")
            
            # Veri okuma işlemini ayrı bir thread'de başlat
            self.read_running = True
            self.read_thread = threading.Thread(target=self._read_data_loop, daemon=True)
            self.read_thread.start()
            return True, f"Bağlandı: {self.port}"
        except serial.SerialException as e:
            error_msg = f"Hata: {e}"
            self.is_connected = False
            return False, error_msg

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.read_running = False # Okuma thread'ini durdur
            self.ser.close()
            self.is_connected = False
            print(f"[{self.port}] Bağlantı kesildi.")
        else:
            self.is_connected = False

    def _read_data_loop(self):
        """Arka planda seri porttan veri okuyan döngü."""
        while self.read_running and self.is_connected:
            try:
                if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    try:
                        decoded_data = data.decode('utf-8')
                        self.data_queue.put(decoded_data)
                    except UnicodeDecodeError:
                        # Decode hatası olursa byte olarak gönder
                        self.data_queue.put(str(data))
                time.sleep(0.01) # İşlemciyi yormamak için küçük bir bekleme
            except serial.SerialException as e:
                print(f"Hata [{self.port}] okuma sırasında: {e}")
                self.data_queue.put(f"\n[BAĞLANTI KAYBI] {e}\n")
                self.disconnect()
                break
            except Exception as e:
                print(f"Beklenmedik hata [{self.port}] okuma sırasında: {e}")
                self.data_queue.put(f"\n[HATA] {e}\n")
                self.disconnect()
                break

    def write_data(self, data):
        if self.ser and self.ser.is_open:
            try:
                # Verinin byte türünde olduğundan emin ol
                if isinstance(data, str):
                    data = data.encode('utf-8')
                self.ser.write(data)
                return True
            except serial.SerialException as e:
                print(f"Hata [{self.port}] yazma sırasında: {e}")
                return False
            except Exception as e:
                print(f"Beklenmedik hata [{self.port}] yazma sırasında: {e}")
                self.disconnect()
                return False
        else:
            print(f"[{self.port}] Bağlı değil, veri gönderilemedi.")
            return False

class UzzyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Uzzy Serial Terminal")
        self.root.geometry("800x600")
        self.root.configure(bg="#1A1A1A")

        # State (Durum Değişkenleri)
        self.selected_brand = tk.StringVar(value="Cisco")
        
        # Servisler
        self.scanner = UzzyScanner()
        self.scanner.start()
        self.serial_conn = UzzySerialConnection(baudrate=115200)
        self.active_popup = None

        # --- LAYOUT (YERLEŞİM) ---
        
        # Sol Sidebar (Aksiyonlar)
        self.left_sidebar = tk.Frame(root, bg="#282828", width=150)
        self.left_sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(self.left_sidebar, text="İŞLEMLER", fg="#A0A0A0", bg="#282828", font=("Segoe UI", 10, "bold")).pack(pady=15)
        
        self.btn_default_port = tk.Button(self.left_sidebar, text="Default Port", bg="#3C3C3C", fg="#E0E0E0", 
                                          bd=0, relief=tk.FLAT, font=("Segoe UI", 10), cursor="hand2", activebackground="#C62828", activeforeground="white", command=lambda: default_port.open_default_port_popup(self))
        self.btn_default_port.pack(fill=tk.X, padx=10, pady=5, ipady=4)
        
        self.btn_vlan_config = tk.Button(self.left_sidebar, text="Vlan Atama", bg="#3C3C3C", fg="#E0E0E0", 
                                         bd=0, relief=tk.FLAT, font=("Segoe UI", 10), cursor="hand2", activebackground="#C62828", activeforeground="white", command=lambda: vlan_config.open_vlan_assignment_popup(self))
        self.btn_vlan_config.pack(fill=tk.X, padx=10, pady=5, ipady=4)
        
        self.btn_port_control = tk.Button(self.left_sidebar, text="Port Aç/Kapa", bg="#3C3C3C", fg="#E0E0E0", 
                                          bd=0, relief=tk.FLAT, font=("Segoe UI", 10), cursor="hand2", activebackground="#C62828", activeforeground="white", command=self.open_port_control_popup)
        self.btn_port_control.pack(fill=tk.X, padx=10, pady=5, ipady=4)
        
        self.btn_mac_list = tk.Button(self.left_sidebar, text="MAC Adresleri", bg="#3C3C3C", fg="#E0E0E0", 
                                       bd=0, relief=tk.FLAT, font=("Segoe UI", 10), cursor="hand2", activebackground="#C62828", activeforeground="white", command=lambda: mac_table.open_mac_table_popup(self))
        self.btn_mac_list.pack(fill=tk.X, padx=10, pady=5, ipady=4)

        # Sağ Sidebar (Marka Seçimi)
        self.right_sidebar = tk.Frame(root, bg="#282828", width=150)
        self.right_sidebar.pack(side=tk.RIGHT, fill=tk.Y)
        
        tk.Label(self.right_sidebar, text="MARKA SEÇİMİ", fg="#A0A0A0", bg="#282828", font=("Segoe UI", 10, "bold")).pack(pady=15)
        
        brands = ["Cisco", "Allied Telesis", "Ruijie"]
        for brand in brands:
            rb = tk.Radiobutton(self.right_sidebar, text=brand, variable=self.selected_brand, value=brand,
                                bg="#282828", fg="#E0E0E0", font=("Segoe UI", 10), cursor="hand2", selectcolor="#C62828", activebackground="#282828",
                                activeforeground="#E53935", indicatoron=0, bd=0, relief=tk.FLAT, padx=20, pady=10)
            rb.pack(fill=tk.X, padx=10, pady=4, ipady=2)

        # Ana Orta Alan
        self.main_container = tk.Frame(root, bg="#1A1A1A")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Terminal Ekranı (Putty Tarzı)
        self.terminal = scrolledtext.ScrolledText(
            self.main_container, bg="#101010", fg="#E0E0E0", 
            insertbackground="white", font=("Consolas", 11), selectbackground="#C62828"
        )
        self.terminal.pack(padx=10, pady=(10, 5), fill=tk.BOTH, expand=True)
        self.terminal.config(state=tk.DISABLED) # Manuel yazımı engelle

        # Giriş Alanı
        self.entry_container = tk.Frame(self.main_container, bg="#282828", bd=1, relief=tk.FLAT)
        self.entry_container.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # İç içe geçmiş çerçeve ile kenarlık efekti
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

        # Periyodik Kontrolleri Başlat
        self.mac_display_area = None  # MAC popup referansı
        self.check_for_data()
        self.auto_connect_service()

    def close_current_popup(self):
        """Mevcut açık olan popup penceresini kapatır."""
        if self.active_popup:
            try:
                self.active_popup.destroy()
            except:
                pass
        self.active_popup = None
        self.mac_display_area = None

    def log_to_terminal(self, message):
        """Terminal ekranına yazı ekler."""
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, message)
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)
        
        # Eğer MAC tablosu popup'ı açıksa veriyi oraya da yönlendir
        if self.mac_display_area:
            try:
                self.mac_display_area.insert(tk.END, message)
                self.mac_display_area.see(tk.END)
            except:
                self.mac_display_area = None

    def send_command(self, event=None):
        command = self.entry.get()
        if command:
            self.log_to_terminal(f"Uzzy >> {command}\n") # Gönderilen komutu terminale yazdır
            if self.serial_conn.is_connected:
                self.serial_conn.write_data(command + "\r\n")
                self.entry.delete(0, tk.END)
            else:
                self.log_to_terminal("\n[UYARI] Bağlı cihaz yok!\n")

    def open_port_control_popup(self):
        """Port açma/kapama işlemi için popup açar."""
        self.close_current_popup()
        popup = tk.Toplevel(self.root)
        self.active_popup = popup
        popup.title(f"Port Kontrolü - {self.selected_brand.get()}")
        popup.geometry("500x600")
        popup.configure(bg="#282828")
        
        selected_ports = set()
        port_state = tk.StringVar(value="no shutdown") # Default: Aç (no shutdown)

        tk.Label(popup, text="Port Aç / Kapat", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 14, "bold")).pack(pady=15)
        
        # Mod Seçimi (AÇ / KAPAT)
        mode_frame = tk.Frame(popup, bg="#282828")
        mode_frame.pack(pady=5)
        
        tk.Radiobutton(mode_frame, text="PORTLARI AÇ", variable=port_state, value="no shutdown", 
                       bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), cursor="hand2", bd=0, selectcolor="#4CAF50", activebackground="#3C3C3C", indicatoron=0, width=15, pady=5).pack(side=tk.LEFT, padx=5, ipady=3)
        tk.Radiobutton(mode_frame, text="PORTLARI KAPAT", variable=port_state, value="shutdown", 
                       bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), cursor="hand2", bd=0, selectcolor="#E53935", activebackground="#3C3C3C", indicatoron=0, width=15, pady=5).pack(side=tk.LEFT, padx=5, ipady=3)

        # Port Izgarası
        tk.Label(popup, text="Portları Seçin", fg="#A0A0A0", bg="#282828", font=("Segoe UI", 10)).pack(pady=5)
        grid_frame = tk.Frame(popup, bg="#282828")
        grid_frame.pack(padx=20, pady=5)

        port_buttons = {}
        start_port_id = [None]
        initial_snapshot = [set()]
        drag_mode = [None]

        def update_grid_colors():
            for p_id, btn in port_buttons.items():
                if p_id in selected_ports:
                    btn.config(bg="#E53935", fg="white")
                else:
                    btn.config(bg="#3C3C3C", fg="#E0E0E0")

        def on_button_press(p_num):
            start_port_id[0] = p_num
            initial_snapshot[0] = selected_ports.copy()
            if p_num in selected_ports:
                drag_mode[0] = "remove"
                selected_ports.remove(p_num)
            else:
                drag_mode[0] = "add"
                selected_ports.add(p_num)
            update_grid_colors()

        def on_drag(event):
            widget = event.widget.winfo_containing(event.x_root, event.y_root)
            if widget in port_buttons.values():
                try:
                    current_p = int(widget.cget("text"))
                    start_p = start_port_id[0]
                    if start_p is None: return
                    
                    port_range = set(range(min(start_p, current_p), max(start_p, current_p) + 1))
                    
                    new_selection = initial_snapshot[0].copy()
                    if drag_mode[0] == "add":
                        new_selection.update(port_range)
                    else:
                        new_selection.difference_update(port_range)
                    
                    if new_selection != selected_ports:
                        selected_ports.clear()
                        selected_ports.update(new_selection)
                        update_grid_colors()
                except: pass

        for i in range(1, 49):
            btn = tk.Button(grid_frame, text=str(i), width=4, height=2, bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#606060")
            row = (i-1) // 8
            col = (i-1) % 8
            btn.grid(row=row, column=col, padx=2, pady=2)
            btn.bind("<Button-1>", lambda e, p=i: on_button_press(p))
            btn.bind("<B1-Motion>", on_drag)
            port_buttons[i] = btn

        def clear_selection():
            selected_ports.clear()
            for btn in port_buttons.values():
                btn.config(bg="#3C3C3C", fg="#E0E0E0")

        tk.Button(popup, text="SEÇİMİ TEMİZLE", bg="#505050", fg="#E0E0E0", font=("Segoe UI", 9, "bold"),
                  bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#606060", command=clear_selection).pack(pady=10, ipady=3)

        def run_port_action():
            if not selected_ports:
                messagebox.showwarning("Uyarı", "Lütfen en az bir port seçin!")
                return
            
            state_label = "AÇILACAK" if port_state.get() == "no shutdown" else "KAPATILACAK"
            confirm = messagebox.askyesno("Onay", f"Seçili {len(selected_ports)} port {state_label}. Emin misiniz?")
            if not confirm: return

            brand = self.selected_brand.get()
            commands = ["configure terminal" if brand == "Ruijie" else "conf t"]
            
            for p in sorted(list(selected_ports)):
                if brand == "Cisco": interface = f"interface GigabitEthernet 1/0/{p}"
                elif brand == "Allied Telesis": interface = f"interface port1.0.{p}"
                else: interface = f"interface GigabitEthernet 0/{p}"
                
                commands.append(interface)
                commands.append(port_state.get())
            
            commands.append("end")

            if self.serial_conn.is_connected:
                for cmd in commands:
                    self.serial_conn.write_data(cmd + "\r\n")
                    time.sleep(0.05)
                self.log_to_terminal(f"\n[PORT] {len(selected_ports)} port {state_label.lower()} işlemi tamamlandı.\n")
                popup.destroy()
            else:
                messagebox.showerror("Hata", "Bağlantı yok!")

        tk.Button(popup, text="DEĞİŞİKLİKLERİ UYGULA", bg="#C62828", fg="white", font=("Segoe UI", 11, "bold"),
                  bd=0, cursor="hand2", relief=tk.FLAT, pady=10, activebackground="#E53935", command=run_port_action).pack(fill=tk.X, padx=50, pady=15, ipady=5)

    def check_for_data(self):
        """Seri porttan gelen verileri kuyruktan çekip ekrana basar."""
        while not self.serial_conn.data_queue.empty():
            data = self.serial_conn.data_queue.get()
            self.log_to_terminal(data)
        self.root.after(50, self.check_for_data) # 50ms sonra tekrar kontrol et

    def auto_connect_service(self):
        """Port tarayıcıyı kontrol eder ve yeni cihaz bulunca otomatik bağlanır."""
        # Eğer bağlı değilsek ve bir port bulunduysa
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
        
        # Eğer bağlıyken cihaz çıkarıldıysa durumu güncelle
        elif self.serial_conn.is_connected:
            if self.serial_conn.port not in self.scanner.discovered_ports:
                self.log_to_terminal(f"\n[BİLGİ] {self.serial_conn.port} fiziksel olarak ayrıldı.\n")
                self.serial_conn.disconnect()
                self.status_var.set("Cihaz Ayrıldı - Yeni Port Bekleniyor...")

        self.root.after(1000, self.auto_connect_service) # Saniyede bir kontrol et

if __name__ == "__main__":
    root = tk.Tk()
    
    # İkon ve resim yolu ayarlaması (dosyanın bulunduğu dizine göre)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(current_dir, "uzzy_icon.png")

    # Pencere İkonunu Ayarla
    try:
        icon_img = tk.PhotoImage(file=icon_path)
        root.iconphoto(True, icon_img)
    except Exception as e:
        print(f"İkon yüklenemedi: {e}")

    # Ana pencereyi başlangıçta gizle
    root.withdraw()
    
    app = UzzyGUI(root)
    
    def on_closing():
        app.serial_conn.disconnect()
        app.scanner.running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # --- SPLASH EKRANI (AÇILIŞ EKRANI) ---
    splash = tk.Toplevel(root)
    splash.overrideredirect(True) # Başlık çubuğunu gizle
    splash.attributes("-topmost", True) # Her zaman üstte tut
    
    splash.configure(bg="#1A1A1A")
    
    try:
        splash_img = tk.PhotoImage(file=icon_path)
        if HAS_PIL:
            # Pillow ile resmi aç, %70 küçült (orijinalin %30'una getir)
            img = Image.open(icon_path).convert("RGBA")
            new_w = int(img.width * 0.3)
            new_h = int(img.height * 0.3)
            
            try:
                resample_filter = Image.Resampling.LANCZOS
            except AttributeError:
                resample_filter = Image.ANTIALIAS
                
            img = img.resize((new_w, new_h), resample_filter)
            
            # Yuvarlak köşe maskesi oluştur (kavis yarıçapı genişliğin %15'i)
            mask = Image.new('L', (new_w, new_h), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, new_w, new_h), radius=int(new_w * 0.15), fill=255)
            
            # Orijinal alfa kanalını yuvarlak maske ile birleştir
            r, g, b, a = img.split()
            img.putalpha(ImageChops.darker(a, mask))
            
            splash_img = ImageTk.PhotoImage(img)
        else:
            # Pillow yoksa standart tkinter ile küçült (yaklaşık %33'üne getirir)
            splash_img = tk.PhotoImage(file=icon_path).subsample(3, 3)

        splash_label = tk.Label(splash, image=splash_img, bg="#1A1A1A", bd=0)
        splash_label.image = splash_img # Resmin bellekten silinmesini (Garbage Collection) önle
        splash_label.pack()
        
        # Resim boyutlarına göre pencereyi ayarla
        splash.update_idletasks()
        w = splash_label.winfo_reqwidth()
        h = splash_label.winfo_reqheight()
    except Exception as e:
        print(f"Splash resmi yüklenemedi: {e}")
        w, h = 300, 300
        tk.Label(splash, text="UZZY", fg="#E53935", bg="#1A1A1A", font=("Segoe UI", 36, "bold")).pack(expand=True, fill=tk.BOTH)

    # Splash ekranını bilgisayarın tam ortasına konumlandır
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    splash.geometry(f"{w}x{h}+{x}+{y}")
    
    def fade_out():
        alpha = splash.attributes("-alpha")
        if alpha > 0:
            splash.attributes("-alpha", alpha - 0.05) # Saydamlığı yavaş yavaş azalt
            splash.after(30, fade_out) # 30 milisaniye sonra tekrar çalıştır
        else:
            splash.destroy() # Splash ekranını yok et
            root.deiconify() # Ana UzzyGUI penceresini görünür yap

    # 5 saniye (5000 ms) bekle ve fade_out (yavaşça kaybolma) işlemini tetikle
    splash.after(5000, fade_out)
    # 3 saniye (3000 ms) bekle ve fade_out (yavaşça kaybolma) işlemini tetikle
    splash.after(3000, fade_out)

    root.mainloop()
