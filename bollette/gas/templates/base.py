from __future__ import annotations

import re

from ...extractors import extract_with_patterns
from ..models import GasBillRecord
from ...text_utils import parse_date


def build_generic_gas_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    patterns: dict[str, list[tuple[str, str]]] = {
        "invoice_number": [
            (r"(?:Fattura n\.?|Numero documento)[:\s]+([A-Z0-9\-\/]+)", "text"),
        ],
        "invoice_date": [
            (r"(?:Fattura n\.?\s+[A-Z0-9\-\/]+\s+del|del)\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", "date"),
        ],
        "due_date": [
            (r"(?:QUANDO SCADE|Scadenza)[:\s]*([^\n]+)", "date"),
        ],
        "pdr_code": [
            (r"Codice PDR[:\s]+([0-9A-Z]+)", "code"),
            (r"\bPDR[:\s]+([0-9A-Z]{8,})", "code"),
        ],
        "tariff_code": [
            (r"^Offerta:\s*([^\n]+)", "text"),
        ],
        "consumption_smc": [
            (r"Consumo totale fatturato[:\s]+([0-9.,]+)\s*Smc", "number"),
            (r"CONSUMO FATTURATO[:\s]+([0-9.,]+)\s*Smc", "number"),
        ],
        "estimated_consumption_smc": [
            (r"di cui stimati[:\s]+([0-9.,]+)\s*Smc", "number"),
        ],
        "total_amount_eur": [
            (r"TOTALE\s+DA PAGARE\s*\n?\s*([0-9.,]+)\s*(?:euro|€)", "money"),
        ],
        "invoice_total_eur": [
            (r"TOTALE BOLLETTA\s+([0-9.,]+)", "money"),
        ],
        "gas_sales_eur": [
            (r"di cui spesa per vendita gas naturale\s+[0-9.,]+\s*€/Smc\s+([0-9.,]+)", "money"),
        ],
        "network_charges_eur": [
            (r"di cui spesa per la rete e gli oneri generali di sistema\s+[0-9.,]+\s*€/Smc\s+([0-9.,]+)", "money"),
        ],
        "taxes_eur": [
            (r"Accise e IVA\s+([0-9.,]+)", "money"),
        ],
        "vat_eur": [
            (r"TOTALE IVA\s+([0-9.,]+)", "money"),
        ],
    }
    overrides: dict[str, str] = {}
    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted

    period = re.search(
        r"Periodo oggetto di fatturazione:\s*(.+?)\s*-\s*(.+?)(?:\n|$)",
        raw_text,
        re.IGNORECASE,
    )
    if period:
        overrides["billing_period_start"] = parse_date(period.group(1))
        overrides["billing_period_end"] = parse_date(period.group(2))

    return overrides


def apply_generic_gas_template(record: GasBillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_generic_gas_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
