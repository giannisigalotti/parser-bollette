from __future__ import annotations

import re

from ..extractors import extract_with_patterns
from ..models import BillRecord


_ABBR_MONTHS = {
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
}


def _parse_abbr_month(s: str) -> str:
    """'GEN.2017' or 'GEN. 2017' → '2017-01-01'."""
    m = re.match(r"([A-Za-z]{3})\.?\s*(\d{4})", s.strip())
    if not m:
        return ""
    month = _ABBR_MONTHS.get(m.group(1).lower(), 0)
    return f"{m.group(2)}-{month:02d}-01" if month else ""


def _parse_dot_date(s: str) -> str:
    """'10.02.2017' → '2017-02-10'."""
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", s.strip())
    if not m:
        return ""
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"


def build_sen_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {"supplier_name": "Servizio Elettrico Nazionale S.p.A."}

    patterns: dict[str, list[tuple[str, str]]] = {
        "invoice_number": [
            (r"N\.\s*Fattura\s+([A-Z0-9]+)", "text"),
        ],
        "pod_code": [
            (r"\b(IT\d{3}E\d{7,})\b", "code"),
        ],
        "committed_power_kw": [
            (r"Potenza contrattualmente\s+impegnata\s+([0-9.,]+)\s+kW", "number"),
            (r"impegnata\s*\n\s*([0-9.,]+)\s+kW", "number"),
        ],
        "tariff_code": [
            (r"Tariffa\s+([^\n]+)", "text"),
        ],
        "energy_cost_eur": [
            (r"Spesa per la materia\s+energia \(A\)\s+([0-9.,]+)\s*€", "money"),
            (r"TOTALE SPESA PER LA MATERIA ENERGIA\s+([0-9.,]+)", "money"),
        ],
        "transport_eur": [
            (r"Spesa per il trasporto e la\s+gestione del contatore \(A\)\s+([0-9.,]+)\s*€", "money"),
            (r"TOTALE SPESA PER IL TRASPORTO E LA GESTIONE DEL CONTATORE\s+([0-9.,]+)", "money"),
        ],
        "system_charges_eur": [
            (r"Spesa per Oneri di Sistema\s+\(A\)\s+([0-9.,]+)\s*€", "money"),
            (r"TOTALE SPESA PER ONERI DI SISTEMA\s+([0-9.,]+)", "money"),
        ],
        "taxes_eur": [
            (r"TOTALE IMPOSTE ED IVA\s+([0-9.,]+)", "money"),
            (r"Totale imposte e IVA \(B\)\s+([0-9.,]+)\s*€", "money"),
        ],
        "vat_eur": [
            (r"Importo IVA\s+\d+%\s+\(su imponibile di euro [0-9.,]+\)\s+([0-9.,]+)\s*€", "money"),
            (r"IVA\s+\d+%\s+\(SU IMPONIBILE DI EURO [0-9.,]+\)\s+([0-9.,]+)", "money"),
        ],
        "invoice_total_eur": [
            (r"TOTALE BOLLETTA\s+([0-9.,]+)", "money"),
            (r"TOTALE DELLA BOLLETTA\s+([0-9.,]+)\s*€", "money"),
        ],
        "total_amount_eur": [
            (r"TOTALE DA PAGARE\s*\n?\s*([0-9.,]+)\s*€", "money"),
        ],
        "customer_name": [
            (r"Casella postale 1100 - 85100 Potenza\s*\n\s*([A-Z][A-Z\s'.]+)\s*\n\s*V\s+", "text"),
        ],
        "supply_address": [
            (r"Forniamo energia in\s*\n\s*([^\n]+)\s*\n\s*([0-9]{5}\s+[A-Z ]+)", "text"),
        ],
    }

    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted

    # Invoice date: "Del 10.02.2017" (dot-separated, not handled by extract_by_kind)
    date_match = re.search(r"[Dd]el\s+(\d{2}\.\d{2}\.\d{4})", raw_text)
    if date_match:
        d = _parse_dot_date(date_match.group(1))
        if d:
            overrides["invoice_date"] = d

    # Due date: "Entro il 02.03.2017"
    due_match = re.search(r"Entro il\s+(\d{2}\.\d{2}\.\d{4})", raw_text)
    if due_match:
        d = _parse_dot_date(due_match.group(1))
        if d:
            overrides["due_date"] = d

    # Billing period: "GEN.2017 - FEB.2017" under BIMESTRE header
    period_match = re.search(
        r"BIMESTRE\s*\n\s*([A-Z]{3}\.?\s*\d{4})\s*-\s*([A-Z]{3}\.?\s*\d{4})",
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

    # Consumption: "Totale energia\nattiva kWh.................... 166"
    cons_match = re.search(
        r"Totale energia\s+attiva kWh[.\s]*([0-9]+)",
        raw_text,
    )
    if cons_match:
        overrides["consumption_kwh"] = cons_match.group(1)

    # F1/F2/F3 breakdown in "consumo fatturato" section
    f1 = re.search(r"ORE DI PUNTA\s+\(F1\)\s+([0-9]+)", raw_text)
    f2 = re.search(r"ORE INTERMEDIE\s+\(F2\)\s+([0-9]+)", raw_text)
    f3 = re.search(r"ORE FUORI PUNTA\s+\(F3\)\s+([0-9]+)", raw_text)
    if f1:
        overrides["consumption_f1_kwh"] = f1.group(1)
    if f2:
        overrides["consumption_f2_kwh"] = f2.group(1)
    if f3:
        overrides["consumption_f3_kwh"] = f3.group(1)

    billed_consumption = re.search(
        r"Consumo fatturato\s+dal\s+[0-9.]+\s+al\s+[0-9.]+[\s\S]{0,260}?"
        r"Totale energia\s+attiva kWh\.*\s*([0-9]+)",
        raw_text,
        re.IGNORECASE,
    )
    if billed_consumption:
        overrides["consumption_kwh"] = billed_consumption.group(1)

    address_match = re.search(
        r"Forniamo energia in\s*\n\s*([^\n]+)\s*\n\s*([0-9]{5}\s+[A-Z ]+)",
        raw_text,
        re.IGNORECASE,
    )
    if address_match:
        overrides["supply_address"] = f"{address_match.group(1).strip()} {address_match.group(2).strip()}"

    return overrides


def apply_sen_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_sen_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
