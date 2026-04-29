from __future__ import annotations

import calendar
import re

from ..extractors import extract_with_patterns
from ..models import BillRecord
from ..text_utils import decimal_to_str, normalize_unit_rate, parse_decimal, parse_float_num, parse_number


_MONTHS = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}


def build_edison_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {"supplier_name": "Edison Energia S.p.A."}

    patterns: dict[str, list[tuple[str, str]]] = {
        "invoice_number": [
            (r"Nr\.?\s*Documento\s+([0-9]+)\s+del", "text"),
            (r"NUMERO DOCUMENTO\s*\n\s*([0-9]+)", "text"),
        ],
        "invoice_date": [
            (r"Nr\.?\s*Documento\s+[0-9]+\s+del\s+([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
            (r"NUMERO DOCUMENTO:\s*[0-9]+\s+DEL\s+([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
        ],
        "due_date": [
            (r"DA PAGARE ENTRO IL\s*\n\s*[0-9.,]+\s*€\s*\n\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", "date"),
        ],
        "pod_code": [
            (r"\b(IT\d{3}E\d{8,})\b", "code"),
        ],
        "tariff_code": [
            (r"OFFERTA\s*\n\s*([^\n]+)", "text"),
            (r"Codice Prodotto\s*\n\s*([^\n]+)", "text"),
        ],
        "committed_power_kw": [
            (r"POTENZA IMPEGNATA\s*\n\s*([0-9.,]+)\s*kW", "number"),
            (r"Potenza impegnata\s*\n\s*([0-9.,]+)\s*kW", "number"),
        ],
        "available_power_kw": [
            (r"POTENZA DISPONIBILE\s*\n\s*([0-9.,]+)\s*kW", "number"),
            (r"Potenza disponibile\s*\n\s*([0-9.,]+)\s*kW", "number"),
        ],
        "total_amount_eur": [
            (r"Totale da pagare\s*\n\s*([0-9.,]+)\s*€", "money"),
            (r"TOTALE BOLLETTA/FATTURA\s*\n\s*DA PAGARE ENTRO IL\s*\n\s*([0-9.,]+)\s*€", "money"),
        ],
        "invoice_total_eur": [
            (r"TOTALE BOLLETTA/FATTURA\s*\n\s*DA PAGARE ENTRO IL\s*\n\s*([0-9.,]+)\s*€", "money"),
            (r"Totale Periodo\s*\n\s*([0-9.,]+)\s*€", "money"),
        ],
        "energy_cost_eur": [
            (r"Totale Servizi di Vendita\s*\n\s*([0-9.,]+)\s*€", "money"),
        ],
        "transport_eur": [
            (r"Totale Servizi di Rete\s*\n\s*([0-9.,]+)\s*€", "money"),
        ],
        "taxes_eur": [
            (r"Totale Imposte\s*\n\s*([0-9.,]+)\s*€", "money"),
        ],
        "vat_eur": [
            (r"Iva\s+\d+%\s*\(su imponibile\s+[0-9.,]+\s*€\):\s*\n\s*([0-9.,]+)\s*€", "money"),
        ],
        "consumption_kwh": [
            (r"CONSUMI FATTURATI\s*\n\s*([0-9.,]+)\s*kWh", "number"),
            (r"Consumo fatturato\s*\n\s*([0-9.,]+)\s*kWh", "number"),
        ],
    }

    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted

    customer_name = _extract_after_exact_label(lines, "CLIENTE")
    if customer_name:
        overrides["customer_name"] = customer_name

    period_start, period_end = _extract_billing_month(raw_text)
    if period_start and period_end:
        overrides["billing_period_start"] = period_start
        overrides["billing_period_end"] = period_end

    supply_address = _extract_supply_address(lines)
    if supply_address:
        overrides["supply_address"] = supply_address

    f1, f2, f3 = _extract_fascia_consumptions(lines)
    if f1 or f2 or f3:
        overrides["consumption_f1_kwh"] = f1
        overrides["consumption_f2_kwh"] = f2
        overrides["consumption_f3_kwh"] = f3

    overrides.update(build_edison_detail_overrides(lines))
    return overrides


def build_edison_detail_overrides(lines: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    rows = _extract_charge_rows(lines)
    groups = {
        "energy": [row for row in rows if row.label.startswith("energia in ")],
        "losses": [row for row in rows if row.label.startswith("perdite in ")],
        "capacity_market": [row for row in rows if "mercato capacita" in row.label],
        "dispatching": [
            row
            for row in rows
            if row.section == "dispatching" and "mercato capacita" not in row.label
        ],
        "uc3": [row for row in rows if row.label.startswith("uc3")],
        "uc6_fixed": [row for row in rows if row.label.startswith("uc6")],
        "arim": [row for row in rows if row.label.startswith("arim")],
        "asos": [row for row in rows if row.label.startswith("asos")],
        "transport_fixed": [
            row for row in rows if row.label.startswith(("quota fissa", "costi di misura"))
        ],
        "transport_power": [row for row in rows if row.label.startswith("quota potenza")],
        "transport_energy": [
            row for row in rows if row.label.startswith(("quota energia", "costi di trasmissione"))
        ],
        "excise": [row for row in rows if row.label.startswith("imposta erariale")],
    }

    for prefix, group_rows in groups.items():
        qty, rate, amount = _aggregate_rows(group_rows)
        overrides[f"{prefix}_qty"] = qty
        overrides[f"{prefix}_unit_rate"] = rate
        overrides[f"{prefix}_imponibile_eur"] = amount

    return overrides


class _ChargeRow:
    def __init__(self, label: str, section: str, qty: str, unit_rate: str, amount: str) -> None:
        self.label = label
        self.section = section
        self.qty = qty
        self.unit_rate = unit_rate
        self.amount = amount


def _extract_charge_rows(lines: list[str]) -> list[_ChargeRow]:
    rows: list[_ChargeRow] = []
    section = ""
    current_label = ""
    for idx, line in enumerate(lines):
        lowered = _slug(line)
        if lowered == "dispacciamento":
            section = "dispatching"
            current_label = lowered
            continue
        if lowered == "servizi di rete":
            section = "network"
            continue
        if lowered == "imposte":
            section = "taxes"
            continue
        if _is_charge_label(line):
            current_label = lowered
            if idx + 1 < len(lines) and _slug(lines[idx + 1]) in {"picco", "fuori picco"}:
                current_label = f"{current_label} {lines[idx + 1].lower()}"
            continue
        qty = line
        unit_rate = lines[idx + 1] if idx + 1 < len(lines) else ""
        amount = lines[idx + 2] if idx + 2 < len(lines) else ""
        vat = lines[idx + 3] if idx + 3 < len(lines) else ""
        if line == "-" and idx + 3 < len(lines) and lines[idx + 1] == "-":
            amount = lines[idx + 2]
            vat = lines[idx + 3]
        elif not re.fullmatch(r"[-0-9.,]+\s+\S+", line):
            continue
        elif idx + 3 >= len(lines) or "€" not in unit_rate or "%" not in vat:
            continue
        if "€" not in amount:
            continue
        if not current_label:
            continue
        rows.append(
            _ChargeRow(
                label=current_label,
                section=section,
                qty=qty,
                unit_rate=unit_rate,
                amount=amount,
            )
        )
    return rows


def _is_charge_label(line: str) -> bool:
    lowered = _slug(line)
    prefixes = (
        "energia in ",
        "perdite in ",
        "reintr.",
        "aggregazione misure",
        "corrispettivo mercato capacita",
        "approv. risorse",
        "funzionamento terna",
        "interromp. carico",
        "costi sicurezza",
        "ulteriori partite",
        "modulaz eolico",
        "uc3",
        "uc6",
        "arim",
        "asos",
        "quota fissa",
        "quota potenza",
        "quota energia",
        "costi di misura",
        "costi di trasmissione",
        "imposta erariale",
    )
    return lowered.startswith(prefixes)


def _aggregate_rows(rows: list[_ChargeRow]) -> tuple[str, str, str]:
    quantities: list[float] = []
    amounts: list[float] = []
    weighted_rates: list[tuple[float, float]] = []
    preferred_unit = ""

    for row in rows:
        qty = parse_decimal(row.qty)
        amount = parse_decimal(row.amount)
        rate = parse_float_num(row.unit_rate)
        if amount:
            amounts.append(float(amount))
        if qty:
            qty_f = float(qty)
            quantities.append(qty_f)
            if rate is not None:
                preferred_unit = preferred_unit or _unit_from_rate(row.unit_rate)
                weighted_rates.append((rate, qty_f))

    if not amounts:
        return "", "", ""

    qty_total = sum(quantities)
    amount_total = sum(amounts)
    unit_rate = ""
    if weighted_rates and qty_total:
        unit_rate = normalize_unit_rate(
            sum(rate * qty for rate, qty in weighted_rates) / qty_total,
            preferred_unit,
        )
    return (
        decimal_to_str(qty_total) if quantities else "",
        unit_rate,
        f"{amount_total:.2f}",
    )


def _unit_from_rate(value: str) -> str:
    match = re.search(r"€/[^\s]+", value)
    return match.group(0) if match else ""


def _extract_billing_month(raw_text: str) -> tuple[str, str]:
    match = re.search(r"Periodo di riferimento\s*\n\s*([A-Za-z]+)\s+(\d{4})", raw_text, re.IGNORECASE)
    if not match:
        return "", ""
    month = _MONTHS.get(match.group(1).lower())
    if not month:
        return "", ""
    year = int(match.group(2))
    last_day = calendar.monthrange(year, month)[1]
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}"


def _extract_supply_address(lines: list[str]) -> str:
    for idx, line in enumerate(lines):
        if line.lower() != "indirizzo di fornitura":
            continue
        pieces: list[str] = []
        for candidate in lines[idx + 1: idx + 5]:
            if _slug(candidate) in {"pod", "distributore locale", "codice cig"}:
                break
            pieces.append(candidate)
        return " ".join(pieces)
    return ""


def _extract_after_exact_label(lines: list[str], label: str) -> str:
    for idx, line in enumerate(lines):
        if line == label and idx + 1 < len(lines):
            return lines[idx + 1]
    return ""


def _extract_fascia_consumptions(lines: list[str]) -> tuple[str, str, str]:
    for idx, line in enumerate(lines):
        if line.lower() != "storico consumi fatturati nell'ultimo anno":
            continue
        found = ("", "", "")
        for pos in range(idx + 1, min(idx + 40, len(lines) - 8)):
            if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", lines[pos]):
                continue
            if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", lines[pos + 1]):
                continue
            values = lines[pos + 4: pos + 8]
            if all(re.fullmatch(r"\d+", value) for value in values):
                f1, f2, f3, _total = values
                found = (f1, f2, f3)
        return found
    return "", "", ""


def _slug(value: str) -> str:
    replacements = str.maketrans("àèéìíîòóùú", "aeeiiioouu")
    return value.lower().translate(replacements).strip()


def apply_edison_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_edison_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
