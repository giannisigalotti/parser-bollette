import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from bollette import build_record, BillRecord, export_xlsx, export_csv, load_output_config
from dataclasses import asdict


APP_DIR = Path(__file__).resolve().parent
DEFAULT_TEMPLATE_LABEL = "Default - tutte le colonne"


class BolletteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Estrattore Bollette PDF")
        self.files = []
        self.format = tk.StringVar(value="xlsx")
        self.output_templates = self.find_output_templates()
        self.output_template = tk.StringVar(value=DEFAULT_TEMPLATE_LABEL)

        frm = ttk.Frame(root, padding=20)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Seleziona uno o più PDF:").pack(anchor="w")
        self.file_label = ttk.Label(frm, text="Nessun file selezionato", foreground="gray")
        self.file_label.pack(anchor="w", pady=(0, 10))

        ttk.Button(frm, text="Scegli file PDF", command=self.choose_files).pack(anchor="w")

        fmt_frame = ttk.Frame(frm)
        fmt_frame.pack(anchor="w", pady=(10, 10))
        ttk.Label(fmt_frame, text="Formato esportazione:").pack(side="left")
        ttk.Radiobutton(fmt_frame, text="Excel (XLSX)", variable=self.format, value="xlsx").pack(side="left")
        ttk.Radiobutton(fmt_frame, text="CSV", variable=self.format, value="csv").pack(side="left")

        template_frame = ttk.Frame(frm)
        template_frame.pack(anchor="w", fill="x", pady=(0, 10))
        ttk.Label(template_frame, text="Template output:").pack(side="left")
        template_values = [DEFAULT_TEMPLATE_LABEL] + [p.name for p in self.output_templates]
        self.template_combo = ttk.Combobox(
            template_frame,
            textvariable=self.output_template,
            values=template_values,
            state="readonly",
            width=36,
        )
        self.template_combo.pack(side="left", padx=(8, 0))

        ttk.Button(frm, text="Estrai e salva", command=self.process).pack(anchor="center", pady=(10, 0))
        self.status = ttk.Label(frm, text="", foreground="blue")
        self.status.pack(anchor="w", pady=(10, 0))

    def find_output_templates(self):
        return sorted(APP_DIR.glob("output_*.json"))

    def selected_output_columns(self):
        selected = self.output_template.get()
        if not selected or selected == DEFAULT_TEMPLATE_LABEL:
            return None
        path = next((p for p in self.output_templates if p.name == selected), None)
        if path is None:
            raise ValueError(f"Template output non trovato: {selected}")
        return load_output_config(path)

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
            records = [asdict(build_record(Path(f))) for f in self.files]
            if not records:
                raise Exception("Nessun dato estratto.")
            out_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx" if self.format.get() == "xlsx" else ".csv",
                filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
                title="Salva file di output"
            )
            if not out_path:
                self.status.config(text="Operazione annullata.")
                return
            bill_records = [BillRecord(**r) for r in records]
            output_columns = self.selected_output_columns()
            if self.format.get() == "xlsx":
                export_xlsx(bill_records, Path(out_path), output_columns)
            else:
                export_csv(bill_records, Path(out_path), output_columns)
            self.status.config(text=f"File salvato: {out_path}")
            messagebox.showinfo("Successo", f"File salvato:\n{out_path}")
        except Exception as e:
            self.status.config(text=f"Errore: {e}")
            messagebox.showerror("Errore", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = BolletteApp(root)
    root.mainloop()
