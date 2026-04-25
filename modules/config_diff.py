import customtkinter as ctk
from tkinter import filedialog, messagebox
import difflib
import os

def open_diff_tool(parent_gui):
    parent_gui.close_current_popup()
    popup = ctk.CTkToplevel(parent_gui.root)
    parent_gui.set_window_icon(popup)
    popup.transient(parent_gui.root)
    parent_gui.active_popup = popup
    popup.title("Config Karşılaştırma (Diff)")
    popup.geometry("800x600")
    
    top_frame = ctk.CTkFrame(popup, fg_color="transparent")
    top_frame.pack(fill=ctk.X, padx=10, pady=10)
    
    ctk.CTkLabel(top_frame, text="1. Config (Running):", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
    file1_lbl = ctk.CTkLabel(top_frame, text="Seçilmedi", width=200, anchor="w", text_color="#A0A0A0")
    file1_lbl.grid(row=0, column=1, padx=5, pady=5)
    
    ctk.CTkLabel(top_frame, text="2. Config (Yedek/Önceki):", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, padx=5, pady=5)
    file2_lbl = ctk.CTkLabel(top_frame, text="Seçilmedi", width=200, anchor="w", text_color="#A0A0A0")
    file2_lbl.grid(row=1, column=1, padx=5, pady=5)
    
    diff_text = ctk.CTkTextbox(popup, font=("Consolas", 11), wrap="none")
    diff_text.pack(fill=ctk.BOTH, expand=True, padx=10, pady=(0, 10))
    diff_text.tag_config("added", foreground="#4CAF50")
    diff_text.tag_config("removed", foreground="#F44336")
    diff_text.tag_config("info", foreground="#29B6F6")
    
    file1_path, file2_path = [None], [None]
    
    def select_file(index, lbl_widget):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if path:
            lbl_widget.configure(text=os.path.basename(path))
            if index == 1: file1_path[0] = path
            else: file2_path[0] = path
            run_diff()
            
    ctk.CTkButton(top_frame, text="Gözat", width=60, command=lambda: select_file(1, file1_lbl)).grid(row=0, column=2, padx=5)
    ctk.CTkButton(top_frame, text="Gözat", width=60, command=lambda: select_file(2, file2_lbl)).grid(row=1, column=2, padx=5)
    
    def run_diff():
        if not file1_path[0] or not file2_path[0]: return
        with open(file1_path[0], 'r', encoding='utf-8') as f1, open(file2_path[0], 'r', encoding='utf-8') as f2:
            diff = list(difflib.unified_diff(f1.readlines(), f2.readlines(), fromfile='Running', tofile='Backup', n=0))
        diff_text.configure(state="normal")
        diff_text.delete("1.0", ctk.END)
        for line in diff:
            diff_text.insert(ctk.END, line, "added" if line.startswith('+') else "removed" if line.startswith('-') else "info" if line.startswith('@') else None)
        diff_text.configure(state="disabled")