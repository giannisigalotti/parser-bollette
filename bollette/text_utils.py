from __future__ import annotations

import re

from dateutil import parser as date_parser


DATE_HINTS = ("giorno", "mese", "anno")

ITALIAN_MONTHS = {
    "gennaio": "January",
    "febbraio": "February",
    "marzo": "March",
    "aprile": "April",
    "maggio": "May",
    "giugno": "June",
    "luglio": "July",
    "agosto": "August",
    "settembre": "September",
    "ottobre": "October",
    "novembre": "November",
    "dicembre": "December",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def slug_text(value: str) -> str:
    lowered = value.lower()
    replacements = str.maketrans("àèéìíîòóùú", "aeeiiioouu")
    return normalize_text(lowered.translate(replacements))


def parse_date(value: str) -> str:
    cleaned = value.strip(" .,:;")
    cleaned = re.sub(r"(\d)([A-Za-z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"([A-Za-z])(\d)", r"\1 \2", cleaned)
    for italian, english in ITALIAN_MONTHS.items():
        cleaned = re.sub(italian, english, cleaned, flags=re.IGNORECASE)
    try:
        parsed = date_parser.parse(cleaned, dayfirst=True, fuzzy=True)
    except (ValueError, OverflowError):
        return ""
    return parsed.date().isoformat()


def parse_decimal(value: str) -> str:
    cleaned = value.strip().replace("−", "-")
    cleaned = re.sub(r"[^\d,.\-]", "", cleaned)
    if not cleaned:
        return ""
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned and cleaned.count(".") >= 1:
        parts = cleaned.split(".")
        if all(part.isdigit() for part in parts) and all(len(part) == 3 for part in parts[1:]):
            cleaned = "".join(parts)
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return ""


def parse_float_num(value: str) -> float | None:
    cleaned = value.strip().replace("−", "-")
    cleaned = re.sub(r"[^\d,.\-]", "", cleaned)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned and cleaned.count(".") >= 1:
        parts = cleaned.split(".")
        if all(part.isdigit() for part in parts) and all(len(part) == 3 for part in parts[1:]):
            cleaned = "".join(parts)
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_number(value: str) -> str:
    parsed = parse_decimal(value)
    if not parsed:
        return ""
    numeric = float(parsed)
    return str(int(numeric)) if numeric.is_integer() else parsed


def decimal_to_str(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def normalize_unit_rate(value: float, unit: str) -> str:
    unit = normalize_text(unit)
    if not unit:
        return f"{value:.6f}"
    return f"{value:.6f} {unit}"


def sum_amounts(values: list[str]) -> str:
    total = sum(float(v) for v in values if v)
    return f"{total:.2f}" if values else ""
