from __future__ import annotations

import re

from ..extractors import extract_with_patterns
from ..models import BillRecord
from ..text_utils import decimal_to_str, parse_date, parse_decimal


def build_iren_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {"supplier_name": "Iren Mercato S.p.A."}

    patterns: dict[str, list[tuple[str, str]]] = {
        "invoice_number": [
            (r"Fattura n\.\s*([0-9]+)", "text"),
        ],
        "invoice_date": [
            (r"Fattura n\.\s*[0-9]+\s+del\s+(\d{1,2}\s+[A-Z]+\s+\d{4})", "date"),
        ],
        "due_date": [
            (r"Scadenza\s+([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
        ],
        "pod_code": [
            (r"Codice POD\s+(IT[^\s]+)", "code"),
        ],
        "supply_address": [
            (r"Indirizzo\s+([^\n]+)", "text"),
        ],
        "committed_power_kw": [
            (r"Potenza impegnata\s+([0-9.,]+)\s+kW", "number"),
        ],
        "tariff_code": [
            (r"Offerta\s+([^\n]+)", "text"),
        ],
        "consumption_kwh": [
            (r"Consumo energia elettrica\s+([0-9.]+)\s+kWh", "number"),
        ],
        "total_amount_eur": [
            (r"Totale da pagare\s+([0-9.,]+)\s*€", "money"),
        ],
        "invoice_total_eur": [
            (r"Totale bolletta\s+([0-9.,]+)", "money"),
        ],
        "energy_cost_eur": [
            (r"Spesa per la materia energia\*?\s+([0-9.,]+)", "money"),
        ],
        "taxes_eur": [
            (r"Imposte\s+([0-9.,]+)(?!\s*e)", "money"),
        ],
        "vat_eur": [
            (r"Iva agevolata\s+\d+%\s+([0-9.,]+)", "money"),
            (r"\bIVA\s+\d+%\s+([0-9.,]+)", "money"),
        ],
        "customer_name": [
            (r"Cliente\s+([A-Z][A-Z\s]+?)(?:\n|Cod\.)", "text"),
        ],
    }

    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted

    # Billing period: "PERIODO 01 APRILE 2023 - 31 MAGGIO 2023"
    period_match = re.search(
        r"PERIODO\s+(\d{1,2}\s+[A-Z]+\s+\d{4})\s*-\s*(\d{1,2}\s+[A-Z]+\s+\d{4})",
        raw_text,
        re.IGNORECASE,
    )
    if period_match:
        start = parse_date(period_match.group(1))
        end = parse_date(period_match.group(2))
        if start:
            overrides["billing_period_start"] = start
        if end:
            overrides["billing_period_end"] = end

    # TV license: amount appears on the line after the multi-line label
    tv_match = re.search(
        r"[Cc]anone di abbonamento alla televisione[^\n]*\n[^\n]*\n\s*([0-9]+,[0-9]{2})",
        raw_text,
    )
    if tv_match:
        v = parse_decimal(tv_match.group(1))
        if v:
            overrides["tv_license_eur"] = v

    fascia_totals = {"F1": 0.0, "F2": 0.0, "F3": 0.0}
    for match in re.finditer(
        r"\b(F[123])\s+[\d.]+\s+[\d.]+\s+([0-9]+)\s+\d+%",
        raw_text,
        re.IGNORECASE,
    ):
        fascia_totals[match.group(1).upper()] += float(match.group(2))
    if any(fascia_totals.values()):
        overrides["consumption_f1_kwh"] = decimal_to_str(fascia_totals["F1"])
        overrides["consumption_f2_kwh"] = decimal_to_str(fascia_totals["F2"])
        overrides["consumption_f3_kwh"] = decimal_to_str(fascia_totals["F3"])

    return overrides


def apply_iren_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_iren_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
