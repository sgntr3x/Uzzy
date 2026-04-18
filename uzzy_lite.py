import serial
import serial.tools.list_ports
import threading
import tkinter as tk
from tkinter import scrolledtext
import queue
import time

class UzzyLite:
    def __init__(self, root):
        self.root = root
        self.root.title("Uzzy Lite - Auto Connect")
        self.root.geometry("700x450")
        self.root.configure(bg="#1A1A1A")

        self.serial_conn = None
        self.connected = False
        self.data_queue = queue.Queue()

        # --- UI Tasarımı ---
        
        # Modern Giriş Alanı (Input Box)
        self.entry_container = tk.Frame(root, bg="#282828", bd=0)
        self.entry_container.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        
        self.entry_inner = tk.Frame(self.entry_container, bg="#3C3C3C", padx=10, pady=5)
        self.entry_inner.pack(fill=tk.X)

        self.prompt_label = tk.Label(
            self.entry_inner, text="Command:", 
            fg="#E53935", bg="#3C3C3C", font=("Consolas", 10, "bold")
        )
        self.prompt_label.pack(side=tk.LEFT)

        self.entry = tk.Entry(
            self.entry_inner, bg="#3C3C3C", fg="#E0E0E0", 
            insertbackground="white", font=("Consolas", 11), 
            relief=tk.FLAT, borderwidth=0, width=1
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        self.entry.bind("<Return>", self.send_command)

        # Terminal Ekranı (Üstte kalacak şekilde pack sırası önemli)
        self.terminal = scrolledtext.ScrolledText(
            root, bg="#101010", fg="#E0E0E0", 
            insertbackground="#ffffff", font=("Consolas", 11),
            borderwidth=0, highlightthickness=0,
            selectbackground="#C62828"
        )
        self.terminal.pack(side=tk.TOP, padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.terminal.config(state=tk.DISABLED)

        # Başlangıç Mesajı
        self.log("Uzzy Lite Terminal v1.0\nSearching for devices...\n")

        # Servisleri Başlat
        self.check_queue()
        self.auto_connect_loop()

    def log(self, message):
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, message)
        self.detect_prompt()
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)

    def detect_prompt(self):
        """Terminaldeki son satırı analiz ederek switch moduna göre promptu günceller."""
        # Son satırı al (Tkinter'ın otomatik eklediği son karakteri atlayarak)
        last_line = self.terminal.get("end-2c linestart", "end-1c").strip()
        
        if not last_line:
            return

        # Switch prompt desenlerini kontrol et (>, #)
        if last_line.endswith(">") or last_line.endswith("#"):
            # Çok uzun satırları (banner metinleri vb.) prompt olarak kabul etme
            if len(last_line) < 40:
                self.prompt_label.config(text=last_line)

    def send_command(self, event=None):
        cmd = self.entry.get()
        if cmd and self.connected:
            try:
                self.serial_conn.write((cmd + "\r\n").encode('utf-8'))
                self.entry.delete(0, tk.END)
            except Exception as e:
                self.log(f"\n[HATA] Gönderilemedi: {e}\n")
        elif not self.connected:
            self.log("\n[UYARI] Cihaz bağlı değil!\n")

    def read_loop(self):
        while self.connected:
            try:
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    self.data_queue.put(data.decode('utf-8', errors='ignore'))
                time.sleep(0.01)
            except:
                break
        self.connected = False

    def auto_connect_loop(self):
        if not self.connected:
            ports = serial.tools.list_ports.comports()
            if ports:
                target = ports[0].device
                try:
                    self.serial_conn = serial.Serial(target, 115200, timeout=1)
                    self.connected = True
                    self.log(f"\nCONNECTED: {target} at 115200 baud\n\n")
                    
                    # Okuma thread'ini başlat
                    threading.Thread(target=self.read_loop, daemon=True).start()
                except Exception as e:
                    pass # Bağlanamazsa bir sonraki döngüde tekrar dener
        
        # Bağlıyken portun hala var olup olmadığını kontrol et
        elif self.connected:
            current_ports = [p.device for p in serial.tools.list_ports.comports()]
            if self.serial_conn.port not in current_ports:
                self.log(f"\nDISCONNECTED: {self.serial_conn.port}\n")
                self.prompt_label.config(text="Command:")
                self.connected = False
                if self.serial_conn: self.serial_conn.close()

        self.root.after(1000, self.auto_connect_loop)

    def check_queue(self):
        while not self.data_queue.empty():
            msg = self.data_queue.get()
            self.log(msg)
        self.root.after(50, self.check_queue)

if __name__ == "__main__":
    root = tk.Tk()
    # Pencereyi her zaman üstte tutmak istersen: root.attributes('-topmost', True)
    app = UzzyLite(root)
    root.mainloop()