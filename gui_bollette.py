import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path
from bollette import (
    build_gas_record,
    build_record,
    classify_pdf,
    export_xlsx,
    load_output_config,
    load_output_config_label,
)
from bollette.models import ELECTRICITY_SERVICE_TYPE, GAS_SERVICE_TYPE


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / ".gui_bollette_config.json"
DEFAULT_TEMPLATE_LABEL = "Default - tutte le colonne"
MAX_DISPLAYED_FILES = 8
SAVE_UPDATE = "update"
SAVE_OVERWRITE = "overwrite"
SAVE_CANCEL = "cancel"
SUPPORTED_EXCEL_SUFFIXES = {".xlsx", ".xlsm"}


class BolletteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Estrattore Bollette PDF")
        self.files = []
        self.config = self.load_local_config()
        self.electricity_output_templates = self.find_output_templates(ELECTRICITY_SERVICE_TYPE)
        self.gas_output_templates = self.find_output_templates(GAS_SERVICE_TYPE)
        self.electricity_template_labels = self.template_label_map(self.electricity_output_templates)
        self.gas_template_labels = self.template_label_map(self.gas_output_templates)
        self.electricity_output_template = tk.StringVar(
            value=self.initial_template_label("electricity_template", self.electricity_template_labels)
        )
        self.gas_output_template = tk.StringVar(
            value=self.initial_template_label("gas_template", self.gas_template_labels)
        )
        self.progress_value = tk.IntVar(value=0)

        frm = ttk.Frame(root, padding=20)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Seleziona uno o più PDF:").pack(anchor="w")
        self.file_label = ttk.Label(frm, text="Nessun file selezionato", foreground="gray")
        self.file_label.pack(anchor="w", pady=(0, 10))

        ttk.Button(frm, text="Scegli file PDF", command=self.choose_files).pack(anchor="w")

        electricity_template_frame = ttk.Frame(frm)
        electricity_template_frame.pack(anchor="w", fill="x", pady=(0, 10))
        ttk.Label(electricity_template_frame, text="Template output elettricità:").pack(side="left")
        electricity_template_values = [DEFAULT_TEMPLATE_LABEL] + list(self.electricity_template_labels)
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
        gas_template_values = [DEFAULT_TEMPLATE_LABEL] + list(self.gas_template_labels)
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
        self.progress = ttk.Progressbar(
            frm,
            orient="horizontal",
            mode="determinate",
            variable=self.progress_value,
            maximum=1,
        )
        self.progress.pack(fill="x", pady=(6, 0))
        self.electricity_output_template.trace_add("write", lambda *_: self.save_combo_config())
        self.gas_output_template.trace_add("write", lambda *_: self.save_combo_config())

    def load_local_config(self):
        try:
            with CONFIG_PATH.open(encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError, TypeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def save_local_config(self):
        try:
            CONFIG_PATH.write_text(json.dumps(self.config, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def save_combo_config(self):
        self.config["electricity_template"] = self.electricity_output_template.get()
        self.config["gas_template"] = self.gas_output_template.get()
        self.save_local_config()

    def initial_template_label(self, key, labels):
        saved = self.config.get(key)
        if isinstance(saved, str) and (saved == DEFAULT_TEMPLATE_LABEL or saved in labels):
            return saved
        return DEFAULT_TEMPLATE_LABEL

    def initial_directory(self, *keys):
        for key in keys:
            value = self.config.get(key)
            if not isinstance(value, str) or not value:
                continue
            path = Path(value).expanduser()
            if path.is_dir():
                return str(path)
        return str(Path.home())

    def find_output_templates(self, service_type):
        templates = []
        for path in sorted(APP_DIR.glob("output_*.json")):
            try:
                load_output_config(path, service_type)
            except (OSError, ValueError):
                continue
            templates.append(path)
        return templates

    def template_label_map(self, templates):
        labels = {}
        for path in templates:
            label = load_output_config_label(path)
            if label in labels:
                label = path.name
            labels[label] = path
        return labels

    def selected_output_columns(self, service_type):
        if service_type == GAS_SERVICE_TYPE:
            selected = self.gas_output_template.get()
            template_labels = self.gas_template_labels
        else:
            selected = self.electricity_output_template.get()
            template_labels = self.electricity_template_labels
        if not selected or selected == DEFAULT_TEMPLATE_LABEL:
            return None
        path = template_labels.get(selected)
        if path is None:
            raise ValueError(f"Template output non trovato: {selected}")
        return load_output_config(path, service_type)

    def choose_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona PDF",
            filetypes=[("PDF files", "*.pdf")],
            initialdir=self.initial_directory("input_dir"),
        )
        self.files = list(files)
        if self.files:
            self.config["input_dir"] = str(Path(self.files[0]).parent)
            self.save_local_config()
            self.file_label.config(text=self.selected_files_label(), foreground="black")
        else:
            self.file_label.config(text="Nessun file selezionato", foreground="gray")

    def selected_files_label(self):
        names = [Path(f).name for f in self.files]
        if len(names) <= MAX_DISPLAYED_FILES:
            return "\n".join(names)

        shown = names[:MAX_DISPLAYED_FILES]
        remaining = len(names) - MAX_DISPLAYED_FILES
        return "\n".join(shown + [f"... altri {remaining} file selezionati"])

    def reset_progress(self, maximum):
        self.progress.configure(maximum=max(maximum, 1))
        self.progress_value.set(0)
        self.root.update_idletasks()

    def advance_progress(self, message):
        self.progress_value.set(self.progress_value.get() + 1)
        self.status.config(text=message)
        self.root.update_idletasks()

    def choose_output_path(self):
        out_dir = filedialog.askdirectory(
            title="Scegli cartella di destinazione",
            initialdir=self.initial_directory("output_dir", "input_dir"),
        )
        if not out_dir:
            return None, SAVE_CANCEL

        filename = simpledialog.askstring(
            "Nome file",
            "Nome file Excel:",
            initialvalue=self.config.get("output_filename") or "bollette_estratte.xlsx",
            parent=self.root,
        )
        if not filename:
            return None, SAVE_CANCEL

        output_path = Path(out_dir) / Path(filename).name
        suffix = output_path.suffix.lower()
        if not suffix:
            output_path = output_path.with_suffix(".xlsx")
        elif suffix == ".xls":
            messagebox.showerror("Formato non supportato", "Il formato .xls non e' supportato. Usa .xlsx o .xlsm.")
            return None, SAVE_CANCEL
        elif suffix not in SUPPORTED_EXCEL_SUFFIXES:
            messagebox.showerror("Formato non supportato", "Usa un file .xlsx o .xlsm.")
            return None, SAVE_CANCEL

        self.config["output_dir"] = str(output_path.parent)
        self.config["output_filename"] = output_path.name
        self.save_combo_config()

        if not output_path.exists():
            return output_path, SAVE_UPDATE

        choice = self.ask_existing_file_action(output_path)
        if choice == SAVE_CANCEL:
            return None, SAVE_CANCEL
        return output_path, choice

    def ask_existing_file_action(self, output_path):
        dialog = tk.Toplevel(self.root)
        dialog.title("File esistente")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        choice = tk.StringVar(value=SAVE_CANCEL)

        frm = ttk.Frame(dialog, padding=18)
        frm.pack(fill="both", expand=True)
        ttk.Label(
            frm,
            text=f"Il file esiste gia':\n{output_path}\n\nVuoi aggiornarlo o sovrascriverlo?",
            justify="left",
            wraplength=520,
        ).pack(anchor="w")

        buttons = ttk.Frame(frm)
        buttons.pack(anchor="e", pady=(16, 0))

        def close_with(value):
            choice.set(value)
            dialog.destroy()

        ttk.Button(buttons, text="Aggiorna", command=lambda: close_with(SAVE_UPDATE)).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Sovrascrivi", command=lambda: close_with(SAVE_OVERWRITE)).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Annulla", command=lambda: close_with(SAVE_CANCEL)).pack(side="left")

        dialog.protocol("WM_DELETE_WINDOW", lambda: close_with(SAVE_CANCEL))
        dialog.grab_set()
        dialog.wait_window()
        return choice.get()

    def process(self):
        if not self.files:
            messagebox.showerror("Errore", "Seleziona almeno un file PDF.")
            return

        output_path, save_mode = self.choose_output_path()
        if output_path is None:
            self.status.config(text="Operazione annullata.")
            self.progress_value.set(0)
            return

        total_files = len(self.files)
        total_steps = total_files + total_files + 1
        self.reset_progress(total_steps)
        self.status.config(text=f"Esame PDF 0/{total_files}...")
        self.root.update_idletasks()
        try:
            grouped = {ELECTRICITY_SERVICE_TYPE: [], GAS_SERVICE_TYPE: []}
            for idx, filename in enumerate(self.files, start=1):
                path = Path(filename)
                grouped.setdefault(classify_pdf(path), []).append(path)
                self.advance_progress(f"Esame PDF {idx}/{total_files}...")
            if not grouped[ELECTRICITY_SERVICE_TYPE] and not grouped[GAS_SERVICE_TYPE]:
                raise Exception("Nessun dato estratto.")

            sheets = []
            processed = 0
            if grouped[ELECTRICITY_SERVICE_TYPE]:
                records = []
                for path in grouped[ELECTRICITY_SERVICE_TYPE]:
                    records.append(build_record(path))
                    processed += 1
                    self.advance_progress(f"Estrazione dati {processed}/{total_files}...")
                sheets.append(("Elettricità", records, self.selected_output_columns(ELECTRICITY_SERVICE_TYPE), ELECTRICITY_SERVICE_TYPE))
            if grouped[GAS_SERVICE_TYPE]:
                records = []
                for path in grouped[GAS_SERVICE_TYPE]:
                    records.append(build_gas_record(path))
                    processed += 1
                    self.advance_progress(f"Estrazione dati {processed}/{total_files}...")
                sheets.append(("Gas", records, self.selected_output_columns(GAS_SERVICE_TYPE), GAS_SERVICE_TYPE))

            self.status.config(text="Generazione Excel...")
            self.root.update_idletasks()
            if save_mode == SAVE_OVERWRITE and output_path.exists():
                output_path.unlink()
            export_xlsx(sheets, output_path)
            self.advance_progress("Generazione Excel completata.")
            self.status.config(text=f"File salvato: {output_path}")
            messagebox.showinfo("Successo", f"File salvato:\n{output_path}")
        except Exception as e:
            self.status.config(text=f"Errore: {e}")
            messagebox.showerror("Errore", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = BolletteApp(root)
    root.mainloop()
