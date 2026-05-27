import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import time
import threading
import os
import re
import json

try:
    from PIL import Image, ImageTk, ImageDraw, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from modules import mac_table
from modules import command_builder
from modules import ai_config
from modules import switch_configs
from modules import poe_config
from modules import config_diff
from modules import templates
import uzzy_backend

SHORTCUTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uzzy_shortcuts.json")
DEFAULT_SHORTCUTS = [
    {"label": "sh run",       "command": "show running-config"},
    {"label": "sh int status","command": "show interfaces status"},
    {"label": "sh vlan",      "command": "show vlan brief"},
    {"label": "sh mac",       "command": "show mac address-table"},
    {"label": "sh lldp nei",  "command": "show lldp neighbors detail"},
]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class UzzyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Uzzy Serial Terminal")
        self.root.geometry("1400x800")

        # State
        self.selected_brand = ctk.StringVar(value="Allied Telesis")
        self.port_count_var = ctk.StringVar(value="48")
        self.baudrate_var = ctk.StringVar(value="9600")
        self.port_mapping = {}
        self.switch_hostname = ""
        self.command_history = []
        self._history_idx = -1
        self.custom_shortcuts = []

        # Services
        self.scanner = uzzy_backend.UzzyScanner()
        self.scanner.start()
        self.serial_conn = uzzy_backend.UzzySerialConnection(baudrate=9600)
        self.active_popup = None
        self.capture_filepath = None

        self._build_toolbar(root)
        self._build_port_panel(root)
        self._build_main_area(root)
        self._build_status_bar(root)

        self.mac_display_area = None
        self.check_for_data()
        self.auto_connect_service()

    # ──────────────────────────────────────────────────────────────
    # LAYOUT BUILDERS
    # ──────────────────────────────────────────────────────────────

    def _build_toolbar(self, root):
        self.top_toolbar = ctk.CTkFrame(root, fg_color="#2D2D30", corner_radius=0)
        self.top_toolbar.pack(side=tk.TOP, fill=tk.X)

        # Model + Hostname (sol)
        info_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        info_frame.pack(side=tk.LEFT, padx=15, pady=10)

        ctk.CTkLabel(info_frame, text="MODEL:", text_color="#A0A0A0",
                     font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.model_label = ctk.CTkLabel(info_frame, text="—", text_color="#E0E0E0",
                                        font=("Segoe UI", 12, "bold"))
        self.model_label.pack(side=tk.LEFT, padx=(0, 14))

        ctk.CTkLabel(info_frame, text="HOST:", text_color="#A0A0A0",
                     font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.hostname_label = ctk.CTkLabel(info_frame, text="—", text_color="#E0E0E0",
                                           font=("Segoe UI", 12, "bold"))
        self.hostname_label.pack(side=tk.LEFT)

        # Baud Rate
        baud_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        baud_frame.pack(side=tk.LEFT, padx=10, pady=10)
        ctk.CTkLabel(baud_frame, text="BAUD:", text_color="#A0A0A0",
                     font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        baudrates = ["9600", "19200", "38400", "57600", "115200"]
        self.baudrate_menu = ctk.CTkOptionMenu(
            baud_frame, variable=self.baudrate_var, values=baudrates,
            fg_color="#3C3C3C", button_color="#505050", width=90,
            command=self.on_baudrate_change)
        self.baudrate_menu.pack(side=tk.LEFT, padx=2)

        # Otomatik Algıla
        detect_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        detect_frame.pack(side=tk.LEFT, padx=10, pady=10)
        BTN   = "#3A3A3C"
        BTN_H = "#505055"

        self.btn_auto_port = ctk.CTkButton(
            detect_frame, text="Otomatik Algıla", fg_color=BTN, hover_color=BTN_H,
            font=("Segoe UI", 12, "bold"), width=120, command=self.auto_detect_ports)
        self.btn_auto_port.pack(side=tk.LEFT)

        # AI Config
        ai_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        ai_frame.pack(side=tk.LEFT, padx=10, pady=10)
        self.btn_ai = ctk.CTkButton(
            ai_frame, text="✨ AI Config", fg_color=BTN, hover_color=BTN_H,
            font=("Segoe UI", 12, "bold"),
            command=lambda: ai_config.open_ai_config_popup(self))
        self.btn_ai.pack(side=tk.LEFT)

        # Template
        tmpl_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        tmpl_frame.pack(side=tk.LEFT, padx=10, pady=10)
        self.btn_template = ctk.CTkButton(
            tmpl_frame, text="📋 Template", fg_color=BTN, hover_color=BTN_H,
            font=("Segoe UI", 12, "bold"),
            command=lambda: templates.open_template_manager(self))
        self.btn_template.pack(side=tk.LEFT)

        # Aksiyon butonları (sağ)
        action_frame = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        action_frame.pack(side=tk.RIGHT, padx=15, pady=10)

        self.btn_refresh = ctk.CTkButton(
            action_frame, text="⟳ Yenile", fg_color=BTN, hover_color=BTN_H,
            font=("Segoe UI", 12, "bold"), width=80, command=self.refresh_connection)
        self.btn_refresh.pack(side=tk.LEFT, padx=5)

        self.btn_download_cfg = ctk.CTkButton(
            action_frame, text="📥 Config İndir", fg_color=BTN, hover_color=BTN_H,
            font=("Segoe UI", 12, "bold"), width=110, command=self.start_config_backup)
        self.btn_download_cfg.pack(side=tk.LEFT, padx=5)

        self.btn_select_all = ctk.CTkButton(
            action_frame, text="Tümünü Seç", fg_color=BTN, hover_color=BTN_H,
            font=("Segoe UI", 12, "bold"), width=90, command=self.select_all_ports)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)

        self.btn_clear = ctk.CTkButton(
            action_frame, text="Temizle", fg_color=BTN, hover_color=BTN_H,
            font=("Segoe UI", 12, "bold"), width=70, command=self.clear_port_selection)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        self.btn_config = ctk.CTkButton(
            action_frame, text="Config ▼", fg_color=BTN, hover_color=BTN_H,
            font=("Segoe UI", 12, "bold"), width=80)

        self.config_menu = tk.Menu(
            self.root, tearoff=0, bg="#3C3C3C", fg="#E0E0E0",
            activebackground="#C62828", bd=0, font=("Segoe UI", 10))
        self.config_menu.add_command(label="VLAN Oluştur",
                                     command=lambda: switch_configs.open_create_vlan_popup(self))
        self.config_menu.add_command(label="VLAN Ata",
                                     command=lambda: switch_configs.open_assign_vlan_popup(self))
        self.config_menu.add_command(label="STP Ayarı Yap",
                                     command=lambda: switch_configs.open_stp_config_popup(self))
        self.config_menu.add_command(label="Management IP Ata",
                                     command=lambda: switch_configs.open_management_ip_popup(self))
        self.config_menu.add_command(label="PoE Kontrolü",
                                     command=lambda: poe_config.open_poe_control_popup(self))
        self.config_menu.add_separator()
        self.config_menu.add_command(label="Port Aç/Kapa",
                                     command=lambda: switch_configs.open_port_control_popup_new(self))
        self.config_menu.add_command(label="Portları Sıfırla (Default)",
                                     command=lambda: switch_configs.apply_default_port_settings(self))
        self.config_menu.add_separator()
        self.config_menu.add_command(label="MAC Adres Listesi",
                                     command=lambda: mac_table.open_mac_table_popup(self))
        self.config_menu.add_command(label="Config Karşılaştırma (Diff)",
                                     command=lambda: config_diff.open_diff_tool(self))

        def show_config_menu(event):
            self.config_menu.post(event.x_root, event.y_root + 15)
        self.btn_config.bind("<Button-1>", show_config_menu)
        self.btn_config.pack(side=tk.LEFT, padx=5)

    def _build_port_panel(self, root):
        self.port_container = ctk.CTkFrame(root, fg_color="#1E1E1E", corner_radius=0)
        self.port_container.pack(side=tk.TOP, fill=tk.X, padx=15, pady=10)
        ctk.CTkLabel(
            self.port_container,
            text="FİZİKSEL PORT GÖRÜNÜMÜ  (Sol tık: seç / Sürükle: çoklu seç / Sağ tık: hızlı işlem)",
            text_color="#888888", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=5, pady=(5, 0))

        self.switch_panel = tk.Frame(self.port_container, bg="#0A0A0A", padx=15, pady=15,
                                     bd=2, relief=tk.GROOVE)
        self.switch_panel.pack(fill=tk.X)

        self.selected_ports = set()
        self.port_buttons = {}
        self.start_port_id = [None]
        self.initial_snapshot = [set()]
        self.drag_mode = [None]

        # Sağ tık context menüsü
        self.port_context_menu = tk.Menu(
            self.root, tearoff=0, bg="#3C3C3C", fg="#E0E0E0",
            activebackground="#C62828", bd=0, font=("Segoe UI", 10))
        self.port_context_menu.add_command(
            label="VLAN Ata", command=lambda: switch_configs.open_assign_vlan_popup(self))
        self.port_context_menu.add_command(
            label="PoE Kontrolü", command=lambda: poe_config.open_poe_control_popup(self))
        self.port_context_menu.add_command(
            label="Port Aç/Kapa", command=lambda: switch_configs.open_port_control_popup_new(self))
        self.port_context_menu.add_command(
            label="Portları Sıfırla (Default)",
            command=lambda: switch_configs.apply_default_port_settings(self))
        self.port_context_menu.add_separator()
        self.port_context_menu.add_command(
            label="Tümünü Seç", command=self.select_all_ports)
        self.port_context_menu.add_command(
            label="Seçimi Temizle", command=self.clear_port_selection)

        self.draw_port_panel()

    def _build_main_area(self, root):
        self.main_container = ctk.CTkFrame(root, fg_color="transparent")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Terminal + History yan yana
        content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self.terminal_font_size = 14
        self.terminal = ctk.CTkTextbox(
            content_frame, font=("Consolas", self.terminal_font_size),
            fg_color="#101010", text_color="#E0E0E0")
        self.terminal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.terminal.tag_config("success", foreground="#4CAF50")
        self.terminal.tag_config("error",   foreground="#F44336")
        self.terminal.tag_config("info",    foreground="#E0E0E0")
        self.terminal.tag_config("warning", foreground="#FFA726")
        # Yazma tuşlarını engelle ama Ctrl+C/Ctrl+A ve fare seçimini serbest bırak
        self.terminal.bind("<Key>", self._terminal_key_guard)

        # Komut Geçmişi paneli (sağ)
        hist_panel = ctk.CTkFrame(content_frame, fg_color="#1A1A1A", width=195, corner_radius=6)
        hist_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 0))
        hist_panel.pack_propagate(False)

        hist_header = ctk.CTkFrame(hist_panel, fg_color="transparent")
        hist_header.pack(fill=tk.X, padx=8, pady=(8, 4))
        ctk.CTkLabel(hist_header, text="GEÇMİŞ", text_color="#A0A0A0",
                     font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        ctk.CTkButton(hist_header, text="✕", fg_color="transparent", hover_color="#3C3C3C",
                      width=24, height=20, font=("Segoe UI", 10),
                      command=self._clear_history).pack(side=tk.RIGHT)
        ctk.CTkLabel(hist_panel, text="(çift tık = tekrar gönder)",
                     text_color="#555555", font=("Segoe UI", 9)).pack(padx=8, anchor=tk.W)

        hist_list_frame = tk.Frame(hist_panel, bg="#1A1A1A")
        hist_list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(4, 6))

        self.history_listbox = tk.Listbox(
            hist_list_frame, bg="#1A1A1A", fg="#B0B0B0",
            selectbackground="#C62828", selectforeground="white",
            font=("Consolas", 10), bd=0, highlightthickness=0,
            activestyle="none", relief=tk.FLAT)
        hist_scroll = ctk.CTkScrollbar(
            hist_list_frame, orientation="vertical",
            command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=hist_scroll.set)
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        hist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox.bind("<Double-Button-1>", self._apply_history_item)

        # Input satırı (prompt + komut girişi)
        self._build_input_area()

        # Kısayollar çubuğu
        self._build_shortcuts_bar()

    def _build_input_area(self):
        input_frame = ctk.CTkFrame(self.main_container, fg_color="#151515", corner_radius=0)
        input_frame.pack(fill=tk.X, padx=10, pady=(3, 0))

        self.prompt_label = ctk.CTkLabel(
            input_frame, text="uzzy> ", text_color="#4CAF50",
            font=("Consolas", 13, "bold"))
        self.prompt_label.pack(side=tk.LEFT, padx=(10, 0), pady=4)

        self.cmd_entry = ctk.CTkEntry(
            input_frame, fg_color="transparent", border_width=0,
            text_color="#E0E0E0", font=("Consolas", 13),
            placeholder_text="komut yazın...")
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 10), pady=4)

        self.cmd_entry.bind("<Return>",    self._on_entry_enter)
        self.cmd_entry.bind("<Up>",        self._on_entry_up)
        self.cmd_entry.bind("<Down>",      self._on_entry_down)
        self.cmd_entry.bind("<Tab>",       self._on_entry_tab)
        self.cmd_entry.bind("<Control-c>", self._on_entry_ctrlc)
        self.cmd_entry.focus_set()

    def _terminal_key_guard(self, event):
        # Ctrl+C (kopyala) ve Ctrl+A (tümünü seç) geçsin, diğer tuşları engelle
        if event.state & 0x4 and event.keysym.lower() in ("c", "a"):
            return None
        return "break"

    def _focus_input(self):
        self.cmd_entry.focus_set()

    def _on_entry_enter(self, event):
        cmd = self.cmd_entry.get()
        self._history_idx = -1
        self.cmd_entry.delete(0, tk.END)

        prompt = self.prompt_label.cget("text")
        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"{prompt}{cmd}\n", "info")
        self.terminal.see("end")

        if cmd.strip():
            self._add_to_history(cmd)

        if self.serial_conn.is_connected:
            self.serial_conn.write_data(cmd + "\r\n")
        else:
            if cmd.strip():
                pass

    def _on_entry_up(self, event):
        if not self.command_history:
            return "break"
        self._history_idx = min(self._history_idx + 1, len(self.command_history) - 1)
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, self.command_history[self._history_idx])
        return "break"

    def _on_entry_down(self, event):
        if self._history_idx <= 0:
            self._history_idx = -1
            self.cmd_entry.delete(0, tk.END)
            return "break"
        self._history_idx -= 1
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, self.command_history[self._history_idx])
        return "break"

    def _on_entry_tab(self, event):
        if self.serial_conn.is_connected:
            self.serial_conn.write_data(self.cmd_entry.get() + "\t")
        return "break"

    def _on_entry_ctrlc(self, event):
        if self.serial_conn.is_connected:
            self.serial_conn.write_data("\x03")
        return "break"

    def _update_prompt(self, data):
        """Switch çıktısından prompt satırını (hostname# veya hostname(config)#) yakalar."""
        lines = data.replace('\r', '').split('\n')
        for line in reversed(lines):
            line = line.strip()
            if re.match(r'^\S+(?:\([^)]+\))?[#>]\s*$', line):
                self.prompt_label.configure(text=line.rstrip() + " ")
                # Hostname'i de güncelle
                m = re.match(r'^(\S+?)(?:\([^)]+\))?[#>]', line)
                if m and not self.switch_hostname:
                    self.switch_hostname = m.group(1)
                    self.hostname_label.configure(text=self.switch_hostname, text_color="#4CAF50")
                break

    def _build_shortcuts_bar(self):
        if hasattr(self, "shortcuts_frame"):
            try:
                self.shortcuts_frame.destroy()
            except Exception:
                pass

        self.shortcuts_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.shortcuts_frame.pack(fill=tk.X, padx=10, pady=(4, 10))

        # Sağ: font boyutu + temizle
        font_frame = ctk.CTkFrame(self.shortcuts_frame, fg_color="transparent")
        font_frame.pack(side=tk.RIGHT)
        ctk.CTkButton(font_frame, text="A-", fg_color="#3C3C3C", width=30, height=24,
                      font=("Consolas", 12, "bold"), command=self.decrease_font).pack(side=tk.LEFT, padx=2)
        ctk.CTkButton(font_frame, text="A+", fg_color="#3C3C3C", width=30, height=24,
                      font=("Consolas", 12, "bold"), command=self.increase_font).pack(side=tk.LEFT, padx=2)
        ctk.CTkButton(font_frame, text="🗑️ Temizle", fg_color="#C62828", hover_color="#E53935",
                      height=24, font=("Segoe UI", 11, "bold"),
                      command=self.clear_terminal).pack(side=tk.LEFT, padx=10)

        # Shortcut butonları
        self.custom_shortcuts = self._load_shortcuts()
        for sc in self.custom_shortcuts:
            btn = ctk.CTkButton(
                self.shortcuts_frame, text=sc["label"], fg_color="#3C3C3C", hover_color="#505050",
                height=24, font=("Consolas", 11, "bold"),
                command=lambda c=sc["command"]: self.send_shortcut_command(c))
            btn.pack(side=tk.LEFT, padx=3)
            btn.bind("<Button-3>", lambda e, s=sc: self._remove_shortcut_confirm(s))

        # "+" ekle
        ctk.CTkButton(
            self.shortcuts_frame, text="+", fg_color="#2E7D32", hover_color="#388E3C",
            width=28, height=24, font=("Segoe UI", 13, "bold"),
            command=self._add_shortcut_dialog).pack(side=tk.LEFT, padx=3)

    def _build_status_bar(self, root):
        self.status_var = tk.StringVar(value="Sistem Hazır - Port Bekleniyor...")
        self.status_bar = ctk.CTkLabel(
            root, textvariable=self.status_var, anchor=tk.W,
            fg_color="#C62828", text_color="white", font=("Segoe UI", 12, "bold"))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, ipadx=10, ipady=4)

    # ──────────────────────────────────────────────────────────────
    # KISAYOL YÖNETİMİ
    # ──────────────────────────────────────────────────────────────

    def _load_shortcuts(self):
        if os.path.exists(SHORTCUTS_FILE):
            try:
                with open(SHORTCUTS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return list(DEFAULT_SHORTCUTS)

    def _save_shortcuts(self):
        try:
            with open(SHORTCUTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.custom_shortcuts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Hata", f"Kısayollar kaydedilemedi:\n{e}")

    def _add_shortcut_dialog(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Kısayol Ekle")
        dialog.geometry("360x190")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Kısayol Etiketi:", text_color="#A0A0A0").pack(pady=(15, 2))
        lbl_entry = ctk.CTkEntry(dialog, placeholder_text="Örn: sh arp")
        lbl_entry.pack(padx=20, fill=tk.X)

        ctk.CTkLabel(dialog, text="Komut:", text_color="#A0A0A0").pack(pady=(10, 2))
        cmd_entry = ctk.CTkEntry(dialog, placeholder_text="Örn: show arp")
        cmd_entry.pack(padx=20, fill=tk.X)

        def save():
            lbl = lbl_entry.get().strip()
            cmd = cmd_entry.get().strip()
            if not lbl or not cmd:
                return
            self.custom_shortcuts.append({"label": lbl, "command": cmd})
            self._save_shortcuts()
            dialog.destroy()
            self._build_shortcuts_bar()

        ctk.CTkButton(dialog, text="EKLE", fg_color="#2E7D32", hover_color="#388E3C",
                      command=save).pack(pady=14)

    def _remove_shortcut_confirm(self, sc):
        if messagebox.askyesno("Kısayol Sil", f'"{sc["label"]}" kısayolu silinsin mi?'):
            self.custom_shortcuts = [s for s in self.custom_shortcuts if s != sc]
            self._save_shortcuts()
            self._build_shortcuts_bar()

    # ──────────────────────────────────────────────────────────────
    # KOMUT GEÇMİŞİ
    # ──────────────────────────────────────────────────────────────

    def _add_to_history(self, cmd):
        cmd = cmd.strip()
        if not cmd:
            return
        if cmd in self.command_history:
            self.command_history.remove(cmd)
        self.command_history.insert(0, cmd)
        self.command_history = self.command_history[:60]
        self.history_listbox.delete(0, tk.END)
        for c in self.command_history:
            self.history_listbox.insert(tk.END, c)

    def _apply_history_item(self, event):
        sel = self.history_listbox.curselection()
        if not sel:
            return
        cmd = self.history_listbox.get(sel[0])
        self.send_shortcut_command(cmd)

    def _clear_history(self):
        self.command_history.clear()
        self.history_listbox.delete(0, tk.END)

    # ──────────────────────────────────────────────────────────────
    # HOSTNAME TESPİTİ
    # ──────────────────────────────────────────────────────────────

    def _detect_hostname(self):
        if not self.serial_conn.is_connected:
            return
        self.serial_conn.write_data("show running-config | include hostname\r\n")
        self.root.after(1800, self._parse_hostname)

    def _parse_hostname(self):
        content = self.terminal.get("1.0", "end").splitlines()
        for line in reversed(content[-60:]):
            match = re.search(r'hostname\s+(\S+)', line, re.IGNORECASE)
            if match:
                self.switch_hostname = match.group(1)
                self.hostname_label.configure(text=self.switch_hostname, text_color="#4CAF50")
                port = self.serial_conn.port
                baud = self.baudrate_var.get()
                self.status_var.set(f"Bağlı: {port} ({baud} Baud)  |  {self.switch_hostname}")
                return

    # ──────────────────────────────────────────────────────────────
    # PORT SAĞ TIK
    # ──────────────────────────────────────────────────────────────

    def _on_port_right_click(self, p_num, event):
        if p_num not in self.selected_ports:
            self.selected_ports.add(p_num)
            self.update_port_grid_colors()
        self.port_context_menu.post(event.x_root, event.y_root)

    # ──────────────────────────────────────────────────────────────
    # YARDIMCI
    # ──────────────────────────────────────────────────────────────

    def set_window_icon(self, window):
        import sys
        def resource_path(relative_path):
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_path, relative_path)

        icon_path_ico = resource_path("uzzy_icon.ico")
        icon_path_png = resource_path("uzzy_icon.png")

        def apply_icon():
            try:
                if os.name == 'nt':
                    window.iconbitmap(icon_path_ico)
                else:
                    icon_img = tk.PhotoImage(file=icon_path_png)
                    window.iconphoto(False, icon_img)
            except Exception:
                pass

        apply_icon()
        window.after(200, apply_icon)

    def on_baudrate_change(self, choice):
        if self.serial_conn.is_connected:
            self.log_to_terminal(f"\n[SİSTEM] Baud rate {choice} olarak değiştirildi. Yeniden bağlanılıyor...\n")
            self.serial_conn.disconnect()

    def close_current_popup(self):
        if self.active_popup:
            try:
                self.active_popup.destroy()
            except Exception:
                pass
        self.active_popup = None
        self.mac_display_area = None

    def log_to_terminal(self, message):
        tag = None
        msg_upper = message.upper()
        if "[HATA]" in msg_upper or "HATASI" in msg_upper or "ERROR" in msg_upper:
            tag = "error"
        elif "[BİLGİ]" in msg_upper or "[SİSTEM]" in msg_upper or "BAĞLANDI" in msg_upper or "BAĞLANTISI KURULDU" in msg_upper:
            tag = "info"
        elif "[YENİ CİHAZ]" in msg_upper or "[VLAN OLUŞTURULDU]" in msg_upper or "ATANDI]" in msg_upper or "AYARLANDI]" in msg_upper or "BAŞARIYLA" in msg_upper or "TAMAMLANDI" in msg_upper:
            tag = "success"
        elif "[UYARI]" in msg_upper:
            tag = "warning"

        # ANSI escape sequence'larını temizle (renk kodları, imleç hareketi vb.)
        message = re.sub(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', message)
        message = message.replace('\r\n', '\n').replace('\r', '\n').replace('\x07', '').replace('\x00', '')

        if '\b' in message:
            for char in message:
                if char == '\b':
                    if self.terminal.index("end-1c") != "1.0":
                        self.terminal.delete("end-2c", "end-1c")
                else:
                    if tag:
                        self.terminal.insert("end", char, tag)
                    else:
                        self.terminal.insert("end", char)
        else:
            if tag:
                self.terminal.insert("end", message, tag)
            else:
                self.terminal.insert("end", message)

        self.terminal.see("end")
        self.terminal.mark_set("insert", "end")

        if self.mac_display_area:
            try:
                self.mac_display_area.insert("end", message)
                self.mac_display_area.see("end")
            except Exception:
                self.mac_display_area = None

    def clear_terminal(self):
        self.terminal.delete("1.0", tk.END)


    def send_shortcut_command(self, cmd):
        self._add_to_history(cmd)
        prompt = self.prompt_label.cget("text")
        self.terminal.insert("end", f"{prompt}{cmd}\n", "info")
        self.terminal.see("end")
        if self.serial_conn.is_connected:
            self.serial_conn.write_data("\r\nend\r\n" + cmd + "\r\n")

    def increase_font(self):
        if self.terminal_font_size < 36:
            self.terminal_font_size += 1
            self.terminal.configure(font=("Consolas", self.terminal_font_size))

    def decrease_font(self):
        if self.terminal_font_size > 6:
            self.terminal_font_size -= 1
            self.terminal.configure(font=("Consolas", self.terminal_font_size))

    # ──────────────────────────────────────────────────────────────
    # PORT PANELİ
    # ──────────────────────────────────────────────────────────────

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

            btn = tk.Button(
                self.switch_panel, text=str(i), width=3, height=1,
                bg="#3C3C3C", fg="#E0E0E0", font=("Consolas", 10, "bold"),
                bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#606060")
            btn.grid(row=row, column=col, padx=pad_x, pady=3)
            btn.bind("<Button-1>", lambda e, p=i: self.on_port_button_press(p))
            btn.bind("<B1-Motion>", self.on_port_drag)
            btn.bind("<Button-3>", lambda e, p=i: self._on_port_right_click(p, e))
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
                if start_p is None:
                    return
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
            except Exception:
                pass

    def clear_port_selection(self):
        self.selected_ports.clear()
        self.update_port_grid_colors()

    def select_all_ports(self):
        self.selected_ports = set(range(1, int(self.port_count_var.get()) + 1))
        self.update_port_grid_colors()

    # ──────────────────────────────────────────────────────────────
    # OTOMATİK ALGILAMA
    # ──────────────────────────────────────────────────────────────

    def auto_detect_ports(self):
        if not self.serial_conn.is_connected:
            messagebox.showwarning("Uyarı", "Lütfen önce cihaza bağlanın.")
            return
        self.log_to_terminal("\n[BİLGİ] Model ve port sayısı otomatik algılanıyor...\n")
        self.model_label.configure(text="Algılanıyor...", text_color="#FFA726")

        self.serial_conn.write_data("terminal length 0\r\n")
        time.sleep(0.3)
        self.serial_conn.write_data("show version\r\n")
        time.sleep(0.3)
        self.serial_conn.write_data("show interfaces status\r\n")

        threading.Thread(target=self._start_analyze_delay, daemon=True).start()

    def _start_analyze_delay(self):
        time.sleep(4)
        self.root.after(0, self._process_port_count)

    def _parse_model_from_content(self, lines):
        for line in lines:
            match = re.search(r'\b(AT-[\w/.-]+)', line, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    def _process_port_count(self):
        content = self.terminal.get("1.0", "end").splitlines()
        found_ports = []

        detected_model = self._parse_model_from_content(content[-500:])
        if detected_model:
            self.model_label.configure(text=detected_model, text_color="#4CAF50")
        else:
            self.model_label.configure(text="Algılanamadı", text_color="#FFA726")

        for line in content[-300:]:
            m = re.match(r'^\s*(Gi|Fa|Te|Tw|Fo|Eth|port)[a-zA-Z]*\s*((?:\d+[/.]){0,2}\d+)',
                         line, re.IGNORECASE)
            if m:
                num_part = m.group(2)
                port_name = f"{m.group(1)}{num_part}"
                if num_part != "0" and port_name not in found_ports:
                    found_ports.append(port_name)

        def natural_sort_key(s):
            return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
        found_ports.sort(key=natural_sort_key)

        self.port_mapping = {i + 1: p for i, p in enumerate(found_ports)}

        total = len(found_ports)
        if total > 0:
            final_count = ("8" if total <= 8 else "12" if total <= 12 else "16" if total <= 16
                           else "24" if total <= 24 else "28" if total <= 28
                           else "48" if total <= 48 else "52")
            self.port_count_var.set(final_count)
            self.root.after(0, self.draw_port_panel)
            model_info = f" | Model: {detected_model}" if detected_model else ""
            self.log_to_terminal(
                f"\n[BAŞARILI] {total} port algılandı{model_info}. "
                f"Port 1 = {self.port_mapping.get(1, '')}. Arayüz güncellendi.\n")
        else:
            self.log_to_terminal(
                "\n[HATA] Otomatik algılama başarısız. Cihazın 'enable' modunda olduğuna emin olun.\n")

    # ──────────────────────────────────────────────────────────────
    # BAĞLANTI
    # ──────────────────────────────────────────────────────────────

    def refresh_connection(self):
        self.log_to_terminal("\n[SİSTEM] Bağlantı yenileniyor...\n")
        if self.serial_conn.is_connected:
            self.serial_conn.disconnect()
        self.scanner.discovered_ports.clear()
        self.status_var.set("Sistem Hazır - Yeniden Bağlanılıyor...")

    def check_for_data(self):
        while not self.serial_conn.data_queue.empty():
            data = self.serial_conn.data_queue.get()
            if getattr(self, 'is_capturing', False) and hasattr(self, 'capture_file_obj') and self.capture_file_obj:
                self.capture_file_obj.write(data)
                self.capture_file_obj.flush()
                self.reset_capture_timer()
            self._update_prompt(data)
            self.log_to_terminal(data)
        self.root.after(50, self.check_for_data)

    def auto_connect_service(self):
        if not self.serial_conn.is_connected:
            current_ports = self.scanner.discovered_ports
            if current_ports:
                target_port = list(current_ports)[0]
                self.log_to_terminal(f"\n[OTOMATİK BAĞLANTI] {target_port} tespit edildi, bağlanılıyor...\n")
                selected_baud = int(self.baudrate_var.get())
                success, msg = self.serial_conn.connect(port=target_port, baudrate=selected_baud)
                if success:
                    self.status_var.set(f"Bağlı: {target_port} ({selected_baud} Baud)")
                    self.log_to_terminal(f"--- {target_port} BAĞLANTISI KURULDU ({selected_baud} Baud) ---\n")
                    self.root.after(1500, lambda: self.serial_conn.write_data("\r\nterminal length 0\r\n"))
                    self.root.after(3500, self._detect_hostname)
                else:
                    self.status_var.set(f"Bağlantı Hatası: {target_port}")
                    self.log_to_terminal(f"[HATA] {msg}\n")

        elif self.serial_conn.is_connected:
            if self.serial_conn.port not in self.scanner.discovered_ports:
                self.log_to_terminal(f"\n[BİLGİ] {self.serial_conn.port} fiziksel olarak ayrıldı.\n")
                self.serial_conn.disconnect()
                self.status_var.set("Cihaz Ayrıldı - Yeni Port Bekleniyor...")
                self.model_label.configure(text="—", text_color="#E0E0E0")
                self.hostname_label.configure(text="—", text_color="#E0E0E0")
                self.switch_hostname = ""
                self.prompt_label.configure(text="uzzy> ")

        self.root.after(1000, self.auto_connect_service)

    # ──────────────────────────────────────────────────────────────
    # CONFIG BACKUP
    # ──────────────────────────────────────────────────────────────

    def start_config_backup(self):
        if not self.serial_conn.is_connected:
            messagebox.showerror("Hata", "Lütfen önce bir cihaza bağlanın.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Switch Config'ini Kaydet")
        if not filepath:
            return

        try:
            self.capture_filepath = filepath
            self.capture_file_obj = open(self.capture_filepath, "w", encoding="utf-8")
            hostname_info = f" | Host: {self.switch_hostname}" if self.switch_hostname else ""
            self.capture_file_obj.write(
                f"! --- Uzzy Config Backup | Allied Telesis{hostname_info} ---\n\n")
            self.is_capturing = True
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya oluşturulamadı:\n{e}")
            return

        self.serial_conn.write_data("terminal length 0\r\n")
        self.root.after(500, lambda: self.serial_conn.write_data("show running-config\r\n"))
        self.log_to_terminal("\n[BİLGİ] Config indiriliyor... Lütfen bitene kadar bekleyin.\n")
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

    icon_path_ico = resource_path("uzzy_icon.ico")
    icon_path_png = resource_path("uzzy_icon.png")

    try:
        if os.name == 'nt':
            root.iconbitmap(icon_path_ico)
        else:
            icon_img = tk.PhotoImage(file=icon_path_png)
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
        if HAS_PIL:
            img = Image.open(icon_path_png).convert("RGBA")
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
            splash_img = tk.PhotoImage(file=icon_path_png).subsample(3, 3)

        splash_label = tk.Label(splash, image=splash_img, bg="#1A1A1A", bd=0)
        splash_label.image = splash_img
        splash_label.pack()
        splash.update_idletasks()
        w = splash_label.winfo_reqwidth()
        h = splash_label.winfo_reqheight()
    except Exception as e:
        print(f"Splash resmi yüklenemedi: {e}")
        w, h = 300, 300
        tk.Label(splash, text="UZZY", fg="#E53935", bg="#1A1A1A",
                 font=("Segoe UI", 36, "bold")).pack(expand=True, fill=tk.BOTH)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    splash.geometry(f"{w}x{h}+{(sw // 2) - (w // 2)}+{(sh // 2) - (h // 2)}")

    def fade_out():
        alpha = splash.attributes("-alpha")
        if alpha > 0:
            splash.attributes("-alpha", alpha - 0.05)
            splash.after(30, fade_out)
        else:
            splash.destroy()
            root.deiconify()

    splash.after(3000, fade_out)
    root.mainloop()


if __name__ == "__main__":
    main()
