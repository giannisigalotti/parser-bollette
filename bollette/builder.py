from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .constants import MONEY_LABELS, TEXT_LABELS
from .extractors import (
    extract_pdf_text,
    extract_lines,
    find_label_value,
    find_period,
    find_consumption,
    find_committed_power,
    infer_supplier,
    infer_supplier_template,
)
from .models import BillRecord
from .templates import TEMPLATE_APPLIERS
from .templates.base import apply_generic_template


def build_record(pdf_path: Path) -> BillRecord:
    raw_text = extract_pdf_text(pdf_path)
    lines = extract_lines(raw_text)
    record = BillRecord(source_file=str(pdf_path.name))
    record.supplier_template = infer_supplier_template(raw_text, lines)

    for field, labels in TEXT_LABELS.items():
        kind = "date" if field in {"invoice_date", "due_date"} else "code" if field == "pod_code" else "text"
        setattr(record, field, find_label_value(lines, labels, kind))

    for field, labels in MONEY_LABELS.items():
        setattr(record, field, find_label_value(lines, labels, "money"))

    record.supplier_name = record.supplier_name or infer_supplier(lines, pdf_path)
    record.billing_period_start, record.billing_period_end = find_period(lines, raw_text)
    record.consumption_kwh = find_consumption(lines, raw_text)
    record.committed_power_kw = find_committed_power(lines, raw_text)

    TEMPLATE_APPLIERS.get(record.supplier_template, apply_generic_template)(record, raw_text, lines)

    record.notes = _build_notes(record)
    return record


def _build_notes(record: BillRecord) -> str:
    missing = [k for k, v in asdict(record).items() if k not in {"source_file", "notes"} and not v]
    parts: list[str] = []
    if record.notes:
        parts.append(record.notes)
    if missing:
        parts.append("Campi mancanti: " + ", ".join(missing))
    return "; ".join(parts)


def discover_pdfs(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".pdf":
        return [path]
    if path.is_dir():
        return sorted(f for f in path.rglob("*.pdf") if f.is_file())
    raise FileNotFoundError(f"Input non trovato: {path}")
