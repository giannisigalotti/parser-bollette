from __future__ import annotations

import csv
import re
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .models import BillRecord, OUTPUT_COLUMNS, NUMERIC_COLUMNS
from .output_config import OutputColumn, default_output_columns


DATE_COLUMNS = ["invoice_date", "due_date", "billing_period_start", "billing_period_end"]


def export_csv(
    records: list[BillRecord],
    output_path: Path,
    columns: list[OutputColumn] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(record) for record in records]
    if not rows:
        return

    output_columns = columns or default_output_columns()
    column_names = [col.source for col in output_columns]
    unit_map: dict[str, str] = {}

    for col in column_names:
        if not col.endswith("_unit_rate"):
            continue
        units: set[str] = set()
        values: list[str] = []
        for raw in [str(row[col]) for row in rows]:
            m = re.match(r"([\d.,\-]+)\s*([\w€/\.]+)?", raw.strip())
            if m:
                values.append(m.group(1).replace(",", "."))
                units.add(m.group(2) or "")
            else:
                values.append("")
                units.add("")
        for i, row in enumerate(rows):
            row[col] = values[i]
        unit_map[col] = next(iter(units - {""}), "") if len(units - {""}) == 1 else ""

    def header(output_col: OutputColumn) -> str:
        col = output_col.source
        title = output_col.title or col
        if output_col.title:
            return title
        return title + (f" ({unit_map[col]})" if unit_map.get(col) else "") if col.endswith("_unit_rate") else title

    headers = [header(col) for col in output_columns]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header(col): row[col.source] for col in output_columns})


def export_xlsx(
    records: list[BillRecord],
    output_path: Path,
    columns: list[OutputColumn] | None = None,
) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.styles.numbers import FORMAT_NUMBER_00
    from openpyxl.utils import get_column_letter

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_columns = columns or default_output_columns()
    column_names = [col.source for col in output_columns]
    frame = pd.DataFrame([asdict(r) for r in records], columns=OUTPUT_COLUMNS)
    frame = frame[column_names]

    # Estrai unità di misura dalle colonne unit_rate
    unit_map: dict[str, str] = {}
    for col in frame.columns:
        if not col.endswith("_unit_rate"):
            continue
        units: set[str] = set()
        values: list[str] = []
        for v in frame[col].astype(str):
            m = re.match(r"([\d.,\-]+)\s*([\w€/\.]+)?", v.strip())
            if m:
                values.append(m.group(1).replace(",", "."))
                units.add(m.group(2) or "")
            else:
                values.append("")
                units.add("")
        frame[col] = pd.to_numeric(values, errors="coerce")
        unit_map[col] = next(iter(units - {""}), "") if len(units - {""}) == 1 else ""

    for col in NUMERIC_COLUMNS:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col].replace("", pd.NA), errors="coerce").astype(float)

    for col in DATE_COLUMNS:
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")

    if "billing_period_start" in frame.columns:
        frame = frame.sort_values("billing_period_start", ascending=True)

    def col_header(output_col: OutputColumn) -> str:
        col = output_col.source
        title = output_col.title or col
        if output_col.title:
            return title
        return title + (f" ({unit_map[col]})" if unit_map.get(col) else "") if col.endswith("_unit_rate") else title

    headers = [col_header(col) for col in output_columns]

    # Aggiorna file esistente invece di sovrascriverlo
    if output_path.exists():
        if "source_file" in frame.columns:
            existing = pd.read_excel(output_path)
            header_to_source = dict(zip(headers, column_names, strict=True))
            existing = existing.rename(columns=header_to_source)
            if "source_file" in existing.columns:
                existing = existing.reindex(columns=column_names)
                existing = existing.set_index("source_file")
                frame = frame.set_index("source_file")
                existing.update(frame)
                for idx in frame.index:
                    if idx not in existing.index:
                        existing.loc[idx] = frame.loc[idx]
                frame = existing.reset_index()
                frame = frame.reindex(columns=column_names)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, header=headers)

    wb = openpyxl.load_workbook(output_path)
    ws = wb.active

    thin = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
    header_font = Font(bold=True)

    # Formattazione celle dati
    for col_idx, col_name in enumerate(frame.columns, 1):
        col_letter = get_column_letter(col_idx)
        for cell in ws[col_letter]:
            if cell.row == 1:
                continue
            if col_name in ("consumption_kwh", "consumption_f1_kwh", "consumption_f2_kwh", "consumption_f3_kwh"):
                cell.number_format = "0"
                cell.alignment = Alignment(horizontal="right")
            elif col_name in NUMERIC_COLUMNS:
                cell.number_format = FORMAT_NUMBER_00
                cell.alignment = Alignment(horizontal="right")
            elif col_name in DATE_COLUMNS:
                has_time = hasattr(cell.value, "hour") and (cell.value.hour or cell.value.minute or cell.value.second)
                cell.number_format = "DD/MM/YYYY HH:MM:SS" if has_time else "DD/MM/YYYY"
                cell.alignment = Alignment(horizontal="center")
            else:
                cell.alignment = Alignment(wrap_text=True, horizontal="left")

    # Auto-fit larghezza colonne
    for col_idx, col_name in enumerate(frame.columns, 1):
        col_letter = get_column_letter(col_idx)
        max_len = max(
            (len(str(c.value)) if c.value is not None else 0 for c in ws[col_letter]),
            default=0,
        )
        ws.column_dimensions[col_letter].width = min(max(max_len, len(col_name)) + 2, 40)

    # Stile header e bordi
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = thin
            if cell.row == 1:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")

    # Altezza minima righe dati
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        ws.row_dimensions[row[0].row].height = 15

    ws.auto_filter.ref = ws.dimensions

    # Rimuovi eventuali righe Totale già presenti e ricreale
    for row_idx in reversed([
        cell.row for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=1)
        for cell in row if str(cell.value).strip().lower() == "totale"
    ]):
        ws.delete_rows(row_idx)

    last_data_row = ws.max_row
    total_row_idx = last_data_row + 1
    for col_idx, col_name in enumerate(frame.columns, 1):
        col_letter = get_column_letter(col_idx)
        cell = ws[f"{col_letter}{total_row_idx}"]
        if col_name in NUMERIC_COLUMNS:
            cell.value = f"=SUM({col_letter}2:{col_letter}{last_data_row})"
            cell.number_format = FORMAT_NUMBER_00
            cell.alignment = Alignment(horizontal="right")
        elif col_idx == 1:
            cell.value = "Totale"
            cell.alignment = Alignment(horizontal="left")
        else:
            cell.alignment = Alignment(horizontal="center")
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin

    wb.save(output_path)
