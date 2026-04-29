from __future__ import annotations

import re
from typing import Iterable

from pypdf import PdfReader

from .text_utils import (
    DATE_HINTS,
    normalize_text,
    slug_text,
    parse_date,
    parse_decimal,
    parse_number,
)


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_lines(text: str) -> list[str]:
    return [normalize_text(line) for line in text.splitlines() if normalize_text(line)]


def extract_by_kind(value: str, kind: str) -> str:
    if kind == "date":
        match = re.search(
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]+\s+\d{2,4})",
            value,
            re.IGNORECASE,
        )
        return parse_date(match.group(1)) if match else ""
    if kind == "money":
        match = re.search(r"(-?\d[\d.\s]*,\d{2}|-?\d[\d,.\s]*\.\d{2})", value)
        return parse_decimal(match.group(1)) if match else ""
    if kind == "code":
        match = re.search(
            r"\b([A-Z]{2}\d[A-Z0-9]{11,14}|IT\d{14}[A-Z0-9]{0,4}|[A-Z0-9][A-Z0-9/\-]{5,})\b",
            value,
        )
        return match.group(1) if match else normalize_text(value)
    if kind == "number":
        match = re.search(r"(-?\d[\d.\s]*,\d+|-?\d[\d,.\s]*\.\d+|-?\d+)", value)
        return parse_number(match.group(1)) if match else ""
    return normalize_text(value)


def extract_with_patterns(text: str, patterns: list[tuple[str, str]]) -> str:
    for pattern, kind in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if not match:
            continue
        value = match.group(1)
        return extract_by_kind(value, kind) if kind != "text" else normalize_text(value)
    return ""


def label_is_too_generic(value: str) -> bool:
    return any(hint in slug_text(value) for hint in DATE_HINTS)


def try_extract_after_label(line: str, label: str, kind: str) -> str:
    pattern = re.compile(re.escape(label), re.IGNORECASE)
    match = pattern.search(line)
    if not match:
        return ""
    tail = line[match.end():]
    tail = re.sub(r"^[\s:.-]+", "", tail)
    return extract_by_kind(tail, kind) or normalize_text(tail)


def find_label_value(lines: list[str], labels: Iterable[str], kind: str) -> str:
    for idx, line in enumerate(lines):
        slug = slug_text(line)
        for label in labels:
            if slug_text(label) not in slug:
                continue
            direct = try_extract_after_label(line, label, kind)
            if direct:
                return direct
            if idx + 1 < len(lines):
                next_line = lines[idx + 1]
                if label_is_too_generic(next_line):
                    continue
                candidate = extract_by_kind(next_line, kind)
                if candidate:
                    return candidate
                return next_line
    return ""


def infer_service_type(raw_text: str, lines: list[str]) -> str:
    early = slug_text("\n".join(lines[:40]) + "\n" + raw_text[:3000])
    haystack = slug_text("\n".join(lines[:120]) + "\n" + raw_text[:12000])
    if (
        "gas naturale" in early
        or re.search(r"\bcodice\s+pdr\b", haystack)
        or re.search(r"\bpdr\s*[:\n]\s*[0-9]{8,}", haystack)
        or re.search(r"consumo\s+(?:totale\s+)?fatturato[:\s]+[0-9.,]+\s*smc", haystack)
        or "spesa per la vendita di gas naturale" in haystack
    ):
        return "gas"
    return "electricity"


