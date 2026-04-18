import tkinter as tk

class PortGrid:
    def __init__(self, parent):
        self.parent = parent
        self.selected_ports = set()
        self.port_buttons = {}
        self.start_port_id = [None]
        self.initial_snapshot = [set()]
        self.drag_mode = [None]
        
        self.frame = tk.Frame(parent, bg="#282828")
        self.frame.pack(padx=20, pady=10)
        self._create_grid()

    def _create_grid(self):
        for i in range(1, 49):
            btn = tk.Button(self.frame, text=str(i), width=4, height=2, bg="#3C3C3C", fg="#E0E0E0", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", relief=tk.FLAT, activebackground="#606060")
            row = (i-1) // 8
            col = (i-1) % 8
            btn.grid(row=row, column=col, padx=2, pady=2)
            btn.bind("<Button-1>", lambda e, p=i: self._on_button_press(p))
            btn.bind("<B1-Motion>", self._on_drag)
            self.port_buttons[i] = btn

    def _update_grid_colors(self):
        for p_id, btn in self.port_buttons.items():
            if p_id in self.selected_ports:
                btn.config(bg="#E53935", fg="white")
            else:
                btn.config(bg="#3C3C3C", fg="#E0E0E0")

    def _on_button_press(self, p_num):
        self.start_port_id[0] = p_num
        self.initial_snapshot[0] = self.selected_ports.copy()
        if p_num in self.selected_ports:
            self.drag_mode[0] = "remove"
            self.selected_ports.remove(p_num)
        else:
            self.drag_mode[0] = "add"
            self.selected_ports.add(p_num)
        self._update_grid_colors()

    def _on_drag(self, event):
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        if widget in self.port_buttons.values():
            try:
                current_p = int(widget.cget("text"))
                start_p = self.start_port_id[0]
                if start_p is None: return
                
                port_range = set(range(min(start_p, current_p), max(start_p, current_p) + 1))
                new_selection = self.initial_snapshot[0].copy()
                
                if self.drag_mode[0] == "add": new_selection.update(port_range)
                else: new_selection.difference_update(port_range)
                
                self.selected_ports = new_selection
                self._update_grid_colors()
            except: pass

    def clear(self):
        self.selected_ports.clear()
        self._update_grid_colors()