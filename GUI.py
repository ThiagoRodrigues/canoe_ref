"""
Optimization Model GUI

Requirements implemented:
1) Class TECH that takes an input commodity and converts it to an output commodity.
2) Class Commodity with a variable cost attribute.
3) A Tkinter GUI to create commodities and technologies and connect a commodity as input or output of a technology.

Notes:
- No external dependencies beyond the Python standard library (tkinter, json, dataclasses).
- You can save/load your data to/from JSON files.
- Technologies reference commodities by name. The GUI keeps the dropdowns in sync when commodities are added/renamed/deleted.
- Basic validation and helpful status messages included.

Run: python optimization_gui.py
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


# ------------------------------
# Core Data Model
# ------------------------------
@dataclass
class Commodity:
    name: str
    variable_cost: float  # cost per unit

    def to_dict(self) -> dict:
        return {"name": self.name, "variable_cost": self.variable_cost}

    @staticmethod
    def from_dict(d: dict) -> "Commodity":
        return Commodity(name=d["name"], variable_cost=float(d["variable_cost"]))


@dataclass
class TECH:
    name: str
    input_commodity: Optional[str] = None  # reference by commodity name
    output_commodity: Optional[str] = None # reference by commodity name
    conversion_ratio: float = 1.0          # units out per unit in (default 1:1)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "input_commodity": self.input_commodity,
            "output_commodity": self.output_commodity,
            "conversion_ratio": self.conversion_ratio,
        }

    @staticmethod
    def from_dict(d: dict) -> "TECH":
        return TECH(
            name=d["name"],
            input_commodity=d.get("input_commodity"),
            output_commodity=d.get("output_commodity"),
            conversion_ratio=float(d.get("conversion_ratio", 1.0)),
        )


class ModelStore:
    """In-memory store for commodities and technologies."""

    def __init__(self) -> None:
        self.commodities: Dict[str, Commodity] = {}
        self.technologies: Dict[str, TECH] = {}

    # Commodity operations
    def add_or_update_commodity(self, c: Commodity) -> None:
        self.commodities[c.name] = c

    def delete_commodity(self, name: str) -> None:
        if name in self.commodities:
            del self.commodities[name]
            # Remove references from technologies if they pointed to this commodity
            for t in self.technologies.values():
                if t.input_commodity == name:
                    t.input_commodity = None
                if t.output_commodity == name:
                    t.output_commodity = None

    def rename_commodity(self, old: str, new: str) -> None:
        if old not in self.commodities:
            return
        c = self.commodities.pop(old)
        c.name = new
        self.commodities[new] = c
        for t in self.technologies.values():
            if t.input_commodity == old:
                t.input_commodity = new
            if t.output_commodity == old:
                t.output_commodity = new

    # Technology operations
    def add_or_update_tech(self, t: TECH) -> None:
        self.technologies[t.name] = t

    def delete_tech(self, name: str) -> None:
        if name in self.technologies:
            del self.technologies[name]

    def rename_tech(self, old: str, new: str) -> None:
        if old not in self.technologies:
            return
        t = self.technologies.pop(old)
        t.name = new
        self.technologies[new] = t

    # Serialization
    def to_dict(self) -> dict:
        return {
            "commodities": [c.to_dict() for c in self.commodities.values()],
            "technologies": [t.to_dict() for t in self.technologies.values()],
        }

    @staticmethod
    def from_dict(d: dict) -> "ModelStore":
        store = ModelStore()
        for c in d.get("commodities", []):
            cc = Commodity.from_dict(c)
            store.commodities[cc.name] = cc
        for t in d.get("technologies", []):
            tt = TECH.from_dict(t)
            store.technologies[tt.name] = tt
        return store


# ------------------------------
# GUI
# ------------------------------
class OptimizationGUI(ttk.Frame):
    def __init__(self, master: tk.Tk, store: ModelStore):
        super().__init__(master, padding=12)
        self.master = master
        self.store = store
        self.grid(sticky="nsew")
        self._build_layout()
        self._refresh_all()

    # ---- Layout ----
    def _build_layout(self) -> None:
        self.master.title("Optimization Model GUI — Commodities & TECH")
        self.master.geometry("980x620")
        self.master.minsize(900, 580)

        # Configure global weights
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Top-level panes
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")

        self.commodity_frame = self._build_commodity_frame(paned)
        self.tech_frame = self._build_tech_frame(paned)
        paned.add(self.commodity_frame, weight=1)
        paned.add(self.tech_frame, weight=1)

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w")
        status.grid(row=1, column=0, sticky="ew", pady=(8,0))

        # Menu
        self._build_menu()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.master)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self._new_project)
        file_menu.add_command(label="Open...", command=self._open)
        file_menu.add_command(label="Save As...", command=self._save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.master.config(menu=menubar)

    # ---- Commodity Panel ----
    def _build_commodity_frame(self, parent) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="Commodities", padding=12)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)

        # Inputs
        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky="w")
        self.c_name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.c_name_var).grid(row=0, column=1, sticky="ew", padx=(8,0))

        ttk.Label(frame, text="Variable Cost:").grid(row=1, column=0, sticky="w")
        self.c_cost_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.c_cost_var).grid(row=1, column=1, sticky="ew", padx=(8,0))

        # Buttons
        btns = ttk.Frame(frame)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6,6))
        for i in range(4):
            btns.columnconfigure(i, weight=1)
        ttk.Button(btns, text="Add / Update", command=self._commodity_add_update).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(btns, text="Delete", command=self._commodity_delete).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(btns, text="Clear", command=self._commodity_clear_form).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(btns, text="Rename", command=self._commodity_rename_dialog).grid(row=0, column=3, sticky="ew", padx=2)

        # List
        self.commodity_list = tk.Listbox(frame, exportselection=False)
        self.commodity_list.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(6,0))
        self.commodity_list.bind("<<ListboxSelect>>", self._on_commodity_select)

        return frame

    # ---- Technology Panel ----
    def _build_tech_frame(self, parent) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text="Technologies (TECH)", padding=12)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(4, weight=1)

        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky="w")
        self.t_name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.t_name_var).grid(row=0, column=1, sticky="ew", padx=(8,0))

        ttk.Label(frame, text="Input Commodity:").grid(row=1, column=0, sticky="w")
        self.t_input_var = tk.StringVar()
        self.t_input_combo = ttk.Combobox(frame, textvariable=self.t_input_var, state="readonly")
        self.t_input_combo.grid(row=1, column=1, sticky="ew", padx=(8,0))

        ttk.Label(frame, text="Output Commodity:").grid(row=2, column=0, sticky="w")
        self.t_output_var = tk.StringVar()
        self.t_output_combo = ttk.Combobox(frame, textvariable=self.t_output_var, state="readonly")
        self.t_output_combo.grid(row=2, column=1, sticky="ew", padx=(8,0))

        ttk.Label(frame, text="Conversion Ratio (out per in):").grid(row=3, column=0, sticky="w")
        self.t_ratio_var = tk.StringVar(value="1.0")
        ttk.Entry(frame, textvariable=self.t_ratio_var).grid(row=3, column=1, sticky="ew", padx=(8,0))

        btns = ttk.Frame(frame)
        btns.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(6,6))
        for i in range(4):
            btns.columnconfigure(i, weight=1)
        ttk.Button(btns, text="Add / Update", command=self._tech_add_update).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(btns, text="Delete", command=self._tech_delete).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(btns, text="Clear", command=self._tech_clear_form).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(btns, text="Rename", command=self._tech_rename_dialog).grid(row=0, column=3, sticky="ew", padx=2)

        self.tech_list = tk.Listbox(frame, exportselection=False)
        self.tech_list.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(6,0))
        self.tech_list.bind("<<ListboxSelect>>", self._on_tech_select)

        return frame

    # ---- Helpers ----
    def _refresh_all(self) -> None:
        self._refresh_commodity_list()
        self._refresh_tech_list()
        self._refresh_commodity_dropdowns()

    def _refresh_commodity_list(self) -> None:
        self.commodity_list.delete(0, tk.END)
        for name in sorted(self.store.commodities.keys()):
            c = self.store.commodities[name]
            self.commodity_list.insert(tk.END, f"{c.name}  (cost={c.variable_cost})")

    def _refresh_tech_list(self) -> None:
        self.tech_list.delete(0, tk.END)
        for name in sorted(self.store.technologies.keys()):
            t = self.store.technologies[name]
            self.tech_list.insert(
                tk.END,
                f"{t.name}  [in: {t.input_commodity or '-'} → out: {t.output_commodity or '-'} | ratio={t.conversion_ratio}]",
            )

    def _refresh_commodity_dropdowns(self) -> None:
        names = sorted(self.store.commodities.keys())
        self.t_input_combo["values"] = names
        self.t_output_combo["values"] = names

        # Keep currently selected values if still valid
        if self.t_input_var.get() not in names:
            self.t_input_var.set("")
        if self.t_output_var.get() not in names:
            self.t_output_var.set("")

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    # ---- Commodity actions ----
    def _commodity_add_update(self) -> None:
        name = self.c_name_var.get().strip()
        cost_str = self.c_cost_var.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Commodity name is required.")
            return
        try:
            cost = float(cost_str)
        except ValueError:
            messagebox.showwarning("Validation", "Variable cost must be a number.")
            return
        # If renaming is intended, use Rename. Here we simply add/update by key = name.
        self.store.add_or_update_commodity(Commodity(name=name, variable_cost=cost))
        self._refresh_commodity_list()
        self._refresh_commodity_dropdowns()
        self._set_status(f"Commodity '{name}' saved.")

    def _commodity_delete(self) -> None:
        sel = self._get_selected(self.commodity_list)
        if sel is None:
            messagebox.showinfo("Delete Commodity", "Select a commodity to delete.")
            return
        # Extract name before the two spaces used in display format
        display = self.commodity_list.get(sel)
        name = display.split("  ")[0]
        if messagebox.askyesno("Confirm Delete", f"Delete commodity '{name}'? This will also clear references in technologies."):
            self.store.delete_commodity(name)
            self._refresh_all()
            self._set_status(f"Commodity '{name}' deleted.")

    def _commodity_clear_form(self) -> None:
        self.c_name_var.set("")
        self.c_cost_var.set("")
        self.commodity_list.selection_clear(0, tk.END)
        self._set_status("Commodity form cleared.")

    def _on_commodity_select(self, _event=None) -> None:
        sel = self._get_selected(self.commodity_list)
        if sel is None:
            return
        display = self.commodity_list.get(sel)
        name = display.split("  ")[0]
        c = self.store.commodities.get(name)
        if c:
            self.c_name_var.set(c.name)
            self.c_cost_var.set(str(c.variable_cost))
            self._set_status(f"Selected commodity '{c.name}'.")

    def _commodity_rename_dialog(self) -> None:
        sel = self._get_selected(self.commodity_list)
        if sel is None:
            messagebox.showinfo("Rename Commodity", "Select a commodity to rename.")
            return
        display = self.commodity_list.get(sel)
        old_name = display.split("  ")[0]

        def do_rename():
            new_name = entry.get().strip()
            if not new_name:
                messagebox.showwarning("Validation", "New name cannot be empty.")
                return
            if new_name in self.store.commodities and new_name != old_name:
                messagebox.showwarning("Validation", "A commodity with this name already exists.")
                return
            self.store.rename_commodity(old_name, new_name)
            dlg.destroy()
            self._refresh_all()
            self._set_status(f"Commodity renamed to '{new_name}'.")

        dlg = tk.Toplevel(self)
        dlg.title("Rename Commodity")
        dlg.transient(self.master)
        dlg.grab_set()
        ttk.Label(dlg, text=f"Rename '{old_name}' to:").grid(row=0, column=0, padx=10, pady=10)
        entry = ttk.Entry(dlg)
        entry.grid(row=0, column=1, padx=10, pady=10)
        entry.insert(0, old_name)
        ttk.Button(dlg, text="OK", command=do_rename).grid(row=1, column=0, columnspan=2, pady=(0,10))
        entry.focus_set()

    # ---- Technology actions ----
    def _tech_add_update(self) -> None:
        name = self.t_name_var.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Technology name is required.")
            return
        # Conversion ratio
        try:
            ratio = float(self.t_ratio_var.get().strip() or "1.0")
            if ratio <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validation", "Conversion ratio must be a positive number.")
            return

        in_name = self.t_input_var.get().strip() or None
        out_name = self.t_output_var.get().strip() or None

        # If commodities are specified, ensure they exist
        if in_name and in_name not in self.store.commodities:
            messagebox.showwarning("Validation", f"Input commodity '{in_name}' does not exist.")
            return
        if out_name and out_name not in self.store.commodities:
            messagebox.showwarning("Validation", f"Output commodity '{out_name}' does not exist.")
            return

        self.store.add_or_update_tech(TECH(name=name, input_commodity=in_name, output_commodity=out_name, conversion_ratio=ratio))
        self._refresh_tech_list()
        self._set_status(f"Technology '{name}' saved.")

    def _tech_delete(self) -> None:
        sel = self._get_selected(self.tech_list)
        if sel is None:
            messagebox.showinfo("Delete Technology", "Select a technology to delete.")
            return
        display = self.tech_list.get(sel)
        name = display.split("  ")[0]
        if messagebox.askyesno("Confirm Delete", f"Delete technology '{name}'?"):
            self.store.delete_tech(name)
            self._refresh_tech_list()
            self._set_status(f"Technology '{name}' deleted.")

    def _tech_clear_form(self) -> None:
        self.t_name_var.set("")
        self.t_input_var.set("")
        self.t_output_var.set("")
        self.t_ratio_var.set("1.0")
        self.tech_list.selection_clear(0, tk.END)
        self._set_status("Technology form cleared.")

    def _on_tech_select(self, _event=None) -> None:
        sel = self._get_selected(self.tech_list)
        if sel is None:
            return
        display = self.tech_list.get(sel)
        name = display.split("  ")[0]
        t = self.store.technologies.get(name)
        if t:
            self.t_name_var.set(t.name)
            self.t_input_var.set(t.input_commodity or "")
            self.t_output_var.set(t.output_commodity or "")
            self.t_ratio_var.set(str(t.conversion_ratio))
            self._set_status(f"Selected technology '{t.name}'.")

    def _tech_rename_dialog(self) -> None:
        sel = self._get_selected(self.tech_list)
        if sel is None:
            messagebox.showinfo("Rename Technology", "Select a technology to rename.")
            return
        display = self.tech_list.get(sel)
        old_name = display.split("  ")[0]

        def do_rename():
            new_name = entry.get().strip()
            if not new_name:
                messagebox.showwarning("Validation", "New name cannot be empty.")
                return
            if new_name in self.store.technologies and new_name != old_name:
                messagebox.showwarning("Validation", "A technology with this name already exists.")
                return
            self.store.rename_tech(old_name, new_name)
            dlg.destroy()
            self._refresh_tech_list()
            self._set_status(f"Technology renamed to '{new_name}'.")

        dlg = tk.Toplevel(self)
        dlg.title("Rename Technology")
        dlg.transient(self.master)
        dlg.grab_set()
        ttk.Label(dlg, text=f"Rename '{old_name}' to:").grid(row=0, column=0, padx=10, pady=10)
        entry = ttk.Entry(dlg)
        entry.grid(row=0, column=1, padx=10, pady=10)
        entry.insert(0, old_name)
        ttk.Button(dlg, text="OK", command=do_rename).grid(row=1, column=0, columnspan=2, pady=(0,10))
        entry.focus_set()

    # ---- File Ops ----
    def _new_project(self) -> None:
        if not self._confirm_discard_changes():
            return
        self.store = ModelStore()
        self._refresh_all()
        self._set_status("New project created.")

    def _open(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Model JSON",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.store = ModelStore.from_dict(data)
            self._refresh_all()
            self._set_status(f"Loaded: {path}")
        except Exception as e:
            messagebox.showerror("Open Error", f"Failed to open file.\n{e}")

    def _save_as(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Model As",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.store.to_dict(), f, indent=2)
            self._set_status(f"Saved to: {path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file.\n{e}")

    def _about(self) -> None:
        messagebox.showinfo(
            "About",
            "Optimization Model GUI\n\n- Manage Commodities with variable costs\n- Define TECH that converts one commodity to another\n- Connect input and output commodities to a technology\n- Save/Load as JSON",
        )

    def _confirm_discard_changes(self) -> bool:
        return messagebox.askyesno(
            "Confirm",
            "Discard current changes and continue?",
        )

    @staticmethod
    def _get_selected(listbox: tk.Listbox) -> Optional[int]:
        sel = listbox.curselection()
        if not sel:
            return None
        return sel[0]


# ------------------------------
# App bootstrap with a small demo
# ------------------------------

def main() -> None:
    store = ModelStore()

    # Optional: add a couple of demo items so the UI isn't empty on first run
    store.add_or_update_commodity(Commodity(name="Electricity", variable_cost=50.0))
    store.add_or_update_commodity(Commodity(name="Hydrogen", variable_cost=120.0))
    store.add_or_update_tech(TECH(name="Electrolyzer", input_commodity="Electricity", output_commodity="Hydrogen", conversion_ratio=0.7))

    root = tk.Tk()
    # Use ttk theme for a cleaner look
    try:
        root.style = ttk.Style()
        if "clam" in root.style.theme_names():
            root.style.theme_use("clam")
    except Exception:
        pass

    app = OptimizationGUI(root, store)
    root.mainloop()


if __name__ == "__main__":
    main()
