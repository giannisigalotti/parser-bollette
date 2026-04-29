import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from bollette import (
    build_gas_record,
    build_record,
    classify_pdf,
    export_xlsx,
    load_output_config,
)
from bollette.models import ELECTRICITY_SERVICE_TYPE, GAS_SERVICE_TYPE


APP_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_LABEL = "Default - tutte le colonne"


class BolletteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Estrattore Bollette PDF")
        self.files = []
        self.electricity_output_templates = self.find_output_templates(ELECTRICITY_SERVICE_TYPE)
        self.gas_output_templates = self.find_output_templates(GAS_SERVICE_TYPE)
        self.electricity_output_template = tk.StringVar(value=DEFAULT_TEMPLATE_LABEL)
        self.gas_output_template = tk.StringVar(value=DEFAULT_TEMPLATE_LABEL)

        frm = ttk.Frame(root, padding=20)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Seleziona uno o più PDF:").pack(anchor="w")
        self.file_label = ttk.Label(frm, text="Nessun file selezionato", foreground="gray")
        self.file_label.pack(anchor="w", pady=(0, 10))

        ttk.Button(frm, text="Scegli file PDF", command=self.choose_files).pack(anchor="w")

        electricity_template_frame = ttk.Frame(frm)
        electricity_template_frame.pack(anchor="w", fill="x", pady=(0, 10))
        ttk.Label(electricity_template_frame, text="Template output elettricità:").pack(side="left")
        electricity_template_values = [DEFAULT_TEMPLATE_LABEL] + [p.name for p in self.electricity_output_templates]
        self.electricity_template_combo = ttk.Combobox(
            electricity_template_frame,
            textvariable=self.electricity_output_template,
            values=electricity_template_values,
            state="readonly",
            width=36,
        )
        self.electricity_template_combo.pack(side="left", padx=(8, 0))

        gas_template_frame = ttk.Frame(frm)
        gas_template_frame.pack(anchor="w", fill="x", pady=(0, 10))
        ttk.Label(gas_template_frame, text="Template output gas:").pack(side="left")
        gas_template_values = [DEFAULT_TEMPLATE_LABEL] + [p.name for p in self.gas_output_templates]
        self.gas_template_combo = ttk.Combobox(
            gas_template_frame,
            textvariable=self.gas_output_template,
            values=gas_template_values,
            state="readonly",
            width=36,
        )
        self.gas_template_combo.pack(side="left", padx=(8, 0))

        ttk.Button(frm, text="Estrai e salva", command=self.process).pack(anchor="center", pady=(10, 0))
        self.status = ttk.Label(frm, text="", foreground="blue")
        self.status.pack(anchor="w", pady=(10, 0))

    def find_output_templates(self, service_type):
        templates = []
        for path in sorted(APP_DIR.glob("output_*.json")):
            try:
                load_output_config(path, service_type)
            except (OSError, ValueError):
                continue
            templates.append(path)
        return templates

    def selected_output_columns(self, service_type):
        if service_type == GAS_SERVICE_TYPE:
            selected = self.gas_output_template.get()
            templates = self.gas_output_templates
        else:
            selected = self.electricity_output_template.get()
            templates = self.electricity_output_templates
        if not selected or selected == DEFAULT_TEMPLATE_LABEL:
            return None
        path = next((p for p in templates if p.name == selected), None)
        if path is None:
            raise ValueError(f"Template output non trovato: {selected}")
        return load_output_config(path, service_type)

    def choose_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        self.files = list(files)
        if self.files:
            self.file_label.config(text="\n".join([Path(f).name for f in self.files]), foreground="black")
        else:
            self.file_label.config(text="Nessun file selezionato", foreground="gray")

    def process(self):
        if not self.files:
            messagebox.showerror("Errore", "Seleziona almeno un file PDF.")
            return
        self.status.config(text="Estrazione in corso...")
        self.root.update_idletasks()
        try:
            grouped = {ELECTRICITY_SERVICE_TYPE: [], GAS_SERVICE_TYPE: []}
            for filename in self.files:
                path = Path(filename)
                grouped.setdefault(classify_pdf(path), []).append(path)
            if not grouped[ELECTRICITY_SERVICE_TYPE] and not grouped[GAS_SERVICE_TYPE]:
                raise Exception("Nessun dato estratto.")

            out_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                title="Salva file di output"
            )
            if not out_path:
                self.status.config(text="Operazione annullata.")
                return

            output_path = Path(out_path)
            sheets = []
            if grouped[ELECTRICITY_SERVICE_TYPE]:
                records = [build_record(path) for path in grouped[ELECTRICITY_SERVICE_TYPE]]
                sheets.append(("Elettricità", records, self.selected_output_columns(ELECTRICITY_SERVICE_TYPE), ELECTRICITY_SERVICE_TYPE))
            if grouped[GAS_SERVICE_TYPE]:
                records = [build_gas_record(path) for path in grouped[GAS_SERVICE_TYPE]]
                sheets.append(("Gas", records, self.selected_output_columns(GAS_SERVICE_TYPE), GAS_SERVICE_TYPE))

            export_xlsx(sheets, output_path)
            self.status.config(text=f"File salvato: {output_path}")
            messagebox.showinfo("Successo", f"File salvato:\n{output_path}")
        except Exception as e:
            self.status.config(text=f"Errore: {e}")
            messagebox.showerror("Errore", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = BolletteApp(root)
    root.mainloop()
