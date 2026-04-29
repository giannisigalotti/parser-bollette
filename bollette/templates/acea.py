from __future__ import annotations

import re

from ..extractors import extract_with_patterns, extract_section, extract_acea_fascia_consumptions
from ..models import BillRecord
from ..templates.base import build_generic_regex_overrides
from ..text_utils import (
    normalize_text,
    parse_date,
    parse_decimal,
    parse_float_num,
    decimal_to_str,
    normalize_unit_rate,
)


# ── Row aggregation helpers ───────────────────────────────────────────────────

_VARIABLE_ROW = re.compile(
    r"^(?:\d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+)?(?:F\d|SCAGLIONE\s+\d+|\d+)?\s*"
    r"(€/[A-Za-z/]+|€/[\w]+|euro/[A-Za-z/]+|Euro/[A-Za-z/]+)\s+([\-−]?\d+[.,]\d+)\s+"
    r"(?:kWh|Kwh|kW|gg)?\s*([\d.]+,\d+|[\d.]+)\s+([\-−]?\d+,\d+|\d+\.\d+)$",
    re.IGNORECASE,
)
_VARIABLE_ROW_ALT = re.compile(
    r"^(?:\d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+)?(?:F\d|SCAGLIONE\s+\d+|\d+)?\s*"
    r"(€/[A-Za-z/]+|€/[\w]+|euro/[A-Za-z/]+|Euro/[A-Za-z/]+)\s+([\-−]?\d+[.,]\d+)\s+"
    r"([\d.]+,\d+|[\d.]+)\s*(?:kWh|Kwh|kW|gg)?\s+([\-−]?\d+,\d+|\d+\.\d+)$",
    re.IGNORECASE,
)
_FIXED_ROW = re.compile(
    r"^(?:\d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+)?(€/[A-Za-z/]+|€/[\w]+|Euro/[A-Za-z/]+|euro/[A-Za-z/]+)\s+"
    r"([\-−]?\d+[.,]\d+)\s+(?:gg|kW)?\s*([\d.]+,\d+|[\d.]+)\s+([\-−]?\d+,\d+|\d+\.\d+)$",
    re.IGNORECASE,
)
_FIXED_ROW_ALT = re.compile(
    r"^(?:\d{2}/\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+)?(€/[A-Za-z/]+|€/[\w]+|Euro/[A-Za-z/]+|euro/[A-Za-z/]+)\s+"
    r"([\-−]?\d+[.,]\d+)\s+([\d.]+,\d+|[\d.]+)\s*(?:gg|kW)?\s+([\-−]?\d+,\d+|\d+\.\d+)$",
    re.IGNORECASE,
)


def _aggregate_rows(block: str, patterns: list[re.Pattern]) -> tuple[str, str, str]:
    quantities: list[float] = []
    imponibili: list[float] = []
    unit_rates: list[tuple[float, float]] = []
    preferred_unit = ""

    for line in [normalize_text(x) for x in block.splitlines() if normalize_text(x)]:
        match = next((p.match(line) for p in patterns if p.match(line)), None)
        if not match:
            continue
        preferred_unit = preferred_unit or match.group(1).replace("Euro", "euro")
        unit_rate = parse_float_num(match.group(2))
        qty = parse_decimal(match.group(3))
        imponibile = parse_decimal(match.group(4))
        if not qty or not imponibile:
            continue
        qty_f, imp_f = float(qty), float(imponibile)
        quantities.append(qty_f)
        imponibili.append(imp_f)
        if unit_rate is not None:
            unit_rates.append((unit_rate, qty_f))

    if not quantities or not imponibili:
        return "", "", ""

    qty_total = sum(quantities)
    imponibile_total = sum(imponibili)
    avg_rate = ""
    if unit_rates and qty_total:
        weighted = sum(rate * qty for rate, qty in unit_rates) / qty_total
        avg_rate = normalize_unit_rate(weighted, preferred_unit)
    return decimal_to_str(qty_total), avg_rate, f"{imponibile_total:.2f}"


def aggregate_acea_rows(block: str) -> tuple[str, str, str]:
    return _aggregate_rows(block, [_VARIABLE_ROW, _VARIABLE_ROW_ALT])


def aggregate_acea_fixed_rows(block: str) -> tuple[str, str, str]:
    return _aggregate_rows(block, [_FIXED_ROW, _FIXED_ROW_ALT])


# ── Override builders ─────────────────────────────────────────────────────────

def build_acea_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    overrides = build_generic_regex_overrides(raw_text, lines)
    patterns: dict[str, list[tuple[str, str]]] = {
        "supplier_name": [
            (r"(Acea Energia S\.p\.A\.)", "text"),
            (r"^(ACEA[^\n]+)", "text"),
            (r"^(Acea[^\n]+)", "text"),
        ],
        "invoice_number": [
            (r"BOLLETTA PER LA FORNITURA\s+DI ENERGIA ELETTRICAn\.\s*([A-Z0-9\-]+)\s+del", "text"),
        ],
        "invoice_date": [
            (r"BOLLETTA PER LA FORNITURA\s+DI ENERGIA ELETTRICAn\.\s*[A-Z0-9\-]+\s+del\s+([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
        ],
        "tariff_code": [
            (r"OFFERTA\s+([^\n]+)", "text"),
            (r"(?:NOME OFFERTA|TIPO OFFERTA|DENOMINAZIONE OFFERTA)[: ]\s*([^\n]+)", "text"),
        ],
        "supply_address": [
            (r"INDIRIZZO FORNITURA\s+([^\n]+(?:\n[^\n]+)?)", "text"),
            (r"(?:INDIRIZZO DI FORNITURA|UBICAZIONE FORNITURA)[: ]\s*([^\n]+)", "text"),
        ],
        "customer_name": [
            (r"INTESTATARIO CONTRATTO\s+([^\n]+)", "text"),
            (r"(?:INTESTATARIO|CLIENTE|NOMINATIVO)[: ]\s*([^\n]+)", "text"),
        ],
        "due_date": [
            (r"ENTRO IL\s+([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
        ],
        "total_amount_eur": [
            (r"TOTALE DA PAGARE\s+([0-9.]+,\d{2})\s+euro", "money"),
            (r"TOTALE DA PAGARE\s+([0-9.]+,\d{2})\s+EURO", "money"),
        ],
        "invoice_total_eur": [
            (r"TOTALE BOLLETTA\s+([0-9.]+,\d{2})\s+EURO", "money"),
        ],
        "energy_cost_eur": [
            (r"SPESA PER LA MATERIA ENERGIA\s+([0-9.]+,\d{2})\s+EURO", "money"),
            (r"SPESA PER LA MATERIA ENERGIA TOTALE\s+([0-9.]+,\d{2})\s+€", "money"),
        ],
        "transport_eur": [
            (r"SPESA PER IL TRASPORTO E LA GESTIONE CONTATORE TOTALE\s+([0-9.]+,\d{2})\s+€", "money"),
            (r"SPESA PER IL TRASPORTO E LA GESTIONE DEL CONTATORE\s+([0-9.]+,\d{2})\s+EURO", "money"),
        ],
        "system_charges_eur": [
            (r"SPESA PER ONERI DI SISTEMA TOTALE\s+(?:\d+\s+)?([0-9.]+,\d{2})\s+€", "money"),
            (r"SPESA PER ONERI DI SISTEMA\*+\s+([0-9.]+,\d{2})\s+EURO", "money"),
        ],
        "taxes_eur": [
            (r"TOTALE IMPOSTE E IVA(?:\s+\d+)?\s+([0-9.]+,\d{2})\s+EURO", "money"),
            (r"TOTALE IMPOSTE E IVA\*+\s+([0-9.]+,\d{2})\s+EURO", "money"),
            (r"TOTALE\s+([0-9.]+,\d{2})\s+euro", "money"),
        ],
        "vat_eur": [
            (r"IVA 10% immediata su imponibile di [0-9.]+,\d{2}\s+EURO\s+([0-9.]+,\d{2})", "money"),
            (r"IVA 10% immediata su imponibile di [0-9.]+,\d{2}\s+euro\s+([0-9.]+,\d{2})", "money"),
        ],
        "tv_license_eur": [
            (r"CANONE DI ABBONAMENTO TV\s+([0-9.]+,\d{2})\s+EURO", "money"),
            (r"CANONE DI ABBONAMENTO ALLA TELEVISIONE PER USO PRIVATO TOTALE\s+([0-9.]+,\d{2})\s+€", "money"),
            (r"Canone TV[: ]\s*([0-9.]+,\d{2})\s+EURO", "money"),
        ],
    }
    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted

    period_match = re.search(
        r"PERIODO DI FATTURAZIONE:\s*([0-9]{2}\s+[A-Z]+?\s+[0-9]{4})\s*-\s*([0-9]{2}\s+[A-Z]+?\s+[0-9]{4})",
        raw_text,
        re.IGNORECASE,
    )
    if period_match:
        overrides["billing_period_start"] = parse_date(period_match.group(1))
        overrides["billing_period_end"] = parse_date(period_match.group(2))

    return overrides


def build_acea_detail_overrides(raw_text: str) -> dict[str, str]:
    blocks = {
        "energy":          extract_section(raw_text, r"COMPONENTE ENERGIA", r"DISPACCIAMENTO"),
        "dispatching":     extract_section(raw_text,
            r"DISPACCIAMENTO\s+(?:DA A|DAL AL)\s+FASCIA(?:\s+UNITA'\s+DI\s+MISURA)?\s+PREZZO UNITARIO\s+QUANTITÀ EURO",
            r"PERDITE DI RETE - DISPACCIAMENTO"),
        "losses_disp":     extract_section(raw_text, r"PERDITE DI RETE - DISPACCIAMENTO", r"PERDITE DI RETE - ENERGIA"),
        "losses_energy":   extract_section(raw_text, r"PERDITE DI RETE - ENERGIA", r"QUOTA FISSA"),
        "dispbt":          extract_section(raw_text, r"COMP\.DI DISPACCIAMENTO \(PARTE FISSA\)", r"COMPONENTE FISSA QV1 FLEX"),
        "commercialization": extract_section(raw_text, r"COMPONENTE FISSA QV1 FLEX", r"SPESA PER IL TRASPORTO E LA GESTIONE CONTATORE"),
        "transport_energy": extract_section(raw_text, r"QUOTA VARIABILE", r"QUOTA FISSA"),
        "transport_fixed":  extract_section(raw_text, r"QUOTA FISSA\s+QUOTA FISSA", r"QUOTA POTENZA"),
        "transport_power":  extract_section(raw_text, r"QUOTA POTENZA\s+QUOTA POTENZA", r"UC6 QUOTA POTENZA"),
        "uc6_fixed":        extract_section(raw_text, r"UC6 QUOTA POTENZA", r"SPESA PER ONERI DI SISTEMA TOTALE"),
        "arim":             extract_section(raw_text, r"COMPONENTE ARIM", r"COMPONENTE ASOS"),
        "asos":             extract_section(raw_text, r"COMPONENTE ASOS", r"IMPOSTE E IVA TOTALE"),
        "excise":           extract_section(raw_text,
            r"IMPOSTA ERARIALE\s+(?:DA A|DAL AL)(?:\s+UNITA'\s+DI\s+MISURA)?\s+PREZZO UNITARIO\s+QUANTITÀ EURO",
            r"IVA 10%"),
    }

    overrides: dict[str, str] = {}

    qty, rate, imp = aggregate_acea_rows(blocks["energy"])
    overrides["energy_qty"] = qty
    overrides["energy_unit_rate"] = rate
    overrides["energy_imponibile_eur"] = imp

    qty_e, rate_e, imp_e = aggregate_acea_rows(blocks["losses_energy"])
    qty_d, rate_d, imp_d = aggregate_acea_rows(blocks["losses_disp"])
    if qty_e or qty_d:
        q_total = sum(float(x) for x in [qty_e, qty_d] if x)
        i_total = sum(float(x) for x in [imp_e, imp_d] if x)
        weighted: list[tuple[float, float]] = []
        for r, q in [(rate_e, qty_e), (rate_d, qty_d)]:
            if q and r:
                parsed = parse_float_num(r)
                if parsed is not None:
                    weighted.append((parsed, float(q)))
        avg = normalize_unit_rate(sum(r * q for r, q in weighted) / q_total, "euro/kWh") if weighted and q_total else ""
        overrides["losses_qty"] = decimal_to_str(q_total)
        overrides["losses_unit_rate"] = avg
        overrides["losses_imponibile_eur"] = f"{i_total:.2f}"

    variable_components = ["dispatching", "transport_energy", "arim", "asos", "excise"]
    fixed_components = ["dispbt", "commercialization", "transport_fixed", "transport_power", "uc6_fixed"]

    for prefix in variable_components:
        qty, rate, imp = aggregate_acea_rows(blocks[prefix])
        overrides[f"{prefix}_qty"] = qty
        overrides[f"{prefix}_unit_rate"] = rate
        overrides[f"{prefix}_imponibile_eur"] = imp

    for prefix in fixed_components:
        qty, rate, imp = aggregate_acea_fixed_rows(blocks[prefix])
        overrides[f"{prefix}_qty"] = qty
        overrides[f"{prefix}_unit_rate"] = rate
        overrides[f"{prefix}_imponibile_eur"] = imp

    return overrides


# ── Record cleaners ───────────────────────────────────────────────────────────

_DETAIL_FIELDS = [
    f"{prefix}_{suffix}"
    for prefix in [
        "energy", "losses", "dispbt", "commercialization", "capacity_market",
        "dispatching", "transport_energy", "transport_fixed", "transport_power",
        "uc3", "uc6_fixed", "uc6_variable", "arim", "asos", "excise",
    ]
    for suffix in ["qty", "unit_rate", "imponibile_eur"]
]


def clean_acea_record(record: BillRecord) -> None:
    if record.supplier_name and "acea.it" in record.supplier_name.lower():
        record.supplier_name = "Acea Energia S.p.A."
    if record.tv_license_eur and not re.fullmatch(r"\d+\.\d{2}", record.tv_license_eur):
        record.tv_license_eur = ""


def clean_acea_conguaglio_record(record: BillRecord) -> None:
    clean_acea_record(record)
    for field in _DETAIL_FIELDS:
        setattr(record, field, "")


# ── Template appliers ─────────────────────────────────────────────────────────

def apply_acea_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_acea_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
    record.consumption_f1_kwh, record.consumption_f2_kwh, record.consumption_f3_kwh = (
        extract_acea_fascia_consumptions(raw_text)
    )
    for field, value in build_acea_detail_overrides(raw_text).items():
        setattr(record, field, value)
    clean_acea_record(record)


def apply_acea_conguaglio_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_acea_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
    record.consumption_f1_kwh, record.consumption_f2_kwh, record.consumption_f3_kwh = (
        extract_acea_fascia_consumptions(raw_text)
    )
    clean_acea_conguaglio_record(record)
    _append_note(
        record,
        "Bolletta Acea con conguaglio: dettagli componente lasciati vuoti per evitare somme fuorvianti su periodi storici/ricalcoli",
    )


def _append_note(record: BillRecord, text: str) -> None:
    if not text:
        return
    if not record.notes:
        record.notes = text
    elif text not in record.notes:
        record.notes = f"{record.notes}; {text}"
