from __future__ import annotations

import re

from ..extractors import extract_with_patterns, extract_detail_values, extract_fascia_consumptions
from ..models import BillRecord
from ..text_utils import normalize_text, parse_decimal


def build_octopus_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    patterns: dict[str, list[tuple[str, str]]] = {
        "supplier_name": [
            (r"^(Octopus Energy Italia Srl)", "text"),
            (r"^(Octopus Energy[^\n]+)", "text"),
        ],
        "invoice_number": [
            (r"NUMERO FATTURA[^\n]*\n\s*([A-Z0-9\-]+)", "text"),
            (r"Fattura\s*n[.\s:]*([A-Z0-9\-\/]+)", "text"),
        ],
        "invoice_date": [
            (r"DATA FATTURA:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", "date"),
            (r"DATA EMISSIONE:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", "date"),
        ],
        "due_date": [
            (r"Entro il\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", "date"),
            (r"SCADENZA:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", "date"),
        ],
        "customer_name": [
            (r"I tuoi dati\s*\n\s*([^\n]+)", "text"),
            (r"Cliente:\s*([^\n]+)", "text"),
        ],
        "supply_address": [
            (r"INDIRIZZO DI FORNITURA:\s*\n\s*([^\n]+)", "text"),
            (r"INDIRIZZO DI FATTURAZIONE:\s*\n\s*([^\n]+)", "text"),
        ],
        "pod_code": [
            (r"CODICE POD:\s*\n\s*([A-Z0-9]+)", "code"),
            (r"\b(IT\d{3}E\d{8,})\b", "code"),
        ],
        "tariff_code": [
            (r"NOME OFFERTA:\s*([^\n]+)", "text"),
            (r"OFFERTA:\s*([^\n]+)", "text"),
        ],
        "consumption_kwh": [
            (r"CONSUMO FATTURATO:\s*([0-9.,]+)\s*kWh", "number"),
        ],
        "committed_power_kw": [
            (r"POTENZA IMPEGNATA:\s*\n\s*([0-9.,]+)\s*kW", "number"),
            (r"Potenza impegnata\s*([0-9.,]+)\s*kW", "number"),
        ],
        "total_amount_eur": [
            (r"TOTALE DA PAGARE\s*\n\s*([0-9.,\-]+)\s*€", "money"),
            (r"Questo mese dovrai pagare\s*\n\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "invoice_total_eur": [
            (r"TOTALE BOLLETTA\s*\n\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "bonus_eur": [
            (r"Bonus applicati\s*\n\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "taxes_eur": [
            (r"Accise e IVA\s*\n\s*([0-9.,\-]+)\s*€", "money"),
            (r"Totale Imposte\s*\n\s*([0-9.,\-]+)\s*€", "money"),
            (r"IMPOSTE\s*\n?\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "vat_eur": [
            (r"DI CUI IVA\s*\n\s*([0-9.,\-]+)\s*€", "money"),
            (r"IVA vendite 10%:\s*[0-9.,\-]+\s*€\s*x\s*10%\s*=\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "transport_eur": [
            (r"Spesa per il trasporto e la gestione del contatore[\s\S]*?TOTALE\s*\n\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "system_charges_eur": [
            (r"Spesa per oneri di sistema[\s\S]*?TOTALE\s*\n\s*([0-9.,\-]+)\s*€", "money"),
            (r"Totale oneri di sistema\s*\n\s*([0-9.,\-]+)\s*€", "money"),
        ],
        "tv_license_eur": [
            (r"Canone di abbonamento alla televisione[^\n]*\n\s*([0-9.,\-]+)\s*€", "money"),
        ],
    }

    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted

    # Aggregated network/system amounts from itemised rows
    network_amounts = [
        parse_decimal(m.group(1))
        for m in re.finditer(
            r"di cui spesa per la rete e gli oneri generali di sistema\s*\n\s*[0-9.,]+\s*[^\n]*\n\s*([0-9.,\-]+)\s*€",
            raw_text,
            re.IGNORECASE,
        )
    ]
    sale_amounts = [
        parse_decimal(m.group(1))
        for m in re.finditer(
            r"di cui spesa per vendita energia elettrica\s*\n\s*[0-9.,]+\s*[^\n]*\n\s*([0-9.,\-]+)\s*€",
            raw_text,
            re.IGNORECASE,
        )
    ]
    if network_amounts:
        overrides["system_charges_eur"] = f"{sum(float(v) for v in network_amounts if v):.2f}"
    if sale_amounts:
        overrides["energy_cost_eur"] = f"{sum(float(v) for v in sale_amounts if v):.2f}"

    if not overrides.get("customer_name"):
        for idx, line in enumerate(lines):
            if normalize_text(line).lower() == "i tuoi dati" and idx + 1 < len(lines):
                overrides["customer_name"] = lines[idx + 1]
                break

    return overrides


def build_octopus_detail_overrides(raw_text: str) -> dict[str, str]:
    components = {
        "energy": [r"Energia"],
        "losses": [r"Perdite"],
        "dispbt": [r"Componente DISPbt"],
        "commercialization": [r"Corrispettivo di commercializzazione", r"Corrispettivo commercializzazione"],
        "capacity_market": [r"Corrispettivo mercato capacit(?:à|a)"],
        "dispatching": [r"Dispacciamento"],
        "transport_energy": [r"Trasporto quota energia"],
        "transport_fixed": [r"Trasporto quota fissa"],
        "transport_power": [r"Trasporto quota potenza"],
        "uc3": [r"UC3[^\n]*(?:\n\s*[^\n]*)?"],
        "uc6_fixed": [r"UC6[^\n]*\n\s*\(fisso\)"],
        "uc6_variable": [r"UC6[^\n]*\n\s*\(variabile\)"],
        "arim": [r"Componente ARIM[^\n]*(?:\n[^\n]*)?"],
        "asos": [r"Componente ASOS[^\n]*(?:\n[^\n]*)?"],
        "excise": [r"Imposta erariale[^\n]*"],
    }
    overrides: dict[str, str] = {}
    for prefix, label_patterns in components.items():
        qty, unit_rate, imponibile = extract_detail_values(raw_text, label_patterns)
        overrides[f"{prefix}_qty"] = qty
        overrides[f"{prefix}_unit_rate"] = unit_rate
        overrides[f"{prefix}_imponibile_eur"] = imponibile
    return overrides


def clean_octopus_record(record: BillRecord) -> None:
    if record.tv_license_eur and not __import__("re").fullmatch(r"\d+\.\d{2}", record.tv_license_eur):
        record.tv_license_eur = ""


def apply_octopus_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_octopus_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
    record.consumption_f1_kwh, record.consumption_f2_kwh, record.consumption_f3_kwh = (
        extract_fascia_consumptions(raw_text)
    )
    for field, value in build_octopus_detail_overrides(raw_text).items():
        setattr(record, field, value)
    clean_octopus_record(record)
