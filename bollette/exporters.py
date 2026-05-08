from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .models import ELECTRICITY_SERVICE_TYPE, GAS_SERVICE_TYPE
from .electricity.models import BillRecord, NUMERIC_COLUMNS, OUTPUT_COLUMNS
from .gas.models import GasBillRecord, GAS_NUMERIC_COLUMNS, GAS_OUTPUT_COLUMNS
from .output_config import OutputColumn, default_output_columns


DATE_COLUMNS = ["invoice_date", "due_date", "billing_period_start", "billing_period_end"]
Record = BillRecord | GasBillRecord

# (sheet_name, records, columns, service_type)
SheetSpec = tuple[str, list[Record], list[OutputColumn] | None, str]


def export_xlsx(sheets: list[SheetSpec], output_path: Path) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.styles.numbers import FORMAT_NUMBER_00
    from openpyxl.utils import get_column_letter

    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_sheets: dict[str, pd.DataFrame] = {}
    if output_path.exists():
        try:
            existing_sheets = pd.read_excel(output_path, sheet_name=None)
        except Exception:
            existing_sheets = {}

    # Build one PreparedSheet per sheet before writing
    prepared: list[_PreparedSheet] = [
        _prepare_sheet(sheet_name, records, columns, service_type, existing_sheets)
        for sheet_name, records, columns, service_type in sheets
    ]

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for ps in prepared:
            ps.frame.to_excel(writer, sheet_name=ps.sheet_name, index=False, header=ps.headers)

    wb = openpyxl.load_workbook(output_path)

    thin = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
    header_font = Font(bold=True)

    for ps in prepared:
        ws = wb[ps.sheet_name]

        for col_idx, col_name in enumerate(ps.frame.columns, 1):
            col_letter = get_column_letter(col_idx)
            for cell in ws[col_letter]:
                if cell.row == 1:
                    continue
                if col_name in (
                    "consumption_kwh",
                    "consumption_f1_kwh",
                    "consumption_f2_kwh",
                    "consumption_f3_kwh",
                    "reactive_energy_kvarh",
                    "reactive_energy_f1_kvarh",
                    "reactive_energy_f2_kvarh",
                    "reactive_energy_f3_kvarh",
                    "consumption_smc",
                    "estimated_consumption_smc",
                    "annual_consumption_smc",
                ):
                    cell.number_format = "0"
                    cell.alignment = Alignment(horizontal="right")
                elif col_name in ps.numeric_columns:
                    cell.number_format = FORMAT_NUMBER_00
                    cell.alignment = Alignment(horizontal="right")
                elif col_name in DATE_COLUMNS:
                    has_time = hasattr(cell.value, "hour") and (
                        cell.value.hour or cell.value.minute or cell.value.second
                    )
                    cell.number_format = "DD/MM/YYYY HH:MM:SS" if has_time else "DD/MM/YYYY"
                    cell.alignment = Alignment(horizontal="center")
                else:
                    cell.alignment = Alignment(wrap_text=True, horizontal="left")

        for col_idx, col_name in enumerate(ps.frame.columns, 1):
            col_letter = get_column_letter(col_idx)
            max_len = max(
                (len(str(c.value)) if c.value is not None else 0 for c in ws[col_letter]),
                default=0,
            )
            ws.column_dimensions[col_letter].width = min(max(max_len, len(col_name)) + 2, 40)

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cell.border = thin
                if cell.row == 1:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center")

        for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
            ws.row_dimensions[row[0].row].height = 15

        ws.auto_filter.ref = ws.dimensions

    wb.save(output_path)


class _PreparedSheet:
    __slots__ = ("sheet_name", "frame", "headers", "numeric_columns")

    def __init__(
        self,
        sheet_name: str,
        frame: pd.DataFrame,
        headers: list[str],
        numeric_columns: list[str],
    ) -> None:
        self.sheet_name = sheet_name
        self.frame = frame
        self.headers = headers
        self.numeric_columns = numeric_columns


def _prepare_sheet(
    sheet_name: str,
    records: list[Record],
    columns: list[OutputColumn] | None,
    service_type: str,
    existing_sheets: dict[str, pd.DataFrame],
) -> _PreparedSheet:
    output_columns = columns or default_output_columns(service_type)
    column_names = [col.source for col in output_columns]
    model_columns = _model_columns(service_type)
    numeric_columns = _numeric_columns(service_type)

    frame = pd.DataFrame([asdict(r) for r in records], columns=model_columns)
    frame = frame[column_names]

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

    for col in numeric_columns:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col].replace("", pd.NA), errors="coerce").astype(float)

    for col in DATE_COLUMNS:
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")

    if "billing_period_start" in frame.columns:
        frame = frame.sort_values("billing_period_start", ascending=True)

    headers = [_col_header(col, unit_map) for col in output_columns]

    if sheet_name in existing_sheets and "source_file" in frame.columns:
        existing = existing_sheets[sheet_name].copy()
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

    return _PreparedSheet(sheet_name, frame, headers, numeric_columns)


def _col_header(output_col: OutputColumn, unit_map: dict[str, str]) -> str:
    col = output_col.source
    title = output_col.title or col
    if output_col.title:
        return title
    return title + (f" ({unit_map[col]})" if unit_map.get(col) else "") if col.endswith("_unit_rate") else title


def _model_columns(service_type: str) -> list[str]:
    if service_type == ELECTRICITY_SERVICE_TYPE:
        return OUTPUT_COLUMNS
    if service_type == GAS_SERVICE_TYPE:
        return GAS_OUTPUT_COLUMNS
    raise ValueError(f"Tipo servizio non supportato: {service_type}")


def _numeric_columns(service_type: str) -> list[str]:
    if service_type == ELECTRICITY_SERVICE_TYPE:
        return NUMERIC_COLUMNS
    if service_type == GAS_SERVICE_TYPE:
        return GAS_NUMERIC_COLUMNS
    raise ValueError(f"Tipo servizio non supportato: {service_type}")
