import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
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
    popup = ctk.CTkToplevel(parent_gui.root)
    parent_gui.set_window_icon(popup)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("AI ile Yapılandır")
    popup.geometry("600x600")
    popup.minsize(550, 550)

    ctk.CTkLabel(popup, text="Yapmak istediğiniz işlemi doğal dilde açıklayın:", font=("Segoe UI", 12, "bold")).pack(pady=10)
    
    input_frame = ctk.CTkFrame(popup, fg_color="transparent")
    input_frame.pack(pady=5, padx=10, fill="both", expand=True)
    
    user_input_text = ctk.CTkTextbox(input_frame, font=("Segoe UI", 12), wrap="word")
    user_input_text.pack(fill="both", expand=True, padx=5, pady=5)
    user_input_text.focus()
    
    user_input_text.insert("1.0", "Örnek: Seçili portları vlan 10'a access modunda ata ve portfast aç.")

    status_label = ctk.CTkLabel(popup, text="", text_color="#A0A0A0", font=("Segoe UI", 10))
    status_label.pack(pady=5)

    def on_apply():
        user_input = user_input_text.get("1.0", ctk.END).strip()
        if not user_input or "Örnek:" in user_input:
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir istek girin.", parent=popup)
            return
        
        apply_button.configure(state="disabled", text="İşleniyor...")
        status_label.configure(text="AI modeli ile iletişim kuruluyor, lütfen bekleyin...")
        threading.Thread(target=_run_ai_configuration, args=(parent_gui, user_input, popup, apply_button, status_label), daemon=True).start()

    apply_button = ctk.CTkButton(popup, text="Yapılandırmayı Oluştur", fg_color="#8E44AD", hover_color="#9B59B6", font=("Segoe UI", 12, "bold"), command=on_apply)
    apply_button.pack(fill=ctk.X, padx=40, pady=10)

def _run_ai_configuration(parent_gui, user_request, popup, button, status_label):
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not available_models: return messagebox.showerror("Model Hatası", "API anahtarı model bulamadı.", parent=popup)
            
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        brand = parent_gui.selected_brand.get()
        
        ports = sorted(list(parent_gui.selected_ports)) if parent_gui.selected_ports else []
        port_mapping = getattr(parent_gui, 'port_mapping', {})
        if ports and port_mapping:
            mapped_ports = [port_mapping.get(p, str(p)) for p in ports]
            ports_str = ", ".join(mapped_ports)
        else:
            ports_str = ", ".join(map(str, ports)) if ports else "Hiçbiri"
        
        prompt = f"Sen bir ağ asistanısın. Switch Markası: {brand} | Seçili Portlar: {ports_str} | İsteği: '{user_request}'\nSadece komutları döndür."
        response = model.generate_content(prompt)
        generated_text = response.text.strip()

        if generated_text.startswith("HATA:"): return messagebox.showerror("AI Hatası", generated_text, parent=popup)

        popup.after(0, _apply_ai_commands, parent_gui, generated_text, popup)
    except Exception as e:
        messagebox.showerror("API Hatası", f"Hata:\n{e}", parent=popup)
    finally:
        def reset_ui():
            button.configure(state="normal", text="Yapılandırmayı Oluştur")
            status_label.configure(text="")
        popup.after(0, reset_ui)

def _apply_ai_commands(parent_gui, commands_text, popup):
    commands_list = [cmd.strip() for cmd in commands_text.split('\n') if cmd.strip()]
    if not commands_list: return messagebox.showwarning("AI Sonucu", "AI komut üretmedi.", parent=popup)

    confirm_popup = ctk.CTkToplevel(popup)
    parent_gui.set_window_icon(confirm_popup)
    confirm_popup.transient(popup)
    confirm_popup.title("AI Config Onayı")
    confirm_popup.geometry("550x550")
    
    ctk.CTkLabel(confirm_popup, text="Aşağıdaki komutlar uygulanacak:", font=("Segoe UI", 12, "bold")).pack(pady=10)
    
    text_frame = ctk.CTkFrame(confirm_popup, fg_color="transparent")
    text_frame.pack(padx=10, pady=5, fill=ctk.BOTH, expand=True)
    
    config_text = ctk.CTkTextbox(text_frame, font=("Consolas", 12), wrap="word")
    config_text.pack(fill=ctk.BOTH, expand=True)
    
    config_string = "\n".join(commands_list)
    config_text.insert("1.0", config_string)
    config_text.configure(state="disabled")
    
    btn_frame = ctk.CTkFrame(confirm_popup, fg_color="transparent")
    btn_frame.pack(pady=15, fill=ctk.X, padx=10)
    
    def on_cancel():
        confirm_popup.destroy()
        
    def on_copy():
        confirm_popup.clipboard_clear()
        confirm_popup.clipboard_append(config_string)
        confirm_popup.update()
        
    def on_download():
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Config'i Kaydet",
            parent=confirm_popup
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(config_string)
                messagebox.showinfo("Başarılı", "Config başarıyla kaydedildi.", parent=confirm_popup)
            except Exception as e:
                messagebox.showerror("Hata", f"Dosya kaydedilemedi:\n{e}", parent=confirm_popup)

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
            
    ctk.CTkButton(btn_frame, text="İptal Et", fg_color="#C62828", hover_color="#E53935", command=on_cancel).pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
    ctk.CTkButton(btn_frame, text="Kopyala", fg_color="#0277BD", hover_color="#01579B", command=on_copy).pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
    ctk.CTkButton(btn_frame, text="TXT İndir", fg_color="#F39C12", hover_color="#D68910", command=on_download).pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)
    ctk.CTkButton(btn_frame, text="Onayla", fg_color="#2E7D32", hover_color="#1B5E20", command=on_confirm).pack(side=ctk.LEFT, padx=5, expand=True, fill=ctk.X)