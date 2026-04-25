import tkinter as tk
from tkinter import messagebox, ttk
import threading
import time
import traceback
import sys
import os

# get_api_key modülünü bulabilmek için ana dizini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import get_api_key

try:
    import google.generativeai as genai
    HAS_GEMINI = True
    GEMINI_ERR = ""
    
    if get_api_key.GEMINI_API_KEY and get_api_key.GEMINI_API_KEY != "BURAYA_API_KEY_GIRIN":
        genai.configure(api_key=get_api_key.GEMINI_API_KEY)
    else:
        print("Uyarı: 'get_api_key.py' içerisinde geçerli bir API anahtarı bulunamadı.")
except Exception:
    HAS_GEMINI = False
    GEMINI_ERR = traceback.format_exc()

def open_ai_config_popup(parent_gui):
    if not HAS_GEMINI:
        messagebox.showerror("Eksik Kütüphane", f"AI kütüphanesi yüklenirken içsel bir hata oluştu:\n\n{GEMINI_ERR}\n\nBu durum genellikle PyInstaller paketlemesinde alt modüllerin eksik kalmasından kaynaklanır.")
        return
        
    if not get_api_key.GEMINI_API_KEY or get_api_key.GEMINI_API_KEY == "BURAYA_API_KEY_GIRIN":
        messagebox.showerror("API Anahtarı Eksik", "Lütfen 'get_api_key.py' dosyasına geçerli bir Gemini API anahtarı girin ve uygulamayı yeniden başlatın.")
        return

    parent_gui.close_current_popup()
    popup = tk.Toplevel(parent_gui.root)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
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
        threading.Thread(target=_run_ai_configuration, args=(parent_gui, user_input, popup, apply_button, status_label), daemon=True).start()

    apply_button = tk.Button(popup, text="Yapılandırmayı Oluştur", bg="#8E44AD", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", 
                             command=on_apply, activebackground="#9B59B6")
    apply_button.pack(fill=tk.X, padx=40, pady=10, ipady=5)

def _run_ai_configuration(parent_gui, user_request, popup, button, status_label):
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not available_models: return messagebox.showerror("Model Hatası", "API anahtarı model bulamadı.", parent=popup)
            
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        brand = parent_gui.selected_brand.get()
        ports = sorted(list(parent_gui.selected_ports)) if parent_gui.selected_ports else "Hiçbiri"
        
        prompt = f"Sen bir ağ asistanısın. Switch Markası: {brand} | Seçili Portlar: {ports} | İsteği: '{user_request}'\nSadece komutları döndür."
        response = model.generate_content(prompt)
        generated_text = response.text.strip()

        if generated_text.startswith("HATA:"): return messagebox.showerror("AI Hatası", generated_text, parent=popup)

        popup.after(0, _apply_ai_commands, parent_gui, generated_text, popup)
    except Exception as e:
        messagebox.showerror("API Hatası", f"Hata:\n{e}", parent=popup)
    finally:
        def reset_ui():
            button.config(state=tk.NORMAL, text="Yapılandırmayı Oluştur")
            status_label.config(text="")
        popup.after(0, reset_ui)

def _apply_ai_commands(parent_gui, commands_text, popup):
    commands_list = [cmd.strip() for cmd in commands_text.split('\n') if cmd.strip()]
    if not commands_list: return messagebox.showwarning("AI Sonucu", "AI komut üretmedi.", parent=popup)

    confirm_popup = tk.Toplevel(popup)
    confirm_popup.transient(popup)
    confirm_popup.title("AI Config Onayı")
    confirm_popup.geometry("550x550")
    confirm_popup.configure(bg="#282828")
    
    tk.Label(confirm_popup, text="Aşağıdaki komutlar uygulanacak:", fg="#E0E0E0", bg="#282828", font=("Segoe UI", 11, "bold")).pack(pady=10)
    
    text_frame = tk.Frame(confirm_popup, bg="#101010", bd=1, relief=tk.SOLID)
    text_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
    
    config_text = tk.Text(text_frame, bg="#101010", fg="#E0E0E0", font=("Consolas", 10), bd=0, wrap=tk.WORD)
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=config_text.yview, style="Dark.Vertical.TScrollbar")
    config_text.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    config_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    config_string = "\n".join(commands_list)
    config_text.insert("1.0", config_string)
    config_text.config(state=tk.DISABLED)
    
    btn_frame = tk.Frame(confirm_popup, bg="#282828")
    btn_frame.pack(pady=15, fill=tk.X, padx=10)
    
    def on_cancel():
        confirm_popup.destroy()
        
    def on_copy():
        confirm_popup.clipboard_clear()
        confirm_popup.clipboard_append(config_string)
        confirm_popup.update()
        
    def on_confirm():
        if messagebox.askyesno("Emin Misin?", "Bu konfigürasyonları uygulamak istediğinize emin misiniz?", parent=confirm_popup):
            confirm_popup.destroy()
            parent_gui.log_to_terminal(f"\n[AI CONFIG] '{commands_list[0]}...' uygulanıyor...\n")
            for cmd in commands_list:
                if parent_gui.serial_conn.is_connected:
                    parent_gui.serial_conn.write_data(cmd + "\r\n")
                else:
                    parent_gui.log_to_terminal(f"(Simülasyon) Uzzy >> {cmd}\n")
                time.sleep(0.05)
            parent_gui.log_to_terminal(f"\n[AI CONFIG] Tamamlandı.\n")
            popup.destroy()
            parent_gui.clear_port_selection()
            
    tk.Button(btn_frame, text="Config'i İptal Et", bg="#C62828", fg="white", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", 
              activebackground="#E53935", command=on_cancel).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X, ipady=4)
    tk.Button(btn_frame, text="Config'i Kopyala", bg="#0277BD", fg="white", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", 
              activebackground="#01579B", command=on_copy).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X, ipady=4)
    tk.Button(btn_frame, text="Config'i Onayla", bg="#2E7D32", fg="white", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", 
              activebackground="#1B5E20", command=on_confirm).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X, ipady=4)