from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from ..extractors import extract_pdf_text, extract_lines
from .extractors import infer_gas_supplier_template
from .models import GasBillRecord
from .templates import GAS_TEMPLATE_APPLIERS
from .templates.base import apply_generic_gas_template


def build_gas_record(pdf_path: Path) -> GasBillRecord:
    raw_text = extract_pdf_text(pdf_path)
    lines = extract_lines(raw_text)
    record = GasBillRecord(source_file=pdf_path.name)
    record.supplier_template = infer_gas_supplier_template(raw_text, lines)

    GAS_TEMPLATE_APPLIERS.get(record.supplier_template, apply_generic_gas_template)(record, raw_text, lines)

    record.notes = _build_gas_notes(record)
    return record


def _build_gas_notes(record: GasBillRecord) -> str:
    missing = [k for k, v in asdict(record).items() if k not in {"source_file", "notes"} and not v]
    parts: list[str] = []
    if record.notes:
        parts.append(record.notes)
    if missing:
        parts.append("Campi mancanti: " + ", ".join(missing))
    return "; ".join(parts)
