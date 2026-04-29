from __future__ import annotations

from pathlib import Path

from .extractors import extract_pdf_text, extract_lines, infer_service_type
from .models import ELECTRICITY_SERVICE_TYPE, GAS_SERVICE_TYPE


def discover_pdfs(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".pdf":
        return [path]
    if path.is_dir():
        return sorted(f for f in path.rglob("*") if f.is_file() and f.suffix.lower() == ".pdf")
    raise FileNotFoundError(f"Input non trovato: {path}")


def classify_pdf(pdf_path: Path) -> str:
    raw_text = extract_pdf_text(pdf_path)
    lines = extract_lines(raw_text)
    return infer_service_type(raw_text, lines)


def group_pdfs_by_service(pdfs: list[Path]) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = {ELECTRICITY_SERVICE_TYPE: [], GAS_SERVICE_TYPE: []}
    for pdf in pdfs:
        grouped.setdefault(classify_pdf(pdf), []).append(pdf)
    return grouped
