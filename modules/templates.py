import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import os
import json
import time
import threading

TEMPLATES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uzzy_templates.json")


def _load():
    if os.path.exists(TEMPLATES_FILE):
        try:
            with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(data):
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def open_template_manager(parent_gui):
    parent_gui.close_current_popup()
    popup = ctk.CTkToplevel(parent_gui.root)
    parent_gui.active_popup = popup
    parent_gui.set_window_icon(popup)
    popup.title("Config Template Yöneticisi")
    popup.geometry("720x560")
    popup.transient(parent_gui.root)
    popup.grab_set()

    templates_data = _load()

    main_frame = ctk.CTkFrame(popup, fg_color="transparent")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    # Sol panel: liste
    left = ctk.CTkFrame(main_frame, fg_color="#1E1E1E", width=210)
    left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
    left.pack_propagate(False)

    ctk.CTkLabel(left, text="TEMPLATELER", text_color="#A0A0A0",
                 font=("Segoe UI", 11, "bold")).pack(pady=(12, 6), padx=10)

    lst_frame = tk.Frame(left, bg="#1A1A1A")
    lst_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    tlist = tk.Listbox(lst_frame, bg="#1A1A1A", fg="#C0C0C0", selectbackground="#C62828",
                       selectforeground="white", font=("Segoe UI", 11), bd=0,
                       highlightthickness=0, activestyle="none", relief=tk.FLAT)
    tscroll = ctk.CTkScrollbar(lst_frame, orientation="vertical", command=tlist.yview)
    tlist.configure(yscrollcommand=tscroll.set)
    tlist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    tscroll.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_list():
        tlist.delete(0, tk.END)
        for name in templates_data:
            tlist.insert(tk.END, name)

    refresh_list()

    # Sağ panel: düzenle / uygula
    right = ctk.CTkFrame(main_frame, fg_color="transparent")
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    ctk.CTkLabel(right, text="Template Adı:", text_color="#A0A0A0",
                 font=("Segoe UI", 11)).pack(anchor=tk.W)
    name_entry = ctk.CTkEntry(right, placeholder_text="Örn: Base Config, VLAN Setup")
    name_entry.pack(fill=tk.X, pady=(2, 10))

    ctk.CTkLabel(right, text="Komutlar  (her satır = 1 komut, sırayla gönderilir):",
                 text_color="#A0A0A0", font=("Segoe UI", 11)).pack(anchor=tk.W)
    cmd_box = ctk.CTkTextbox(right, font=("Consolas", 12), fg_color="#101010", text_color="#E0E0E0")
    cmd_box.pack(fill=tk.BOTH, expand=True, pady=(2, 10))

    def on_select(event):
        sel = tlist.curselection()
        if not sel:
            return
        tname = tlist.get(sel[0])
        name_entry.delete(0, tk.END)
        name_entry.insert(0, tname)
        cmd_box.delete("1.0", tk.END)
        cmd_box.insert("1.0", "\n".join(templates_data[tname].get("commands", [])))

    tlist.bind("<<ListboxSelect>>", on_select)

    def save_template():
        tname = name_entry.get().strip()
        if not tname:
            messagebox.showwarning("Uyarı", "Template adı boş olamaz!", parent=popup)
            return
        raw = cmd_box.get("1.0", "end").strip()
        cmds = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if not cmds:
            messagebox.showwarning("Uyarı", "En az bir komut giriniz!", parent=popup)
            return
        templates_data[tname] = {"commands": cmds}
        _save(templates_data)
        refresh_list()
        messagebox.showinfo("Başarılı", f'"{tname}" kaydedildi.', parent=popup)

    def delete_template():
        sel = tlist.curselection()
        if not sel:
            return
        tname = tlist.get(sel[0])
        if messagebox.askyesno("Sil", f'"{tname}" silinsin mi?', parent=popup):
            del templates_data[tname]
            _save(templates_data)
            name_entry.delete(0, tk.END)
            cmd_box.delete("1.0", tk.END)
            refresh_list()

    def apply_template():
        sel = tlist.curselection()
        if not sel:
            messagebox.showwarning("Uyarı", "Lütfen bir template seçin!", parent=popup)
            return
        tname = tlist.get(sel[0])
        cmds = templates_data[tname].get("commands", [])
        if not cmds:
            return
        if not messagebox.askyesno("Onayla",
                                    f'"{tname}" uygulanacak ({len(cmds)} komut).\nEmin misiniz?',
                                    parent=popup):
            return
        if not parent_gui.serial_conn.is_connected:
            messagebox.showerror("Hata", "Bağlantı yok!", parent=popup)
            return

        def run():
            parent_gui.log_to_terminal(f"\n[TEMPLATE] '{tname}' uygulanıyor ({len(cmds)} komut)...\n")
            for cmd in cmds:
                parent_gui.serial_conn.write_data(cmd + "\r\n")
                time.sleep(0.15)
            parent_gui.log_to_terminal(f"\n[TEMPLATE] '{tname}' tamamlandı.\n")

        threading.Thread(target=run, daemon=True).start()
        popup.destroy()

    btn_frame = ctk.CTkFrame(right, fg_color="transparent")
    btn_frame.pack(fill=tk.X)
    ctk.CTkButton(btn_frame, text="💾 Kaydet", fg_color="#3A3A3C", hover_color="#505055",
                  font=("Segoe UI", 12, "bold"), command=save_template).pack(side=tk.LEFT, padx=(0, 5))
    ctk.CTkButton(btn_frame, text="🗑 Sil", fg_color="#3A3A3C", hover_color="#505055",
                  font=("Segoe UI", 12, "bold"), command=delete_template).pack(side=tk.LEFT, padx=5)
    ctk.CTkButton(btn_frame, text="▶ Uygula", fg_color="#3A3A3C", hover_color="#505055",
                  font=("Segoe UI", 12, "bold"), command=apply_template).pack(side=tk.LEFT, padx=5)
