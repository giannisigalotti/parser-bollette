from __future__ import annotations

import re
from pathlib import Path

from ..text_utils import (
    slug_text,
    normalize_text,
    parse_date,
    parse_decimal,
    parse_float_num,
    parse_number,
    decimal_to_str,
)
from .constants import PERIOD_LABELS


def find_period(lines: list[str], raw_text: str) -> tuple[str, str]:
    combined = "\n".join(lines)
    patterns = [
        r"dal\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+al\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*[-–]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]
    for label in PERIOD_LABELS:
        for line in lines:
            if slug_text(label) in slug_text(line):
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        return parse_date(match.group(1)), parse_date(match.group(2))
    for pattern in patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            return parse_date(match.group(1)), parse_date(match.group(2))
    month_matches = re.findall(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", raw_text)
    if len(month_matches) >= 2:
        return parse_date(month_matches[0]), parse_date(month_matches[1])
    return "", ""


def find_consumption(lines: list[str], raw_text: str) -> str:
    candidates: list[float] = []
    kwh_patterns = [
        r"consum[oi]\w*\D{0,12}(\d[\d.\s]*,\d+|\d[\d.\s]*)\s*kwh",
        r"energia attiva\D{0,12}(\d[\d.\s]*,\d+|\d[\d.\s]*)\s*kwh",
        r"totale kwh\D{0,12}(\d[\d.\s]*,\d+|\d[\d.\s]*)",
    ]
    for line in lines:
        lowered = slug_text(line)
        if "kwh" not in lowered:
            continue
        for pattern in kwh_patterns:
            match = re.search(pattern, lowered, re.IGNORECASE)
            if match:
                parsed = parse_decimal(match.group(1))
                if parsed:
                    candidates.append(float(parsed))
    if not candidates:
        for match in re.finditer(r"(\d[\d.\s]*,\d+|\d[\d.\s]*)\s*kwh", raw_text, re.IGNORECASE):
            parsed = parse_decimal(match.group(1))
            if parsed:
                candidates.append(float(parsed))
    if not candidates:
        return ""
    best = max(candidates)
    return str(int(best)) if best.is_integer() else f"{best:.2f}"


def find_committed_power(lines: list[str], raw_text: str) -> str:
    patterns = [
        r"potenza impegnata\D{0,10}(\d[\d.,]*)\s*kw",
        r"potenza contrattualmente\s+impegnata\D{0,20}(\d[\d.,]*)\s*kw",
    ]
    haystack = slug_text("\n".join(lines) + "\n" + raw_text)
    for pattern in patterns:
        match = re.search(pattern, haystack, re.IGNORECASE)
        if match:
            return parse_number(match.group(1))
    return ""


def find_available_power(lines: list[str], raw_text: str) -> str:
    patterns = [
        r"potenza disponibile\D{0,20}(\d[\d.,]*)\s*kw",
        r"potenza contrattualmente\s+disponibile\D{0,20}(\d[\d.,]*)\s*kw",
    ]
    haystack = slug_text("\n".join(lines) + "\n" + raw_text)
    for pattern in patterns:
        match = re.search(pattern, haystack, re.IGNORECASE)
        if match:
            return parse_number(match.group(1))
    return ""


def infer_supplier(lines: list[str], pdf_path: Path) -> str:
    for line in lines[:6]:
        if "octopus energy" in slug_text(line):
            return normalize_text(line[:120])
    joined = " ".join(lines[:5]).strip()
    if joined:
        pieces = re.split(
            r"\b(fattura|numero fattura|data emissione|cliente|pod|scadenza)\b",
            joined,
            flags=re.IGNORECASE,
        )
        candidate = normalize_text(pieces[0])
        if candidate:
            return candidate[:120]
    return lines[0][:120] if lines else pdf_path.stem


def infer_supplier_template(raw_text: str, lines: list[str]) -> str:
    haystack = slug_text("\n".join(lines[:40]) + "\n" + raw_text[:5000])
    if "octopus energy" in haystack:
        return "octopus"
    if "acea energia" in haystack or "acea" in haystack:
        if "periodo di conguaglio" in haystack or "periodica + conguaglio" in haystack:
            return "acea_conguaglio"
        return "acea_standard"
    if "enel energia" in haystack:
        return "enel"
    if "a2a energia" in haystack:
        return "a2a"
    if "iren mercato" in haystack:
        return "iren"
    if "servizio elettrico nazionale" in haystack:
        return "sen"
    if "edison energia" in haystack:
        return "edison"
    return "generic"


def extract_section(raw_text: str, start_label: str, end_label: str | None = None) -> str:
    start = re.search(start_label, raw_text, re.IGNORECASE)
    if not start:
        return ""
    tail = raw_text[start.end():]
    if end_label:
        end = re.search(end_label, tail, re.IGNORECASE)
        if end:
            tail = tail[: end.start()]
    return tail


def extract_detail_values(raw_text: str, label_patterns: list[str]) -> tuple[str, str, str]:
    label_block = "(?:" + "|".join(label_patterns) + ")"
    pattern = re.compile(
        label_block
        + r"\s*\n\s*([0-9.,]+)\s*\n\s*([0-9.,]+(?:\s*€/[\w]+)?)\s*\n\s*([0-9.,\-]+)\s*€",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(raw_text)
    if not match:
        return "", "", ""
    qty = parse_number(match.group(1))
    unit_rate = normalize_text(match.group(2))
    imponibile = parse_decimal(match.group(3))
    return qty, unit_rate, imponibile


def extract_fascia_consumptions(raw_text: str) -> tuple[str, str, str]:
    match = re.search(
        r"Letture.*?(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(\d+)\s+(\d+)\s+Rilevata\s+"
        r"(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(\d+)\s+(\d+)\s+Rilevata",
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return "", "", ""
    return (
        str(int(match.group(2)) - int(match.group(6))),
        str(int(match.group(3)) - int(match.group(7))),
        str(int(match.group(4)) - int(match.group(8))),
    )


def extract_acea_fascia_consumptions(raw_text: str) -> tuple[str, str, str]:
    totals = {"F1": 0.0, "F2": 0.0, "F3": 0.0}
    letture_block = extract_section(
        raw_text, r"PROSPETTO LETTURE E CONSUMI", r"DETTAGLIO CONSUMO FATTURATO"
    )
    for line in [normalize_text(x) for x in letture_block.splitlines() if normalize_text(x)]:
        match = re.search(r"\b(F[123])\b.*?\b(\d+)\s*kWh\b", line, re.IGNORECASE)
        if match:
            qty = parse_float_num(match.group(2))
            if qty is not None:
                totals[match.group(1).upper()] += qty
    if any(totals.values()):
        return (
            decimal_to_str(totals["F1"]),
            decimal_to_str(totals["F2"]),
            decimal_to_str(totals["F3"]),
        )
    return "", "", ""
