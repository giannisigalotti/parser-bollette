from __future__ import annotations

import re

from ...extractors import extract_with_patterns
from ..models import BillRecord
from ...text_utils import decimal_to_str, parse_decimal, parse_float_num, parse_number, sum_amounts


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
            (r"L.?offerta che hai sottoscritto è:\s*([^\n]+)", "text"),
            (r"Nome offerta\s*\n\s*([^\n]+)", "text"),
            (r"La tua offerta:\s*([^\n]+)", "text"),
        ],
        "pod_code": [
            (r"\b(IT\d{3}E\d{8,})\b", "code"),
        ],
        "supply_address": [
            (r"La fornitura di energia elettrica è in:\s*\n\s*([^\n]+)", "text"),
            (r"INDIRIZZO DI FORNITURA:\s*\n\s*([^\n]+?)(?:\s+x{4,}.*)?$", "text"),
        ],
        "committed_power_kw": [
            (r"POTENZA IMPEGNATA:\s*\n?\s*([0-9.,]+)\s*kW", "number"),
        ],
        "available_power_kw": [
            (r"POTENZA DISPONIBILE:\s*\n?\s*([0-9.,]+)\s*kW", "number"),
            (r"Potenza disponibile:\s*([0-9.,]+)\s*kW", "number"),
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

    customer_name = _extract_enel_customer_name(lines)
    if customer_name:
        overrides["customer_name"] = customer_name

    tv_match = re.search(
        r"([0-9]+,[0-9]{2})\s*€[^\n]{0,10}\n[^\n]*[Cc]anone di abbonamento alla televisione",
        raw_text,
    )
    if tv_match:
        v = parse_decimal(tv_match.group(1))
        if v:
            overrides["tv_license_eur"] = v

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

    energy_cost = _extract_enel_energy_cost(lines)
    if energy_cost:
        overrides["energy_cost_eur"] = energy_cost

    transport_cost = _extract_enel_transport_cost(lines)
    if transport_cost:
        overrides["transport_eur"] = transport_cost

    overrides["committed_power_kw"] = _extract_enel_committed_power(lines)

    invoice_total = _extract_enel_invoice_total(lines)
    if invoice_total:
        overrides["invoice_total_eur"] = invoice_total

    excise_amount = _extract_enel_excise_amount(lines)

    split_payment_vat = _extract_enel_split_payment_vat(lines)
    overrides["vat_eur"] = excise_amount or split_payment_vat
    if split_payment_vat:
        overrides["taxes_eur"] = split_payment_vat

    fascia_values = _extract_enel_fascia_consumptions(lines)
    if fascia_values:
        (
            overrides["consumption_f1_kwh"],
            overrides["consumption_f2_kwh"],
            overrides["consumption_f3_kwh"],
            overrides["consumption_kwh"],
        ) = fascia_values

    reactive_values = _extract_enel_reactive_energy(lines)
    if reactive_values:
        (
            overrides["reactive_energy_f1_kvarh"],
            overrides["reactive_energy_f2_kvarh"],
            overrides["reactive_energy_f3_kvarh"],
            overrides["reactive_energy_kvarh"],
        ) = reactive_values

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


def _extract_enel_customer_name(lines: list[str]) -> str:
    for line in lines[:40]:
        match = re.match(r"Gentile\s+(.+?)(?:,)?$", line, re.IGNORECASE)
        if not match:
            continue
        value = match.group(1)
        value = re.sub(r"\s+Amm\.\s*pub\.?$", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+", " ", value).strip(" ,.")
        if value:
            return value
    return ""


def _extract_enel_energy_cost(lines: list[str]) -> str:
    patterns = [
        r"Totale spesa per l.?energia\s+([0-9.,]+)\s*€?",
        r"Spesa per l.?energia\s+\(A\)\s+([0-9.,]+)\s*€",
        r"Totale spesa\s+\(A\)\s+([0-9.,]+)\s*€",
    ]
    return _extract_enel_amount_from_lines(lines, patterns)


def _extract_enel_transport_cost(lines: list[str]) -> str:
    patterns = [
        r"Totale spesa per il trasporto dell.?energia elettrica e la gestione del contatore\s+([0-9.,]+)\s*€?",
        r"Spesa per il trasporto dell.?energia elettrica e la gestione\s+del contatore\s+\(A\)\s+([0-9.,]+)\s*€",
    ]
    return _extract_enel_amount_from_lines(lines, patterns)


def _extract_enel_amount_from_lines(lines: list[str], patterns: list[str]) -> str:
    for idx, line in enumerate(lines):
        combined = line
        if idx + 1 < len(lines):
            combined += " " + lines[idx + 1]
        for pattern in patterns:
            match = re.search(pattern, combined, re.IGNORECASE)
            if match:
                return parse_decimal(match.group(1))
    return ""


def _extract_enel_committed_power(lines: list[str]) -> str:
    for idx, line in enumerate(lines):
        match = re.search(
            r"\b(?:Potenza contrattualmente impegnata|POTENZA IMPEGNATA):\s*([0-9.,]+)\s*kW\b",
            line,
            re.IGNORECASE,
        )
        if match:
            return parse_number(match.group(1))
        if re.fullmatch(r"POTENZA IMPEGNATA:", line, re.IGNORECASE) and idx + 1 < len(lines):
            next_match = re.search(r"([0-9.,]+)\s*kW\b", lines[idx + 1], re.IGNORECASE)
            if next_match:
                return parse_number(next_match.group(1))
    return ""


def _extract_enel_invoice_total(lines: list[str]) -> str:
    for idx, line in enumerate(lines):
        if not re.fullmatch(r"ACCISE E IVA", line, re.IGNORECASE):
            continue
        if idx + 1 >= len(lines) or not re.fullmatch(r"TOTALE BOLLETTA", lines[idx + 1], re.IGNORECASE):
            continue
        amounts: list[str] = []
        for candidate in lines[idx + 2 : idx + 6]:
            if re.fullmatch(r"[0-9][0-9.,\s]*\s*€?", candidate):
                parsed = parse_decimal(candidate)
                if parsed:
                    amounts.append(parsed)
        if len(amounts) >= 2:
            return amounts[1]

    return _extract_enel_amount_from_lines(
        lines,
        [r"\bTotale\s+Bolletta\s+([0-9.,]+)\s*€?"],
    )


def _extract_enel_excise_amount(lines: list[str]) -> str:
    for idx, line in enumerate(lines):
        if not re.search(r"Accisa sull.?energia elettrica", line, re.IGNORECASE):
            continue
        for candidate in lines[idx + 1 : idx + 5]:
            if re.fullmatch(r"[0-9][0-9.,\s]*\s*€", candidate):
                return parse_decimal(candidate)
    return ""


def _extract_enel_split_payment_vat(lines: list[str]) -> str:
    for idx, line in enumerate(lines):
        if not re.search(r"IVA\s+Scissione\s+Pagamenti", line, re.IGNORECASE):
            continue

        same_line = _last_money_in_line(line)
        if same_line:
            return same_line

        for candidate in lines[idx + 1 : idx + 4]:
            parsed = _last_money_in_line(candidate)
            if parsed:
                return parsed
    return ""


def _last_money_in_line(line: str) -> str:
    if "€" not in line:
        return ""
    return _last_decimal_in_line(line)


def _last_decimal_in_line(line: str) -> str:
    matches = re.findall(r"(?<!\d)([0-9][0-9.,]*)(?!\d)", line)
    if not matches:
        return ""
    return parse_decimal(matches[-1])


def _extract_enel_fascia_consumptions(lines: list[str]) -> tuple[str, str, str, str] | None:
    for idx, line in enumerate(lines):
        if not re.search(r"\bConsumo\s+(?:rilevato|fatturato)\b", line, re.IGNORECASE):
            continue
        if re.search(r"\breattiva\b", line, re.IGNORECASE):
            continue

        block = lines[idx + 1 : idx + 8]
        parsed = _parse_enel_fascia_block(block, "kWh")
        if parsed:
            return parsed
    return None


def _extract_enel_reactive_energy(lines: list[str]) -> tuple[str, str, str, str] | None:
    for idx, line in enumerate(lines):
        if not re.search(r"\bConsumo\s+(?:rilevato|fatturato)\s+reattiva\b", line, re.IGNORECASE):
            continue

        block = lines[idx + 1 : idx + 8]
        parsed = _parse_enel_fascia_block(block, "kVarh")
        if parsed:
            return parsed
    return _extract_enel_reactive_reading_delta(lines)


def _extract_enel_reactive_reading_delta(lines: list[str]) -> tuple[str, str, str, str] | None:
    for idx, line in enumerate(lines):
        if not re.fullmatch(r"Riepilogo letture energia reattiva prelevata", line, re.IGNORECASE):
            continue

        readings: list[tuple[float, float, float]] = []
        for candidate in lines[idx + 1 : idx + 10]:
            if candidate.startswith("Bolletta sintetica") or candidate.startswith("Riepilogo "):
                break
            match = re.match(
                r"\d{2}/\d{2}/\d{4}\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)",
                candidate,
            )
            if not match:
                continue
            values = tuple(parse_float_num(match.group(i)) or 0.0 for i in range(1, 4))
            readings.append(values)

        if len(readings) < 2:
            continue

        first = readings[0]
        last = readings[-1]
        deltas = tuple(max(last[i] - first[i], 0.0) for i in range(3))
        total = sum(deltas)
        return (
            decimal_to_str(deltas[0]),
            decimal_to_str(deltas[1]),
            decimal_to_str(deltas[2]),
            decimal_to_str(total),
        )
    return None


def _parse_enel_fascia_block(block: list[str], unit: str) -> tuple[str, str, str, str] | None:
    label_lines: list[str] = []
    values: list[str] = []
    unit_pattern = re.escape(unit)

    for line in block:
        found_values = re.findall(rf"([0-9][0-9.,]*)\s*{unit_pattern}\b", line, re.IGNORECASE)
        if found_values:
            values = found_values
            break
        label_lines.append(line)

    if len(values) < 4:
        return None

    labels = _enel_fascia_labels(label_lines)
    if labels == ["F1", "F2", "F3", "TOTAL"]:
        f1, f2, f3, total = values[:4]
    elif labels == ["TOTAL", "F3", "F2", "F1"]:
        f3, f2, f1, total = values[:4]
    elif labels == ["F3", "F2", "F1", "TOTAL"]:
        f3, f2, f1, total = values[:4]
    else:
        return None

    return (
        parse_number(f1),
        parse_number(f2),
        parse_number(f3),
        parse_number(total),
    )


def _enel_fascia_labels(lines: list[str]) -> list[str]:
    labels: list[str] = []
    for line in lines:
        for match in re.finditer(r"\b(F[123])\b|Totale energia", line, re.IGNORECASE):
            labels.append(match.group(1).upper() if match.group(1) else "TOTAL")
    return labels


def apply_enel_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_enel_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)
