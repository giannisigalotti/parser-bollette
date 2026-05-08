from __future__ import annotations

import re

from ...extractors import extract_with_patterns
from ...text_utils import decimal_to_str, parse_date, parse_decimal, parse_number
from ..models import BillRecord


def build_a2a_regex_overrides(raw_text: str, lines: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {"supplier_name": "A2A Energia S.p.A."}

    patterns: dict[str, list[tuple[str, str]]] = {
        "invoice_number": [
            (r"Bolletta di [^\n]* n\.\s*([0-9]+)\s+del", "text"),
            (r"^([0-9]+)\s+numero fattura elettronica", "text"),
        ],
        "invoice_date": [
            (r"Bolletta di [^\n]* n\.\s*[0-9]+\s+del\s+([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})", "date"),
        ],
        "due_date": [
            (r"ENTRO QUANDO \?\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})", "date"),
        ],
        "pod_code": [
            (r"POD \(punto di prelievo\)\s*\n\s*(IT[0-9A-Z]+)", "code"),
        ],
        "committed_power_kw": [
            (r"Potenza impegnata\s*\n\s*([0-9.,]+)\s*kW", "number"),
        ],
        "available_power_kw": [
            (r"Potenza disponibile\s*\n\s*([0-9.,]+)\s*kW", "number"),
        ],
        "energy_cost_eur": [
            (r"Spesa per la materia energia:\s*([0-9.,]+)\s*€", "money"),
            (r"SPESA PER LA MATERIA ENERGIA\s*€\s*([0-9.,]+)", "money"),
        ],
        "transport_eur": [
            (r"Spesa per il trasporto\s+e la gestione del contatore:\s*([0-9.,]+)\s*€", "money"),
            (r"SPESA PER IL TRASPORTO E LA GESTIONE DEL CONTATORE\s*€\s*([0-9.,]+)", "money"),
        ],
        "system_charges_eur": [
            (r"Spesa per oneri di sistema:\s*([0-9.,]+)\s*€", "money"),
            (r"SPESA PER ONERI DI SISTEMA\s*€\s*([0-9.,]+)", "money"),
        ],
        "taxes_eur": [
            (r"Totale imposte e IVA:\s*([0-9.,]+)\s*€", "money"),
        ],
        "invoice_total_eur": [
            (r"TOTALE BOLLETTA:\s*([0-9.,]+)\s*€", "money"),
            (r"TOTALE BOLLETTA\s*€\s*([0-9.,]+)", "money"),
        ],
        "total_amount_eur": [
            (r"TOTALE A PAGARE\s*€\s*([0-9.,]+)", "money"),
            (r"QUANTO DEVO PAGARE \?\s*([0-9.,]+)\s+euro", "money"),
        ],
        "vat_eur": [
            (r"Aliquota IVA\s+[0-9]+\s*%\s+[0-9.,]+\s*€\s+([0-9.,]+)\s*€", "money"),
            (r"IVA\s+[0-9]+%[^\n]*\s€\s*([0-9.,]+)", "money"),
        ],
    }

    for field, field_patterns in patterns.items():
        extracted = extract_with_patterns(raw_text, field_patterns)
        if extracted:
            overrides[field] = extracted

    customer_name = _line_after(lines, "Intestatario del contratto:")
    if customer_name:
        overrides["customer_name"] = customer_name

    supply_address = _extract_multiline_after(
        lines,
        "Indirizzo di fornitura:",
        stop_labels=("Tipologia cliente",),
    )
    if supply_address:
        overrides["supply_address"] = supply_address

    tariff_code = _line_after(lines, "Tipologia offerta")
    if tariff_code:
        overrides["tariff_code"] = tariff_code

    billing_period = re.search(
        r"bolletta per i consumi\s+dal\s+(.+?)\s+al\s+(.+?)(?:\n|lo stato)",
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    if billing_period:
        overrides["billing_period_start"] = parse_date(billing_period.group(1))
        overrides["billing_period_end"] = parse_date(billing_period.group(2))

    active = _extract_a2a_active_consumptions(raw_text)
    if active:
        (
            overrides["consumption_f1_kwh"],
            overrides["consumption_f2_kwh"],
            overrides["consumption_f3_kwh"],
            overrides["consumption_kwh"],
        ) = active

    reactive = _extract_a2a_reactive_consumptions(lines)
    if reactive:
        (
            overrides["reactive_energy_f1_kvarh"],
            overrides["reactive_energy_f2_kvarh"],
            overrides["reactive_energy_f3_kvarh"],
            overrides["reactive_energy_kvarh"],
        ) = reactive

    excise = _extract_a2a_excise(raw_text)
    if excise:
        overrides["excise_qty"], overrides["excise_unit_rate"], overrides["excise_imponibile_eur"] = excise

    transport = _extract_a2a_transport_details(lines)
    overrides.update(transport)

    return overrides


def apply_a2a_template(record: BillRecord, raw_text: str, lines: list[str]) -> None:
    for field, value in build_a2a_regex_overrides(raw_text, lines).items():
        setattr(record, field, value)


def _line_after(lines: list[str], label: str) -> str:
    for idx, line in enumerate(lines):
        if line.lower() == label.lower() and idx + 1 < len(lines):
            return lines[idx + 1]
    return ""


def _extract_multiline_after(lines: list[str], label: str, stop_labels: tuple[str, ...]) -> str:
    for idx, line in enumerate(lines):
        if line.lower() != label.lower():
            continue
        parts: list[str] = []
        for candidate in lines[idx + 1 :]:
            if any(candidate.lower().startswith(stop.lower()) for stop in stop_labels):
                break
            parts.append(candidate)
        return " ".join(parts)
    return ""


def _extract_a2a_active_consumptions(raw_text: str) -> tuple[str, str, str, str] | None:
    match = re.search(
        r"Totale consumo fatturato di energia attiva\s+"
        r"([0-9.]+)\s*kWh\s+([0-9.]+)\s*kWh\s+([0-9.]+)\s*kWh\s+([0-9.]+)\s*kWh",
        raw_text,
        re.IGNORECASE,
    )
    if not match:
        return None
    return tuple(parse_number(match.group(i)) for i in range(1, 5))  # type: ignore[return-value]


def _extract_a2a_reactive_consumptions(lines: list[str]) -> tuple[str, str, str, str] | None:
    values: dict[str, float] = {}
    in_section = False
    for line in lines:
        if "ENERGIA REATTIVA" in line:
            in_section = True
            continue
        if in_section and line == "PERIODO":
            continue
        if in_section and "POTENZA" in line:
            break
        if not in_section:
            continue
        match = re.search(r"Fascia oraria\s+(F[123]).*?([0-9.]+)\s*kvarh", line, re.IGNORECASE)
        if match:
            values[match.group(1).upper()] = float(parse_decimal(match.group(2)) or 0)
    if not values:
        return None
    f1 = values.get("F1", 0.0)
    f2 = values.get("F2", 0.0)
    f3 = values.get("F3", 0.0)
    return decimal_to_str(f1), decimal_to_str(f2), decimal_to_str(f3), decimal_to_str(f1 + f2 + f3)


def _extract_a2a_excise(raw_text: str) -> tuple[str, str, str] | None:
    match = re.search(
        r"ACCISE \(kWh\) €/kWh IMPORTO\s+([0-9.]+)\s+([0-9.,]+)\s+([0-9.,]+)\s*€",
        raw_text,
        re.IGNORECASE,
    )
    if not match:
        return None
    return parse_number(match.group(1)), match.group(2), parse_decimal(match.group(3))


def _extract_a2a_transport_details(lines: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    fixed = _line_after(lines, "QUOTA FISSA")
    fixed_match = re.search(
        r"€/cliente/mese\s+([0-9.,]+)\s+1 mese\s+€\s+([0-9.,]+)",
        fixed,
        re.IGNORECASE,
    )
    if fixed_match:
        overrides["transport_fixed_qty"] = "1"
        overrides["transport_fixed_unit_rate"] = fixed_match.group(1)
        overrides["transport_fixed_imponibile_eur"] = parse_decimal(fixed_match.group(2))

    power = _line_after(lines, "QUOTA POTENZA")
    power_match = re.search(
        r"€/kW/mese\s+([0-9.,]+)\s+1 mese\s+x\s+([0-9.,]+)\s+kW\s+€\s+([0-9.,]+)",
        power,
        re.IGNORECASE,
    )
    if power_match:
        overrides["transport_power_qty"] = parse_number(power_match.group(2))
        overrides["transport_power_unit_rate"] = power_match.group(1)
        overrides["transport_power_imponibile_eur"] = parse_decimal(power_match.group(3))

    variable = _line_after(lines, "QUOTA VARIABILE")
    variable_match = re.search(
        r"€/kWh\s+([0-9.,]+)\s+([0-9.,]+)\s+kWh\s+€\s+([0-9.,]+)",
        variable,
        re.IGNORECASE,
    )
    if variable_match:
        overrides["transport_energy_qty"] = parse_number(variable_match.group(2))
        overrides["transport_energy_unit_rate"] = variable_match.group(1)
        overrides["transport_energy_imponibile_eur"] = parse_decimal(variable_match.group(3))

    return overrides
