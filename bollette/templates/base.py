from __future__ import annotations

from ..constants import MONEY_LABELS, TEXT_LABELS, PERIOD_LABELS
from ..extractors import extract_with_patterns
from ..models import BillRecord


def build_generic_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    patterns: dict[str, list[tuple[str, str]]] = {
        "invoice_number": [
            (r"(?:NUMERO FATTURA|FATTURA N\.?|NUMERO DOCUMENTO)[^\n:]*[: ]\s*([A-Z0-9\-\/]+)", "text"),
        ],
        "invoice_date": [
            (r"(?:DATA FATTURA|DATA EMISSIONE|EMESSA IL)[: ]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", "date"),
        ],
        "due_date": [
            (r"(?:SCADENZA|DATA SCADENZA|ENTRO IL)[: ]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", "date"),
        ],
        "pod_code": [
            (r"\b(IT\d{3}E\d{8,})\b", "code"),
        ],
        "committed_power_kw": [
            (r"(?:POTENZA IMPEGNATA|POTENZA DISPONIBILE)[: ]\s*([0-9.,]+)\s*kW", "number"),
        ],
        "consumption_kwh": [
            (r"(?:CONSUMO FATTURATO|CONSUMO TOTALE|ENERGIA ATTIVA)[: ]\s*([0-9.,]+)\s*kWh", "number"),
        ],
        "total_amount_eur": [
            (r"(?:TOTALE DA PAGARE|IMPORTO DA PAGARE|TOTALE FATTURA)[: ]?\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "invoice_total_eur": [
            (r"TOTALE BOLLETTA[: ]?\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "taxes_eur": [
            (r"(?:TOTALE IMPOSTE|ACCISE E IVA|IMPOSTE)[: ]?\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "vat_eur": [
            (r"(?:DI CUI IVA|IVA)[: ]?\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "transport_eur": [
            (r"(?:SPESA PER IL TRASPORTO E LA GESTIONE DEL CONTATORE|TRASPORTO E GESTIONE DEL CONTATORE)[: ]?\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "system_charges_eur": [
            (r"(?:TOTALE ONERI DI SISTEMA|SPESA PER ONERI DI SISTEMA|ONERI DI SISTEMA)[: ]?\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "tv_license_eur": [
            (r"(?:CANONE RAI|CANONE TV|CANONE DI ABBONAMENTO ALLA TELEVISIONE)[^\n]*[: ]?\s*([0-9.,\-]+)\s*€", "money"),
        ],
    }
    overrides: dict[str, str] = {}
    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted
    return overrides


def apply_generic_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_generic_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)


__all__ = [
    "MONEY_LABELS",
    "TEXT_LABELS",
    "PERIOD_LABELS",
    "build_generic_regex_overrides",
    "apply_generic_template",
]
