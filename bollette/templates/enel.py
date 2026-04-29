from __future__ import annotations

import re

from ..extractors import extract_with_patterns
from ..models import BillRecord
from ..text_utils import parse_decimal, parse_number, sum_amounts


_ABBR_MONTHS = {
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
}


def _parse_abbr_month(s: str) -> str:
    """'LUG. 2024' or 'LUG.2024' → 'YYYY-MM-01'."""
    m = re.match(r"([A-Za-z]{3})\.?\s*(\d{4})", s.strip())
    if not m:
        return ""
    month = _ABBR_MONTHS.get(m.group(1).lower(), 0)
    return f"{m.group(2)}-{month:02d}-01" if month else ""


def build_enel_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {"supplier_name": "Enel Energia S.p.A."}

    patterns: dict[str, list[tuple[str, str]]] = {
        "invoice_number": [
            (r"fattura elettronica n\.\s*([A-Z0-9]+)\s+del", "text"),
        ],
        "invoice_date": [
            (r"fattura elettronica n\.\s*[A-Z0-9]+\s+del\s+([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
        ],
        "due_date": [
            (r"Quando scade\?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
            (r"Scadenza[:\s]+([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
        ],
        "tariff_code": [
            (r"Nome offerta\s*\n\s*([^\n]+)", "text"),
            (r"La tua offerta:\s*([^\n]+)", "text"),
        ],
        "pod_code": [
            (r"\b(IT\d{3}E\d{8,})\b", "code"),
        ],
        "supply_address": [
            (r"INDIRIZZO DI FORNITURA:\s*\n\s*([^\n]+?)(?:\s+x{4,}.*)?$", "text"),
        ],
        "committed_power_kw": [
            (r"POTENZA IMPEGNATA:\s*\n?\s*([0-9.,]+)\s*kW", "number"),
        ],
        "consumption_kwh": [
            (r"([0-9.]+)\s+kWh\s*\n\s*consumi rilevati", "number"),
            (r"Totale energia\s*\n[^\n]*\n[^\n]*\n[^\n]*\n\s*([0-9.]+)\s+kWh", "number"),
        ],
        "total_amount_eur": [
            (r"TOTALE DA PAGARE\s*\n?\s*([0-9.,]+)\s*€", "money"),
        ],
        "invoice_total_eur": [
            (r"([0-9.,]+)\s*€\s*\n\s*Totale bolletta\b", "money"),
            (r"ACCISE E IVA\s*\n\s*TOTALE BOLLETTA\s*\n\s*[0-9.,]+\s*€\s*\n\s*([0-9.,]+)\s*€", "money"),
            (r"TOTALE BOLLETTA\s*\n?\s*([0-9.,]+)\s*€", "money"),
        ],
        "taxes_eur": [
            (r"ACCISE E IVA\s*\n?\s*([0-9.,]+)\s*€", "money"),
            (r"ACCISE E IVA\s*\n\s*TOTALE BOLLETTA\s*\n\s*([0-9.,]+)\s*€", "money"),
        ],
        "energy_cost_eur": [
            (r"Totale di spesa per la vendita di energia elettrica\s*\n?\s*([0-9.,]+)\s*€", "money"),
        ],
        "customer_name": [
            (r"\*somma dei consumi negli ultimi 12 mesi\s*\n\s*([A-Z][A-Z\s']+)\s*\n\s*C/O", "text"),
        ],
    }

    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted

    # TV license: amount appears on the line just before the label in fiscal detail
    tv_match = re.search(
        r"([0-9]+,[0-9]{2})\s*€[^\n]{0,10}\n[^\n]*[Cc]anone di abbonamento alla televisione",
        raw_text,
    )
    if tv_match:
        v = parse_decimal(tv_match.group(1))
        if v:
            overrides["tv_license_eur"] = v

    # Amounts in the first summary put the value before the multiline label.
    tv_summary = re.search(
        r"([0-9][0-9.,\s]*,[0-9]{2})\s*€\s*\n\s*Canone di abbonamento alla\s*\n\s*televisione per uso privato",
        raw_text,
        re.IGNORECASE,
    )
    if tv_summary:
        v = parse_decimal(tv_summary.group(1))
        if v:
            overrides["tv_license_eur"] = v

    bonus_values = [
        parse_decimal(m.group(1))
        for m in re.finditer(r"\b(?:Bonus Enel|BONUS SOCIALE)\s+(-?[0-9.,]+)\s*€", raw_text, re.IGNORECASE)
    ]
    if bonus_values:
        overrides["bonus_eur"] = sum_amounts([v for v in bonus_values if v])

    network_total = _extract_enel_network_total(lines)
    if network_total:
        overrides["system_charges_eur"] = network_total

    fascia_match = re.search(
        r"Consumo rilevato.*?Totale energia\s+F3\s+F2\s+F1\s+"
        r"([0-9.]+)\s*kWh\s+([0-9.]+)\s*kWh\s+([0-9.]+)\s*kWh\s+([0-9.]+)\s*kWh",
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    if fascia_match:
        overrides["consumption_f3_kwh"] = parse_number(fascia_match.group(1))
        overrides["consumption_f2_kwh"] = parse_number(fascia_match.group(2))
        overrides["consumption_f1_kwh"] = parse_number(fascia_match.group(3))
        overrides["consumption_kwh"] = parse_number(fascia_match.group(4))

    # Billing period from "Periodo LUG. 2024 - AGO. 2024"
    period_match = re.search(
        r"Periodo\s+([A-Z]{3}\.?\s*\d{4})\s*-\s*([A-Z]{3}\.?\s*\d{4})",
        raw_text,
        re.IGNORECASE,
    )
    if period_match:
        start = _parse_abbr_month(period_match.group(1))
        end = _parse_abbr_month(period_match.group(2))
        if start:
            overrides["billing_period_start"] = start
        if end:
            overrides["billing_period_end"] = end

    return overrides


def _money_lines(lines: list[str], start_label: str, end_label: str) -> list[str]:
    in_block = False
    values: list[str] = []
    for line in lines:
        if start_label.lower() in line.lower():
            in_block = True
            continue
        if in_block and end_label.lower() in line.lower():
            break
        if not in_block:
            continue
        if re.fullmatch(r"[0-9][0-9.,\s]*\s*€", line):
            parsed = parse_decimal(line)
            if parsed:
                values.append(parsed)
    return values


def _extract_enel_network_total(lines: list[str]) -> str:
    quota_consumi = _money_lines(lines, "QUOTA CONSUMI", "QUOTA FISSA E QUOTA POTENZA")
    quota_fissa_potenza = _money_lines(lines, "QUOTA FISSA E QUOTA POTENZA", "SERVIZI AGGIUNTIVI")

    network_values: list[str] = []
    if len(quota_consumi) >= 3:
        network_values.append(quota_consumi[2])
    if len(quota_fissa_potenza) >= 5:
        network_values.extend([quota_fissa_potenza[2], quota_fissa_potenza[4]])
    return sum_amounts(network_values) if network_values else ""


def apply_enel_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_enel_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
