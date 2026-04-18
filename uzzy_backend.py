import serial
import serial.tools.list_ports
import threading
import time
import queue

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

# Seri port bağlantısını yönetecek sınıf
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